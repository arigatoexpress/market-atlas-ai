#!/usr/bin/env node
/**
 * TradingView MCP Server — Unified connector for Claude Code
 *
 * Provides full agentic access to TradingView Premium:
 * - Real-time market data via WebSocket (@mathieuc/tradingview)
 * - Browser automation via Playwright (charts, alerts, Pine Script, watchlists)
 * - Pine Script development (validate, generate, compile)
 * - Webhook listener for TradingView alerts (Sapphire-compatible)
 *
 * Usage:
 *   TRADINGVIEW_SESSION_ID=xxx TRADINGVIEW_SESSION_ID_SIGN=yyy node dist/index.js
 */

import { config } from "dotenv";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

// Load .env from project root
const __dirname = dirname(fileURLToPath(import.meta.url));
config({ path: resolve(__dirname, "..", ".env") });

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

import { TradingViewClient } from "./services/tradingview-client.js";
import { BrowserAutomation } from "./services/browser-automation.js";
import { PineScriptService } from "./services/pine-script.js";
import { WebhookServer } from "./services/webhook-server.js";

import { registerMarketDataTools } from "./tools/market-data.js";
import { registerChartTools } from "./tools/chart-tools.js";
import { registerAlertTools } from "./tools/alert-tools.js";
import { registerWatchlistTools } from "./tools/watchlist-tools.js";
import { registerPineScriptTools } from "./tools/pine-script-tools.js";
import { registerWebhookTools } from "./tools/webhook-tools.js";

async function main() {
  // Load configuration from environment
  const sessionId = process.env.TRADINGVIEW_SESSION_ID || "";
  const sessionIdSign = process.env.TRADINGVIEW_SESSION_ID_SIGN || "";
  const webhookPort = parseInt(process.env.WEBHOOK_PORT || "3456");
  const webhookSecret = process.env.WEBHOOK_SECRET || "";

  if (!sessionId) {
    console.error(
      "[TradingView MCP] WARNING: TRADINGVIEW_SESSION_ID not set. " +
        "Data access will be limited to free tier. " +
        "Extract your session cookie from browser DevTools > Application > Cookies > tradingview.com"
    );
  }

  // Initialize services
  const tvClient = new TradingViewClient(sessionId, sessionIdSign);
  const browser = new BrowserAutomation(sessionId, sessionIdSign);
  const pineService = new PineScriptService();
  const webhookServer = new WebhookServer(webhookPort, webhookSecret);

  // Create MCP server
  const server = new McpServer({
    name: "tradingview-mcp",
    version: "1.0.0",
  });

  // Register all tool groups
  registerMarketDataTools(server, tvClient);
  registerChartTools(server, browser);
  registerAlertTools(server, browser);
  registerWatchlistTools(server, browser);
  registerPineScriptTools(server, pineService, browser);
  registerWebhookTools(server, webhookServer);

  // Register a status/info tool
  server.tool(
    "tv_status",
    "Get the status of the TradingView MCP server — shows connected services, session status, webhook stats",
    {},
    async () => {
      const webhookStats = webhookServer.getStats();
      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify(
              {
                server: "tradingview-mcp v1.0.0",
                session: sessionId
                  ? { authenticated: true, sessionIdPrefix: sessionId.substring(0, 8) + "..." }
                  : { authenticated: false, note: "Set TRADINGVIEW_SESSION_ID for premium access" },
                services: {
                  websocket_data: "ready",
                  browser_automation: "ready (lazy-init on first use)",
                  pine_script: "ready",
                  webhook_server: `listening on port ${webhookPort}`,
                },
                webhook: webhookStats,
                tools: [
                  "tv_get_quote",
                  "tv_get_candles",
                  "tv_get_indicators",
                  "tv_technical_analysis",
                  "tv_screen",
                  "tv_search_symbol",
                  "tv_capture_chart",
                  "tv_read_chart_data",
                  "tv_screenshot",
                  "tv_navigate",
                  "tv_page_info",
                  "tv_execute_js",
                  "tv_create_alert",
                  "tv_list_alerts",
                  "tv_get_watchlist",
                  "tv_add_to_watchlist",
                  "tv_pine_validate",
                  "tv_pine_generate_template",
                  "tv_pine_generate_sapphire_strategy",
                  "tv_pine_list_templates",
                  "tv_pine_open_editor",
                  "tv_pine_write",
                  "tv_pine_compile",
                  "tv_webhook_signals",
                  "tv_webhook_stats",
                  "tv_status",
                ],
              },
              null,
              2
            ),
          },
        ],
      };
    }
  );

  // Start webhook server in background
  try {
    await webhookServer.start();
    console.error(`[TradingView MCP] Webhook server started on port ${webhookPort}`);
  } catch (err) {
    console.error(
      `[TradingView MCP] Webhook server failed to start on port ${webhookPort}: ${err instanceof Error ? err.message : String(err)}`
    );
    console.error(
      "[TradingView MCP] Webhook tools will still work but won't receive real-time alerts"
    );
  }

  // Handle graceful shutdown
  process.on("SIGINT", async () => {
    console.error("[TradingView MCP] Shutting down...");
    await browser.close();
    await tvClient.close();
    await webhookServer.stop();
    process.exit(0);
  });

  process.on("SIGTERM", async () => {
    console.error("[TradingView MCP] Shutting down...");
    await browser.close();
    await tvClient.close();
    await webhookServer.stop();
    process.exit(0);
  });

  // Connect via stdio transport (for Claude Code MCP)
  const transport = new StdioServerTransport();
  await server.connect(transport);

  console.error("[TradingView MCP] Server connected and ready");
  console.error(
    `[TradingView MCP] Session: ${sessionId ? "authenticated (premium)" : "unauthenticated (free tier)"}`
  );
  console.error(`[TradingView MCP] 26 tools registered across 6 categories`);
}

main().catch((err) => {
  console.error("[TradingView MCP] Fatal error:", err);
  process.exit(1);
});
