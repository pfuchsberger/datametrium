# datametrium

Pipeline: **GitHub Actions** (disparado por cron-job.org) genera `datametrium.json` con Python y lo sube a **Cloudflare R2**.

```
cron-job.org ──POST──▶ GitHub API (workflow_dispatch)
                            │
                            ▼
                  Actions corre publicar.py
                  (genera datametrium.json)
                            │
                            ▼
                  PUT a Cloudflare R2 (API REST)
```

## Archivos

- `publicar.py` — genera el JSON (hoy: snapshot VIX/UVIX/UVXY vía yfinance) y lo sube a R2. El contenido se cambia editando solo `generar_datos()`.
- `.github/workflows/publicar.yml` — workflow con `workflow_dispatch` (sin cron interno de GitHub).

## Setup (una sola vez)

### 1. Cloudflare

1. Dashboard → **R2** → crear bucket (ej. `datametrium`).
2. **R2 → Manage R2 API Tokens** → no — para la API REST usar: **My Profile → API Tokens → Create Token → Custom**, con permiso **Account / Workers R2 Storage / Edit**.
3. Anotar el **Account ID** (barra lateral derecha del dashboard).
4. (Opcional, para servir el JSON público) en el bucket: **Settings → Public access** → habilitar `r2.dev` o conectar un custom domain tipo `data.datametrium.com`.

### 2. Secrets del repo en GitHub

Repo → Settings → Secrets and variables → Actions → New repository secret:

| Secret | Valor |
|---|---|
| `CLOUDFLARE_ACCOUNT_ID` | Account ID de Cloudflare |
| `CLOUDFLARE_API_TOKEN` | el token del paso 1.2 |
| `R2_BUCKET` | nombre del bucket (ej. `datametrium`) |

### 3. cron-job.org

Crear un cronjob con:

- **URL:** `https://api.github.com/repos/pfuchsberger/datametrium/actions/workflows/publicar.yml/dispatches`
- **Método:** POST
- **Headers:**
  - `Authorization: Bearer <GitHub PAT con scope repo/actions>`
  - `Accept: application/vnd.github+json`
- **Body:** `{"ref":"main"}`
- **Horario:** el que quieras (timezone configurable, maneja DST).

GitHub responde `204 No Content` cuando el dispatch fue aceptado.

## Probar

- **Local (sin subir):** `py publicar.py --solo-generar`
- **Manual en GitHub:** Actions → publicar-json → Run workflow.
