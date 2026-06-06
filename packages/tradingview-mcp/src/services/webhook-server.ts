/**
 * Webhook Server for TradingView Alerts
 * Receives webhooks from TradingView and makes them available to Claude via MCP.
 * Compatible with Sapphire's TradingViewSignal format.
 */

import express, { Request, Response } from "express";
import { Server } from "http";

export interface WebhookSignal {
  symbol: string;
  action: "BUY" | "SELL" | "CLOSE";
  indicator: string;
  confidence: number;
  timeframe: string;
  price: number;
  timestamp: string;
  raw: Record<string, unknown>;
}

export class WebhookServer {
  private app: express.Application;
  private server: Server | null = null;
  private port: number;
  private secret: string;
  private signals: WebhookSignal[] = [];
  private maxSignals = 1000;
  private onSignalCallback?: (signal: WebhookSignal) => void;

  constructor(port: number = 3456, secret: string = "") {
    this.port = port;
    this.secret = secret;
    this.app = express();
    this.setupRoutes();
  }

  private setupRoutes(): void {
    this.app.use(express.json());
    this.app.use(express.text());

    // Health check
    this.app.get("/health", (_req: Request, res: Response) => {
      res.json({
        status: "ok",
        signals_count: this.signals.length,
        uptime: process.uptime(),
      });
    });

    // TradingView webhook endpoint
    this.app.post("/webhook", (req: Request, res: Response) => {
      try {
        // Validate secret if configured
        if (this.secret) {
          const providedSecret =
            req.headers["x-webhook-secret"] ||
            req.query.secret ||
            (typeof req.body === "object" ? req.body.secret : null);
          if (providedSecret !== this.secret) {
            res.status(401).json({ error: "Invalid secret" });
            return;
          }
        }

        // Parse the payload — TradingView can send JSON or plain text
        let payload: Record<string, unknown>;
        if (typeof req.body === "string") {
          try {
            payload = JSON.parse(req.body);
          } catch {
            payload = { raw_message: req.body };
          }
        } else {
          payload = req.body;
        }

        const signal = this.parseSignal(payload);
        this.signals.unshift(signal);

        // Keep signals list bounded
        if (this.signals.length > this.maxSignals) {
          this.signals = this.signals.slice(0, this.maxSignals);
        }

        // Notify callback if registered
        if (this.onSignalCallback) {
          this.onSignalCallback(signal);
        }

        console.log(
          `[Webhook] ${signal.action} ${signal.symbol} @ ${signal.price} (${signal.indicator}, conf=${signal.confidence})`
        );
        res.json({ status: "received", signal_id: this.signals.length });
      } catch (err) {
        console.error("[Webhook] Error processing:", err);
        res.status(500).json({ error: "Processing failed" });
      }
    });

    // Sapphire-compatible endpoint
    this.app.post("/sapphire/signal", (req: Request, res: Response) => {
      // Same as /webhook but explicitly for Sapphire format
      try {
        const signal = this.parseSignal(req.body);
        this.signals.unshift(signal);
        if (this.signals.length > this.maxSignals) {
          this.signals = this.signals.slice(0, this.maxSignals);
        }
        if (this.onSignalCallback) this.onSignalCallback(signal);
        res.json({ status: "received" });
      } catch (_err) {
        res.status(500).json({ error: "Processing failed" });
      }
    });

    // Get recent signals
    this.app.get("/signals", (_req: Request, res: Response) => {
      const limit = parseInt((_req.query.limit as string) || "50");
      res.json(this.signals.slice(0, limit));
    });

    // Clear signals
    this.app.delete("/signals", (_req: Request, res: Response) => {
      this.signals = [];
      res.json({ status: "cleared" });
    });
  }

  private parseSignal(payload: Record<string, unknown>): WebhookSignal {
    // Normalize symbol (BTCUSDC -> BTC-USDC)
    let symbol = String(payload.symbol || payload.ticker || "UNKNOWN");
    if (!symbol.includes("-")) {
      for (const quote of ["USDC", "USDT", "USD", "PERP"]) {
        if (symbol.endsWith(quote)) {
          symbol = symbol.slice(0, -quote.length) + "-" + quote;
          break;
        }
      }
    }

    return {
      symbol,
      action: String(payload.action || payload.side || payload.order || "UNKNOWN").toUpperCase() as
        | "BUY"
        | "SELL"
        | "CLOSE",
      indicator: String(payload.indicator || payload.strategy || payload.source || "webhook"),
      confidence: parseFloat(String(payload.confidence || payload.strength || "0.5")),
      timeframe: String(payload.timeframe || payload.interval || payload.tf || "15m"),
      price: parseFloat(String(payload.price || payload.close || "0")),
      timestamp: String(payload.timestamp || new Date().toISOString()),
      raw: payload,
    };
  }

  onSignal(callback: (signal: WebhookSignal) => void): void {
    this.onSignalCallback = callback;
  }

  getRecentSignals(limit: number = 50): WebhookSignal[] {
    return this.signals.slice(0, limit);
  }

  getSignalsBySymbol(symbol: string, limit: number = 20): WebhookSignal[] {
    return this.signals.filter((s) => s.symbol.includes(symbol.toUpperCase())).slice(0, limit);
  }

  getStats(): Record<string, unknown> {
    const symbolCounts: Record<string, number> = {};
    const actionCounts: Record<string, number> = {};
    for (const s of this.signals) {
      symbolCounts[s.symbol] = (symbolCounts[s.symbol] || 0) + 1;
      actionCounts[s.action] = (actionCounts[s.action] || 0) + 1;
    }
    return {
      total_signals: this.signals.length,
      by_symbol: symbolCounts,
      by_action: actionCounts,
      latest: this.signals[0] || null,
      server_port: this.port,
    };
  }

  async start(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.server = this.app.listen(this.port, "127.0.0.1", () => {
        console.error(`[Webhook] TradingView webhook server listening on port ${this.port}`);
        resolve();
      });
      this.server.on("error", (err: NodeJS.ErrnoException) => {
        if (err.code === "EADDRINUSE") {
          console.error(`[Webhook] Port ${this.port} already in use — webhook server disabled`);
          this.server = null;
          resolve(); // Don't crash, just skip the webhook server
        } else {
          reject(err);
        }
      });
    });
  }

  async stop(): Promise<void> {
    return new Promise((resolve) => {
      if (this.server) {
        this.server.close(() => resolve());
      } else {
        resolve();
      }
    });
  }
}
