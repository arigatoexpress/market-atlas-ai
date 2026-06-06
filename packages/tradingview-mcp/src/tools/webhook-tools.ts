/**
 * Webhook & Signal Tools
 * Query received TradingView webhook signals and manage the webhook server.
 */

import { z } from "zod";
import { WebhookServer } from "../services/webhook-server.js";

export function registerWebhookTools(server: any, webhookServer: WebhookServer) {
  server.tool(
    "tv_webhook_signals",
    "Get recent TradingView webhook signals received by the listener. These are real-time alerts from your TV strategies.",
    {
      limit: z.number().optional().default(20).describe("Max signals to return"),
      symbol: z.string().optional().describe("Filter by symbol (e.g., BTC)"),
    },
    async ({ limit, symbol }: { limit: number; symbol?: string }) => {
      const signals = symbol
        ? webhookServer.getSignalsBySymbol(symbol, limit)
        : webhookServer.getRecentSignals(limit);
      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify({ count: signals.length, signals }, null, 2),
          },
        ],
      };
    }
  );

  server.tool(
    "tv_webhook_stats",
    "Get statistics about received webhook signals — counts by symbol, action, latest signal",
    {},
    async () => {
      const stats = webhookServer.getStats();
      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify(stats, null, 2),
          },
        ],
      };
    }
  );
}
