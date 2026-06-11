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

import csv
import io
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import requests

ARCHIVO = "datametrium.json"
R2_KEY = "datametrium.json"

# Endpoint de settlement diario de la CBOE: devuelve un CSV con el precio de
# settlement de TODOS los contratos de futuros listados (Product,Symbol,
# Expiration Date,Price) para la fecha de trading ?dt=YYYY-MM-DD. Los datos
# salen ~10:00 CT del dia habil siguiente. Filtramos Product == "VX" para
# quedarnos con la curva completa de futuros de VIX (mensuales + semanales).
CBOE_SETTLEMENT = "https://www-api.cboe.com/us/futures/market_statistics/settlement/csv"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


def _bajar_settlement(dt):
    """Devuelve las filas VX del settlement de la fecha dt, o [] si no hay."""
    resp = requests.get(
        CBOE_SETTLEMENT,
        params={"dt": dt.isoformat()},
        headers={"User-Agent": UA},
        timeout=60,
    )
    resp.raise_for_status()
    filas = list(csv.DictReader(io.StringIO(resp.text)))
    return [f for f in filas if f.get("Product") == "VX"]


def generar_datos():
    """Lee la curva de futuros de VIX de la CBOE y arma el dict del JSON.

    Busca el settlement mas reciente disponible: prueba hoy y retrocede dia a
    dia (cubre fin de semana / feriados / lag de publicacion).
    """
    hoy = datetime.now(timezone.utc).date()
    filas, fecha_settle = None, None
    for atras in range(7):
        dt = hoy - timedelta(days=atras)
        vx = _bajar_settlement(dt)
        if vx:
            filas, fecha_settle = vx, dt
            break
    if not filas:
        raise RuntimeError("CBOE no devolvio datos VX en los ultimos 7 dias")

    curva = []
    for f in filas:
        venc = datetime.strptime(f["Expiration Date"], "%Y-%m-%d").date()
        curva.append({
            "symbol": f["Symbol"],
            "vencimiento": f["Expiration Date"],
            "dias_al_vto": (venc - fecha_settle).days,
            "precio": float(f["Price"]),
        })
    curva.sort(key=lambda c: c["vencimiento"])

    return {
        "fuente": "CBOE settlement",
        "fecha_settlement": fecha_settle.isoformat(),
        "generado_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_contratos": len(curva),
        "curva": curva,
    }


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
