/**
 * Chart & Browser Automation Tools
 * Captures chart screenshots, manages watchlists, handles alerts via Playwright.
 */

import { z } from "zod";
import { BrowserAutomation } from "../services/browser-automation.js";

export function registerChartTools(server: any, browser: BrowserAutomation) {
  server.tool(
    "tv_capture_chart",
    "Capture a screenshot of a TradingView chart with your premium indicators and layouts. Returns base64 image.",
    {
      symbol: z.string().describe("Symbol (e.g., BINANCE:BTCUSDT, NASDAQ:AAPL)"),
      timeframe: z.string().optional().default("1D").describe("Timeframe: 1, 5, 15, 60, D, W, M"),
    },
    async ({ symbol, timeframe }: { symbol: string; timeframe: string }) => {
      try {
        const result = await browser.captureChart(symbol, timeframe);
        return {
          content: [
            {
              type: "image" as const,
              data: result.imageBase64,
              mimeType: "image/png",
            },
            {
              type: "text" as const,
              text: `Chart captured: ${result.symbol} @ ${result.timeframe} (${new Date(result.timestamp).toISOString()})`,
            },
          ],
        };
      } catch (err) {
        return {
          content: [
            {
              type: "text" as const,
              text: `Error capturing chart: ${err instanceof Error ? err.message : String(err)}`,
            },
          ],
          isError: true,
        };
      }
    }
  );

  server.tool(
    "tv_read_chart_data",
    "Read data visible on a TradingView chart — prices, indicator values, data window contents",
    {
      symbol: z.string().describe("Symbol to read chart for"),
      timeframe: z.string().optional().default("1D"),
    },
    async ({ symbol, timeframe }: { symbol: string; timeframe: string }) => {
      try {
        const data = await browser.readChartData(symbol, timeframe);
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify(data, null, 2),
            },
          ],
        };
      } catch (err) {
        return {
          content: [
            {
              type: "text" as const,
              text: `Error: ${err instanceof Error ? err.message : String(err)}`,
            },
          ],
          isError: true,
        };
      }
    }
  );

  server.tool(
    "tv_screenshot",
    "Take a screenshot of the current TradingView page (whatever is visible)",
    {},
    async () => {
      try {
        const imageBase64 = await browser.screenshot();
        return {
          content: [
            {
              type: "image" as const,
              data: imageBase64,
              mimeType: "image/png",
            },
          ],
        };
      } catch (err) {
        return {
          content: [
            {
              type: "text" as const,
              text: `Screenshot error: ${err instanceof Error ? err.message : String(err)}`,
            },
          ],
          isError: true,
        };
      }
    }
  );

  server.tool(
    "tv_navigate",
    "Navigate to a specific TradingView page (e.g., /screener, /ideas, /chart)",
    {
      path: z
        .string()
        .describe("Path or full URL (e.g., '/screener/', 'https://www.tradingview.com/ideas/')"),
    },
    async ({ path }: { path: string }) => {
      try {
        const result = await browser.navigateTo(path);
        return {
          content: [
            {
              type: "text" as const,
              text: `Navigated to: ${result.url}`,
            },
          ],
        };
      } catch (err) {
        return {
          content: [
            {
              type: "text" as const,
              text: `Navigation error: ${err instanceof Error ? err.message : String(err)}`,
            },
          ],
          isError: true,
        };
      }
    }
  );

  server.tool("tv_page_info", "Get the current TradingView page URL and title", {}, async () => {
    try {
      const info = await browser.getPageInfo();
      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify(info, null, 2),
          },
        ],
      };
    } catch (err) {
      return {
        content: [
          {
            type: "text" as const,
            text: `Error: ${err instanceof Error ? err.message : String(err)}`,
          },
        ],
        isError: true,
      };
    }
  });

  server.tool(
    "tv_execute_js",
    "Execute JavaScript on the TradingView page for advanced automation (access DOM, internal APIs)",
    {
      script: z.string().describe("JavaScript code to execute on the TradingView page"),
    },
    async ({ script }: { script: string }) => {
      try {
        const result = await browser.executeOnPage(script);
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      } catch (err) {
        return {
          content: [
            {
              type: "text" as const,
              text: `JS execution error: ${err instanceof Error ? err.message : String(err)}`,
            },
          ],
          isError: true,
        };
      }
    }
  );
}
