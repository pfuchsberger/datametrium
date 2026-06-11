import { McpAgent } from "agents/mcp";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

interface Env {
  DATA: R2Bucket;
  MCP_OBJECT: DurableObjectNamespace;
}

const R2_KEY = "datametrium.json";

export class DatametriumMCP extends McpAgent<Env> {
  server = new McpServer({ name: "datametrium-mcp", version: "1.0.0" });

  async init() {
    this.server.tool(
      "get_vix_curve",
      "Devuelve la curva completa de futuros de VIX (VX) con el precio de " +
        "settlement diario de la CBOE: cada contrato con su symbol, fecha de " +
        "vencimiento, dias al vencimiento y precio. Datos EOD del settlement " +
        "mas reciente publicado.",
      {},
      async () => {
        const obj = await this.env.DATA.get(R2_KEY);
        if (!obj) {
          return {
            isError: true,
            content: [
              { type: "text", text: `No se encontro ${R2_KEY} en R2.` },
            ],
          };
        }
        const text = await obj.text();
        return { content: [{ type: "text", text }] };
      },
    );
  }
}

export default {
  fetch(request: Request, env: Env, ctx: ExecutionContext) {
    const url = new URL(request.url);
    if (url.pathname === "/mcp") {
      return DatametriumMCP.serve("/mcp").fetch(request, env, ctx);
    }
    if (url.pathname === "/sse" || url.pathname === "/sse/message") {
      return DatametriumMCP.serveSSE("/sse").fetch(request, env, ctx);
    }
    return new Response("datametrium-mcp: endpoint MCP en /mcp", {
      status: 404,
    });
  },
};
