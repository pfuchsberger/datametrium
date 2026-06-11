"""Genera datametrium.json y lo sube a Cloudflare R2.

Corre en GitHub Actions, disparado por cron-job.org via workflow_dispatch
(mismo esquema que putvol: cron-job.org es confiable a horario fijo,
el cron interno de GitHub dropea/demora runs).

Variables de entorno necesarias (secrets del repo):
  CLOUDFLARE_ACCOUNT_ID  - Account ID de Cloudflare (dashboard, barra lateral)
  CLOUDFLARE_API_TOKEN   - API token con permiso "Workers R2 Storage: Edit"
  R2_BUCKET              - nombre del bucket R2 destino

Uso local (solo generar, sin subir):  py publicar.py --solo-generar
"""

import json
import os
import sys
from datetime import datetime, timezone

import requests
import yfinance as yf

TICKERS = ["^VIX", "UVIX", "UVXY"]
ARCHIVO = "datametrium.json"
R2_KEY = "datametrium.json"


def generar_datos():
    """Arma el dict que va al JSON.

    Reemplazar/extender aca el contenido real. El resto del pipeline
    (escritura, subida a R2, workflow) no depende de que haya adentro.
    """
    datos = {
        "generado_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cotizaciones": {},
    }
    for ticker in TICKERS:
        hist = yf.Ticker(ticker).history(period="5d")
        if hist.empty:
            print(f"AVISO: sin datos para {ticker}")
            continue
        ultimo = hist.iloc[-1]
        datos["cotizaciones"][ticker] = {
            "fecha": hist.index[-1].strftime("%Y-%m-%d"),
            "cierre": round(float(ultimo["Close"]), 4),
        }
    return datos


def subir_a_r2(path):
    """Sube el archivo a R2 con un PUT directo a la API de Cloudflare."""
    cuenta = os.environ["CLOUDFLARE_ACCOUNT_ID"]
    token = os.environ["CLOUDFLARE_API_TOKEN"]
    bucket = os.environ["R2_BUCKET"]
    url = (
        f"https://api.cloudflare.com/client/v4/accounts/{cuenta}"
        f"/r2/buckets/{bucket}/objects/{R2_KEY}"
    )
    with open(path, "rb") as f:
        resp = requests.put(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            data=f,
            timeout=60,
        )
    if not resp.ok:
        print(f"ERROR subiendo a R2 ({resp.status_code}): {resp.text}")
        resp.raise_for_status()
    print(f"Subido a R2: {bucket}/{R2_KEY}")


def main():
    datos = generar_datos()
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    print(f"{ARCHIVO} generado:")
    print(json.dumps(datos, ensure_ascii=False, indent=2))

    if "--solo-generar" in sys.argv:
        print("Modo --solo-generar: no se sube a R2.")
        return
    subir_a_r2(ARCHIVO)


if __name__ == "__main__":
    main()
