/**
 * Pine Script Development Tools
 * Write, validate, compile, and deploy Pine Script code.
 */

import { z } from "zod";
import { PineScriptService } from "../services/pine-script.js";
import { BrowserAutomation } from "../services/browser-automation.js";

export function registerPineScriptTools(
  server: any,
  pineService: PineScriptService,
  browser: BrowserAutomation
) {
  server.tool(
    "tv_pine_validate",
    "Validate Pine Script code locally — checks syntax, version, common errors",
    {
      code: z.string().describe("Pine Script code to validate"),
    },
    async ({ code }: { code: string }) => {
      const result = pineService.validate(code);
      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify(result, null, 2),
          },
        ],
      };
    }
  );

  server.tool(
    "tv_pine_generate_template",
    "Generate a Pine Script template (indicator, strategy, or library)",
    {
      type: z
        .enum(["indicator", "strategy", "library"])
        .describe("Type of Pine Script to generate"),
      name: z.string().describe("Name for the script"),
      version: z.string().optional().default("5").describe("Pine Script version (4, 5, or 6)"),
      overlay: z.boolean().optional().default(true).describe("Whether to overlay on price chart"),
    },
    async (params: {
      type: "indicator" | "strategy" | "library";
      name: string;
      version: string;
      overlay: boolean;
    }) => {
      const code = pineService.generateTemplate(params.type, params.name, {
        version: params.version,
        overlay: params.overlay,
      });
      return {
        content: [
          {
            type: "text" as const,
            text: code,
          },
        ],
      };
    }
  );

  server.tool(
    "tv_pine_generate_sapphire_strategy",
    "Generate a Sapphire-compatible Pine Script strategy with webhook alerts that match the Sapphire TradingViewSignal format",
    {
      name: z.string().describe("Strategy name"),
      webhookUrl: z.string().optional().describe("Webhook URL for Sapphire signals"),
    },
    async ({ name, webhookUrl }: { name: string; webhookUrl?: string }) => {
      const code = pineService.generateSapphireStrategy(name, { webhookUrl });
      // Also validate it
      const validation = pineService.validate(code);
      return {
        content: [
          {
            type: "text" as const,
            text: `// Validation: ${validation.valid ? "PASSED" : "FAILED"}\n// Errors: ${validation.errors.join(", ") || "none"}\n// Warnings: ${validation.warnings.join(", ") || "none"}\n\n${code}`,
          },
        ],
      };
    }
  );

  server.tool(
    "tv_pine_list_templates",
    "List all available Pine Script templates",
    {},
    async () => {
      const templates = pineService.getTemplates();
      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify(
              templates.map((t) => ({
                name: t.name,
                description: t.description,
                category: t.category,
              })),
              null,
              2
            ),
          },
        ],
      };
    }
  );

  server.tool(
    "tv_pine_open_editor",
    "Open the Pine Script editor in TradingView and read the current code",
    {},
    async () => {
      try {
        const result = await browser.openPineEditor();
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

  server.tool(
    "tv_pine_write",
    "Write Pine Script code to the TradingView Pine Editor",
    {
      code: z.string().describe("Pine Script code to write to the editor"),
    },
    async ({ code }: { code: string }) => {
      // Validate first
      const validation = pineService.validate(code);
      if (!validation.valid) {
        return {
          content: [
            {
              type: "text" as const,
              text: `Pine Script validation failed. Fix errors before deploying:\n${JSON.stringify(validation, null, 2)}`,
            },
          ],
          isError: true,
        };
      }

      try {
        const result = await browser.writePineScript(code);
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({ ...result, validation }, null, 2),
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
    "tv_pine_compile",
    "Compile the current Pine Script in the editor and add it to the chart. Reports any compilation errors.",
    {},
    async () => {
      try {
        const result = await browser.compilePineScript();
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
              text: `Compilation error: ${err instanceof Error ? err.message : String(err)}`,
            },
          ],
          isError: true,
        };
      }
    }
  );
}
