/**
 * Watchlist Management Tools
 */

import { z } from "zod";
import { BrowserAutomation } from "../services/browser-automation.js";

export function registerWatchlistTools(server: any, browser: BrowserAutomation) {
  server.tool(
    "tv_get_watchlist",
    "Get the current TradingView watchlist contents",
    {},
    async () => {
      try {
        const items = await browser.getWatchlist();
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({ count: items.length, items }, null, 2),
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
    "tv_add_to_watchlist",
    "Add a symbol to the TradingView watchlist",
    {
      symbol: z.string().describe("Symbol to add (e.g., BINANCE:ETHUSDT)"),
    },
    async ({ symbol }: { symbol: string }) => {
      try {
        const result = await browser.addToWatchlist(symbol);
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
              text: `Error: ${err instanceof Error ? err.message : String(err)}`,
            },
          ],
          isError: true,
        };
      }
    }
  );
}
