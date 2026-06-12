# datametrium

Pipeline: **GitHub Actions** (disparado por cron-job.org) genera `datametrium.json` con la curva de futuros de VIX de la CBOE y lo **commitea de vuelta al repo**.

```
cron-job.org ──POST──▶ GitHub API (workflow_dispatch)
                            │
                            ▼
                  Actions corre publicar.py
                  (genera datametrium.json)
                            │
                            ▼
                  git commit + push del JSON al repo
```

## Archivos

- `publicar.py` — lee **toda la curva de futuros de VIX (VX)** del settlement diario de la CBOE y la guarda en `datametrium.json`. El contenido se cambia editando solo `generar_datos()`.
- `.github/workflows/publicar.yml` — workflow con `workflow_dispatch` que genera y commitea el JSON (sin cron interno de GitHub).
- `datametrium.json` — salida, versionada en el repo. Accesible vía raw:
  `https://raw.githubusercontent.com/pfuchsberger/datametrium/main/datametrium.json`

## Fuente de datos

Endpoint público de settlement de la CBOE (CSV, todos los contratos de futuros):

```
https://www-api.cboe.com/us/futures/market_statistics/settlement/csv?dt=YYYY-MM-DD
```

Se filtra `Product == "VX"` → curva completa (mensuales + semanales) con `symbol`, `vencimiento`, `dias_al_vto` y `precio`. El settlement sale ~10:00 CT del día hábil siguiente; el script retrocede hasta 7 días para tomar el más reciente disponible.

## Setup (una sola vez): cron-job.org

Crear un cronjob con:

- **URL:** `https://api.github.com/repos/pfuchsberger/datametrium/actions/workflows/publicar.yml/dispatches`
- **Método:** POST
- **Headers:**
  - `Authorization: Bearer <GitHub PAT con scope repo/actions>`
  - `Accept: application/vnd.github+json`
- **Body:** `{"ref":"main"}`
- **Horario:** recomendado media mañana CT (el settlement del día anterior ya está publicado). Timezone configurable, maneja DST.

GitHub responde `204 No Content` cuando el dispatch fue aceptado.

## Probar

- **Local:** `py publicar.py` → genera `datametrium.json`.
- **Manual en GitHub:** Actions → publicar-json → Run workflow.
