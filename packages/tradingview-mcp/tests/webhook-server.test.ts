import { describe, expect, it, beforeEach, vi } from "vitest";
import request from "supertest";
import { WebhookServer } from "../src/services/webhook-server.js";

describe("WebhookServer", () => {
  let webhook: WebhookServer;

  beforeEach(() => {
    webhook = new WebhookServer(3456, "");
  });

  describe("GET /health", () => {
    it("returns ok status with signal count and uptime", async () => {
      const res = await request((webhook as any)["app"])
        .get("/health")
        .expect(200);
      expect(res.body.status).toBe("ok");
      expect(res.body).toHaveProperty("signals_count");
      expect(res.body).toHaveProperty("uptime");
    });
  });

  describe("POST /webhook", () => {
    it("accepts a JSON payload and stores the signal", async () => {
      const payload = {
        symbol: "BTCUSDT",
        action: "BUY",
        indicator: "RSI",
        confidence: 0.85,
        timeframe: "15m",
        price: 42000,
        timestamp: "2024-01-01T00:00:00Z",
      };

      const res = await request((webhook as any)["app"])
        .post("/webhook")
        .send(payload)
        .expect(200);

      expect(res.body.status).toBe("received");
      expect(webhook.getRecentSignals(1)).toHaveLength(1);
    });

    it("accepts a plain text payload and wraps it", async () => {
      const res = await request((webhook as any)["app"])
        .post("/webhook")
        .set("Content-Type", "text/plain")
        .send('{"symbol":"ETHUSDT","action":"SELL"}')
        .expect(200);

      expect(res.body.status).toBe("received");
    });

    it("rejects requests with invalid secret", async () => {
      const secured = new WebhookServer(3457, "supersecret");
      const res = await request((secured as any)["app"])
        .post("/webhook")
        .send({ symbol: "BTCUSDT", action: "BUY" })
        .expect(401);

      expect(res.body.error).toBe("Invalid secret");
    });

    it("accepts requests with valid secret in header", async () => {
      const secured = new WebhookServer(3457, "supersecret");
      const res = await request((secured as any)["app"])
        .post("/webhook")
        .set("x-webhook-secret", "supersecret")
        .send({ symbol: "BTCUSDT", action: "BUY" })
        .expect(200);

      expect(res.body.status).toBe("received");
    });

    it("normalizes symbol by inserting dash for common quote currencies", async () => {
      await request((webhook as any)["app"])
        .post("/webhook")
        .send({ symbol: "BTCUSDT", action: "BUY" })
        .expect(200);

      const signals = webhook.getRecentSignals(1);
      expect(signals[0].symbol).toBe("BTC-USDT");
    });

    it("does not double-insert dash if symbol already contains one", async () => {
      await request((webhook as any)["app"])
        .post("/webhook")
        .send({ symbol: "BTC-USDT", action: "BUY" })
        .expect(200);

      const signals = webhook.getRecentSignals(1);
      expect(signals[0].symbol).toBe("BTC-USDT");
    });

    it("defaults unknown action to UNKNOWN", async () => {
      await request((webhook as any)["app"])
        .post("/webhook")
        .send({ symbol: "AAPL" })
        .expect(200);

      const signals = webhook.getRecentSignals(1);
      expect(signals[0].action).toBe("UNKNOWN");
    });
  });

  describe("POST /sapphire/signal", () => {
    it("stores a Sapphire-formatted signal", async () => {
      const res = await request((webhook as any)["app"])
        .post("/sapphire/signal")
        .send({ symbol: "SOLUSDC", action: "CLOSE", strategy: "MyStrat" })
        .expect(200);

      expect(res.body.status).toBe("received");
      expect(webhook.getSignalsBySymbol("SOL")).toHaveLength(1);
    });
  });

  describe("GET /signals", () => {
    it("returns recent signals with a limit", async () => {
      for (let i = 0; i < 5; i++) {
        await request((webhook as any)["app"])
          .post("/webhook")
          .send({ symbol: `SYM${i}`, action: "BUY" });
      }

      const res = await request((webhook as any)["app"])
        .get("/signals?limit=3")
        .expect(200);
      expect(res.body).toHaveLength(3);
    });
  });

  describe("DELETE /signals", () => {
    it("clears all stored signals", async () => {
      await request((webhook as any)["app"])
        .post("/webhook")
        .send({ symbol: "BTCUSDT", action: "BUY" });

      await request((webhook as any)["app"])
        .delete("/signals")
        .expect(200);
      expect(webhook.getRecentSignals()).toHaveLength(0);
    });
  });

  describe("getStats", () => {
    it("aggregates signals by symbol and action", async () => {
      await request((webhook as any)["app"])
        .post("/webhook")
        .send({ symbol: "BTCUSDT", action: "BUY" });
      await request((webhook as any)["app"])
        .post("/webhook")
        .send({ symbol: "BTCUSDT", action: "SELL" });

      const stats = webhook.getStats();
      expect(stats.total_signals).toBe(2);
      expect((stats as any).by_action).toEqual({ BUY: 1, SELL: 1 });
      expect((stats as any).by_symbol).toHaveProperty("BTC-USDT");
    });
  });

  describe("onSignal callback", () => {
    it("fires the registered callback when a signal is received", async () => {
      const cb = vi.fn();
      webhook.onSignal(cb);

      await request((webhook as any)["app"])
        .post("/webhook")
        .send({ symbol: "BTCUSDT", action: "BUY" });

      expect(cb).toHaveBeenCalledOnce();
      expect(cb).toHaveBeenCalledWith(
        expect.objectContaining({
          symbol: "BTC-USDT",
          action: "BUY",
        })
      );
    });
  });
});
