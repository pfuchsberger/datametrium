# datametrium-mcp

Servidor **MCP remoto** (Cloudflare Worker) que expone la curva de futuros de VIX. Lee el `datametrium.json` que el pipeline (`../publicar.py`) publica en **R2** y lo sirve como tool MCP.

```
cliente MCP ──/mcp (Streamable HTTP)──▶ Worker (McpAgent) ──get──▶ R2: datametrium.json
```

Sin autenticación (authless): cualquiera con la URL puede llamarlo. La curva VIX es dato público.

## Tools

- **`get_vix_curve`** — devuelve el JSON completo de la curva (todos los contratos VX con symbol, vencimiento, días al vto y precio de settlement).

## Endpoints del Worker

- `POST /mcp` — transporte **Streamable HTTP** (el recomendado).
- `GET /sse` — transporte SSE (compatibilidad con clientes viejos).

## Desarrollo local

```sh
npm install
# sembrar un objeto en el R2 local para probar el tool:
npx wrangler r2 object put datametrium/datametrium.json --file=../datametrium.json --local
npm run dev          # http://127.0.0.1:8787/mcp
```

## Deploy

Requiere una sola vez: `npx wrangler login` (cuenta Cloudflare) y que exista el bucket R2 `datametrium` (mismo que usa `publicar.py`).

```sh
npm run deploy
```

Queda en `https://datametrium-mcp.<tu-subdominio>.workers.dev/mcp`. Para custom domain (ej. `mcp.datametrium.com`) agregar la ruta en el dashboard del Worker.

## Conectar desde un cliente MCP

URL del server: `https://datametrium-mcp.<tu-subdominio>.workers.dev/mcp`

En Claude Code:

```sh
claude mcp add --transport http datametrium https://datametrium-mcp.<tu-subdominio>.workers.dev/mcp
```
