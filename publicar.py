"""Genera datametrium.json con la curva de futuros de VIX de la CBOE.

Corre en GitHub Actions, disparado por cron-job.org via workflow_dispatch
(mismo esquema que putvol: cron-job.org es confiable a horario fijo,
el cron interno de GitHub dropea/demora runs). El workflow commitea el
JSON resultante de vuelta al repo.
"""

import csv
import io
import json
from datetime import datetime, timedelta, timezone

import requests

ARCHIVO = "datametrium.json"

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


def main():
    datos = generar_datos()
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    print(f"{ARCHIVO} generado:")
    print(json.dumps(datos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
