/**
 * Market Data Tools — Real-time prices, candles, indicators, screener
 */

import { z } from "zod";
import { TradingViewClient } from "../services/tradingview-client.js";

export function registerMarketDataTools(server: any, tvClient: TradingViewClient) {
  server.tool(
    "tv_get_quote",
    "Get real-time quote/price data for a symbol (e.g., BINANCE:BTCUSDT, NASDAQ:AAPL)",
    { symbol: z.string().describe("TradingView symbol (e.g., BINANCE:BTCUSDT, NASDAQ:AAPL)") },
    async ({ symbol }: { symbol: string }) => {
      try {
        const data = await tvClient.getQuote(symbol);
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
              text: `Error getting quote for ${symbol}: ${err instanceof Error ? err.message : String(err)}`,
            },
          ],
          isError: true,
        };
      }
    }
  );

  server.tool(
    "tv_get_candles",
    "Get OHLCV candlestick history for a symbol. Returns array of {time, open, high, low, close, volume}.",
    {
      symbol: z.string().describe("TradingView symbol (e.g., BINANCE:BTCUSDT)"),
      timeframe: z
        .string()
        .optional()
        .default("1D")
        .describe("Timeframe: 1, 5, 15, 30, 60, 240, 1D, 1W, 1M"),
      count: z.number().optional().default(100).describe("Number of candles to fetch (max 500)"),
    },
    async ({ symbol, timeframe, count }: { symbol: string; timeframe: string; count: number }) => {
      try {
        const candles = await tvClient.getCandles(symbol, timeframe, Math.min(count, 500));
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify(
                {
                  symbol,
                  timeframe,
                  count: candles.length,
                  candles: candles.slice(0, 20), // Return first 20 for readability
                  summary: {
                    latest_close: candles[candles.length - 1]?.close,
                    period_high: Math.max(...candles.map((c) => c.high)),
                    period_low: Math.min(...candles.map((c) => c.low)),
                    avg_volume: candles.reduce((s, c) => s + c.volume, 0) / candles.length,
                  },
                  _note:
                    candles.length > 20
                      ? `Showing first 20 of ${candles.length} candles. Full data available.`
                      : undefined,
                },
                null,
                2
              ),
            },
          ],
        };
      } catch (err) {
        return {
          content: [
            {
              type: "text" as const,
              text: `Error getting candles: ${err instanceof Error ? err.message : String(err)}`,
            },
          ],
          isError: true,
        };
      }
    }
  );

  server.tool(
    "tv_get_indicators",
    "Get technical indicator values for a symbol from TradingView (RSI, MACD, Stochastic, etc.)",
    {
      symbol: z.string().describe("TradingView symbol"),
      timeframe: z.string().optional().default("1D").describe("Timeframe"),
    },
    async ({ symbol, timeframe }: { symbol: string; timeframe: string }) => {
      try {
        const data = await tvClient.getIndicators(symbol, timeframe);
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
              text: `Error getting indicators: ${err instanceof Error ? err.message : String(err)}`,
            },
          ],
          isError: true,
        };
      }
    }
  );

  server.tool(
    "tv_technical_analysis",
    "Get TradingView's technical analysis summary — BUY/SELL/NEUTRAL recommendations from oscillators and moving averages",
    {
      symbol: z.string().describe("Symbol ticker (e.g., BTCUSDT)"),
      screener: z
        .string()
        .optional()
        .default("crypto")
        .describe("Screener: crypto, america, forex"),
      exchange: z
        .string()
        .optional()
        .default("BINANCE")
        .describe("Exchange: BINANCE, NASDAQ, etc."),
    },
    async ({
      symbol,
      screener,
      exchange,
    }: {
      symbol: string;
      screener: string;
      exchange: string;
    }) => {
      try {
        const data = await tvClient.getTechnicalAnalysis(symbol, screener, exchange);
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
    "tv_screen",
    "Screen/scan for symbols using TradingView's screener. Find top gainers, losers, volume leaders, etc.",
    {
      screener: z
        .string()
        .optional()
        .default("crypto")
        .describe("Market: crypto, america, forex, cfd"),
      sortBy: z
        .string()
        .optional()
        .default("volume")
        .describe("Sort by: volume, change, market_cap"),
      limit: z.number().optional().default(20).describe("Max results"),
    },
    async ({ screener, sortBy, limit }: { screener: string; sortBy: string; limit: number }) => {
      try {
        const results = await tvClient.screen(screener, [], sortBy, limit);
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({ screener, sortBy, count: results.length, results }, null, 2),
            },
          ],
        };
      } catch (err) {
        return {
          content: [
            {
              type: "text" as const,
              text: `Screener error: ${err instanceof Error ? err.message : String(err)}`,
            },
          ],
          isError: true,
        };
      }
    }
  );

  server.tool(
    "tv_search_symbol",
    "Search for a symbol on TradingView by name or ticker",
    {
      query: z.string().describe("Search query (e.g., 'bitcoin', 'AAPL', 'ethereum')"),
      type: z
        .string()
        .optional()
        .default("")
        .describe("Filter by type: stock, crypto, forex, index, futures"),
    },
    async ({ query, type }: { query: string; type: string }) => {
      try {
        const results = await tvClient.searchSymbol(query, type);
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify(results, null, 2),
            },
          ],
        };
      } catch (err) {
        return {
          content: [
            {
              type: "text" as const,
              text: `Search error: ${err instanceof Error ? err.message : String(err)}`,
            },
          ],
          isError: true,
        };
      }
    }
  );
}
