import { describe, expect, it, vi } from "vitest";

import { registerMarketDataTools } from "../src/tools/market-data.js";
import { registerChartTools } from "../src/tools/chart-tools.js";
import { registerAlertTools } from "../src/tools/alert-tools.js";
import { registerWatchlistTools } from "../src/tools/watchlist-tools.js";
import { registerPineScriptTools } from "../src/tools/pine-script-tools.js";
import { registerWebhookTools } from "../src/tools/webhook-tools.js";

function createMockMcpServer() {
  const tools: Array<{ name: string; schema: unknown }> = [];
  return {
    tool: vi.fn((name: string, _description: string, schema: unknown, _handler: unknown) => {
      tools.push({ name, schema });
    }),
    getTools: () => tools,
  };
}

describe("MCP Tool Registration", () => {
  it("registers all market data tools", () => {
    const server = createMockMcpServer();
    const mockClient = {
      getQuote: vi.fn(),
      getCandles: vi.fn(),
      getIndicators: vi.fn(),
      getTechnicalAnalysis: vi.fn(),
      screen: vi.fn(),
      searchSymbol: vi.fn(),
    } as unknown as import("../src/services/tradingview-client.js").TradingViewClient;

    registerMarketDataTools(server, mockClient);
    expect(server.getTools().map((t) => t.name)).toEqual(
      expect.arrayContaining([
        "tv_get_quote",
        "tv_get_candles",
        "tv_get_indicators",
        "tv_technical_analysis",
        "tv_screen",
        "tv_search_symbol",
      ])
    );
  });

  it("registers all chart tools", () => {
    const server = createMockMcpServer();
    const mockBrowser = {
      captureChart: vi.fn(),
      readChartData: vi.fn(),
      screenshot: vi.fn(),
      navigateTo: vi.fn(),
      getPageInfo: vi.fn(),
      executeOnPage: vi.fn(),
    } as unknown as import("../src/services/browser-automation.js").BrowserAutomation;

    registerChartTools(server, mockBrowser);
    expect(server.getTools().map((t) => t.name)).toEqual(
      expect.arrayContaining([
        "tv_capture_chart",
        "tv_read_chart_data",
        "tv_screenshot",
        "tv_navigate",
        "tv_page_info",
        "tv_execute_js",
      ])
    );
  });

  it("registers all alert tools", () => {
    const server = createMockMcpServer();
    const mockBrowser = {
      createAlert: vi.fn(),
      listAlerts: vi.fn(),
    } as unknown as import("../src/services/browser-automation.js").BrowserAutomation;

    registerAlertTools(server, mockBrowser);
    expect(server.getTools().map((t) => t.name)).toEqual(
      expect.arrayContaining(["tv_create_alert", "tv_list_alerts"])
    );
  });

  it("registers all watchlist tools", () => {
    const server = createMockMcpServer();
    const mockBrowser = {
      getWatchlist: vi.fn(),
      addToWatchlist: vi.fn(),
    } as unknown as import("../src/services/browser-automation.js").BrowserAutomation;

    registerWatchlistTools(server, mockBrowser);
    expect(server.getTools().map((t) => t.name)).toEqual(
      expect.arrayContaining(["tv_get_watchlist", "tv_add_to_watchlist"])
    );
  });

  it("registers all pine script tools", () => {
    const server = createMockMcpServer();
    const mockPine = {
      validate: vi.fn(),
      generateTemplate: vi.fn(),
      generateSapphireStrategy: vi.fn(),
      getTemplates: vi.fn(),
    } as unknown as import("../src/services/pine-script.js").PineScriptService;
    const mockBrowser = {
      openPineEditor: vi.fn(),
      writePineScript: vi.fn(),
      compilePineScript: vi.fn(),
    } as unknown as import("../src/services/browser-automation.js").BrowserAutomation;

    registerPineScriptTools(server, mockPine, mockBrowser);
    expect(server.getTools().map((t) => t.name)).toEqual(
      expect.arrayContaining([
        "tv_pine_validate",
        "tv_pine_generate_template",
        "tv_pine_generate_sapphire_strategy",
        "tv_pine_list_templates",
        "tv_pine_open_editor",
        "tv_pine_write",
        "tv_pine_compile",
      ])
    );
  });

  it("registers all webhook tools", () => {
    const server = createMockMcpServer();
    const mockWebhook = {
      getRecentSignals: vi.fn(),
      getSignalsBySymbol: vi.fn(),
      getStats: vi.fn(),
    } as unknown as import("../src/services/webhook-server.js").WebhookServer;

    registerWebhookTools(server, mockWebhook);
    expect(server.getTools().map((t) => t.name)).toEqual(
      expect.arrayContaining(["tv_webhook_signals", "tv_webhook_stats"])
    );
  });
});
