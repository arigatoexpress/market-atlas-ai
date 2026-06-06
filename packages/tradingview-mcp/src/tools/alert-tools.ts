/**
 * Alert Management Tools
 * Create, list, and manage TradingView alerts via browser automation.
 */

import { z } from "zod";
import { BrowserAutomation } from "../services/browser-automation.js";

export function registerAlertTools(server: any, browser: BrowserAutomation) {
  server.tool(
    "tv_create_alert",
    "Create a TradingView alert for a symbol. Can optionally set a webhook URL for Sapphire integration.",
    {
      symbol: z.string().describe("Symbol to set alert on (e.g., BINANCE:BTCUSDT)"),
      condition: z
        .string()
        .describe("Alert condition description (e.g., 'crossing', 'greater than')"),
      value: z.number().describe("Alert trigger value/price"),
      message: z
        .string()
        .describe("Alert message — use Sapphire JSON format for webhook integration"),
      webhookUrl: z.string().optional().describe("Webhook URL to send alert to (for Sapphire)"),
      expiration: z.string().optional().describe("Alert expiration (e.g., 'Once', 'Every time')"),
    },
    async (params: {
      symbol: string;
      condition: string;
      value: number;
      message: string;
      webhookUrl?: string;
      expiration?: string;
    }) => {
      try {
        const result = await browser.createAlert(params);
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
              text: `Alert creation error: ${err instanceof Error ? err.message : String(err)}`,
            },
          ],
          isError: true,
        };
      }
    }
  );

  server.tool("tv_list_alerts", "List all active TradingView alerts", {}, async () => {
    try {
      const alerts = await browser.listAlerts();
      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify({ count: alerts.length, alerts }, null, 2),
          },
        ],
      };
    } catch (err) {
      return {
        content: [
          {
            type: "text" as const,
            text: `Error listing alerts: ${err instanceof Error ? err.message : String(err)}`,
          },
        ],
        isError: true,
      };
    }
  });
}
