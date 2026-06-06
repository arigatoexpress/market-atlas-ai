import { describe, expect, it, vi, beforeEach } from "vitest";
import { TradingViewClient } from "../src/services/tradingview-client.js";
import { BrowserAutomation } from "../src/services/browser-automation.js";

// ─── Mock @mathieuc/tradingview ───
const mockChart = {
  setMarket: vi.fn(),
  onUpdate: vi.fn((cb: () => void) => cb()),
  periods: [
    {
      time: 1704067200,
      open: 100,
      close: 110,
      max: 115,
      min: 95,
      volume: 1000,
    },
  ],
  delete: vi.fn(),
  Study: vi.fn().mockImplementation(() => ({
    onUpdate: vi.fn((cb: () => void) => cb()),
    periods: [{ K: 50, D: 45 }],
  })),
};

const mockTvClient = {
  Session: {
    Chart: vi.fn().mockImplementation(() => mockChart),
  },
  end: vi.fn(),
};

vi.mock("@mathieuc/tradingview", () => ({
  default: {
    Client: vi.fn().mockImplementation(() => mockTvClient),
    getScreener: vi
      .fn()
      .mockResolvedValue([{ s: "BTCUSDT", exchange: "BINANCE", close: 42000, volume: 1e9 }]),
    searchMarket: vi
      .fn()
      .mockResolvedValue([
        { symbol: "BTCUSDT", exchange: "BINANCE", type: "crypto", description: "Bitcoin" },
      ]),
  },
}));

// ─── Mock Playwright ───
const mockPage = {
  goto: vi.fn().mockResolvedValue(undefined),
  waitForSelector: vi.fn().mockResolvedValue(undefined),
  waitForTimeout: vi.fn().mockResolvedValue(undefined),
  click: vi.fn().mockResolvedValue(undefined),
  keyboard: {
    press: vi.fn().mockResolvedValue(undefined),
    type: vi.fn().mockResolvedValue(undefined),
  },
  screenshot: vi.fn().mockResolvedValue(Buffer.from("fake-screenshot")),
  evaluate: vi.fn().mockResolvedValue({}),
  url: vi.fn().mockReturnValue("https://www.tradingview.com/chart/?symbol=BINANCE%3ABTCUSDT"),
  title: vi.fn().mockResolvedValue("BTCUSDT — TradingView"),
  isClosed: vi.fn().mockReturnValue(false),
  close: vi.fn().mockResolvedValue(undefined),
  $: vi.fn().mockResolvedValue(null),
};

const mockContext = {
  newPage: vi.fn().mockResolvedValue(mockPage),
  addCookies: vi.fn().mockResolvedValue(undefined),
  close: vi.fn().mockResolvedValue(undefined),
};

const mockBrowser = {
  newContext: vi.fn().mockResolvedValue(mockContext),
  close: vi.fn().mockResolvedValue(undefined),
};

vi.mock("playwright", () => ({
  chromium: {
    launch: vi.fn().mockImplementation(() => Promise.resolve(mockBrowser)),
  },
}));

describe("TradingViewClient", () => {
  let client: TradingViewClient;

  beforeEach(() => {
    client = new TradingViewClient("test-session", "test-sign");
    vi.clearAllMocks();
  });

  describe("getQuote", () => {
    it("resolves with market data from the latest period", async () => {
      const data = await client.getQuote("BINANCE:BTCUSDT");
      expect(data.symbol).toBe("BINANCE:BTCUSDT");
      expect(data.price).toBe(110);
      expect(data.change).toBe(10);
      expect(data.volume).toBe(1000);
    });
  });

  describe("getCandles", () => {
    it("returns an array of candle data", async () => {
      const candles = await client.getCandles("BINANCE:BTCUSDT", "1D", 10);
      expect(candles).toHaveLength(1);
      expect(candles[0]).toMatchObject({
        open: 100,
        high: 115,
        low: 95,
        close: 110,
        volume: 1000,
      });
    });
  });

  describe("getIndicators", () => {
    it("returns indicator values", async () => {
      const result = await client.getIndicators("BINANCE:BTCUSDT", "1D");
      expect(result.symbol).toBe("BINANCE:BTCUSDT");
      expect(result.indicators).toHaveProperty("K", 50);
    });
  });

  describe("searchSymbol", () => {
    it("returns mapped search results", async () => {
      const results = await client.searchSymbol("bitcoin", "crypto");
      expect(results).toHaveLength(1);
      expect(results[0].symbol).toBe("BTCUSDT");
      expect(results[0].description).toBe("Bitcoin");
    });
  });

  describe("screen", () => {
    it("returns screener results mapped to ScreenerResult shape", async () => {
      const results = await client.screen("crypto", [], "volume", 10);
      expect(results).toHaveLength(1);
      expect(results[0].symbol).toBe("BTCUSDT");
    });
  });

  describe("close", () => {
    it("ends the client without error", async () => {
      await client.close();
      expect(true).toBe(true);
    });
  });
});

describe("BrowserAutomation", () => {
  let browser: BrowserAutomation;

  beforeEach(() => {
    browser = new BrowserAutomation("session-id", "session-sign");
    vi.clearAllMocks();
  });

  describe("captureChart", () => {
    it("constructs the correct TradingView chart URL from symbol and timeframe", async () => {
      const result = await browser.captureChart("BINANCE:BTCUSDT", "4H");

      expect(mockPage.goto).toHaveBeenCalledWith(
        "https://www.tradingview.com/chart/?symbol=BINANCE%3ABTCUSDT&interval=4H",
        expect.any(Object)
      );
      expect(result.symbol).toBe("BINANCE:BTCUSDT");
      expect(result.timeframe).toBe("4H");
      expect(result.imageBase64).toBeDefined();
    });
  });

  describe("readChartData", () => {
    it("extracts DOM data via page.evaluate with expected selectors", async () => {
      mockPage.evaluate.mockResolvedValueOnce({
        lastPrice: "42000.00",
        dataWindow: "O 41800 H 42100 L 41700 C 42000",
        indicators: ["RSI: 55"],
      });

      const data = await browser.readChartData("BINANCE:ETHUSDT", "1H");
      expect(mockPage.goto).toHaveBeenCalledWith(
        expect.stringContaining("symbol=BINANCE%3AETHUSDT"),
        expect.any(Object)
      );
      expect(data.lastPrice).toBe("42000.00");
      expect(data.indicators).toEqual(["RSI: 55"]);
    });
  });

  describe("navigateTo", () => {
    it("prefixes relative paths with tradingview.com", async () => {
      await browser.navigateTo("/screener/");
      expect(mockPage.goto).toHaveBeenCalledWith(
        "https://www.tradingview.com/screener/",
        expect.any(Object)
      );
    });

    it("uses absolute URLs as-is", async () => {
      await browser.navigateTo("https://example.com");
      expect(mockPage.goto).toHaveBeenCalledWith("https://example.com", expect.any(Object));
    });
  });

  describe("getPageInfo", () => {
    it("returns current url and title from the page", async () => {
      const info = await browser.getPageInfo();
      expect(info.url).toBe("https://www.tradingview.com/chart/?symbol=BINANCE%3ABTCUSDT");
      expect(info.title).toBe("BTCUSDT — TradingView");
    });
  });

  describe("close", () => {
    it("closes page, context, and browser gracefully", async () => {
      await browser.getPageInfo(); // ensure browser is initialized
      await browser.close();
      expect(mockPage.close).toHaveBeenCalled();
      expect(mockContext.close).toHaveBeenCalled();
      expect(mockBrowser.close).toHaveBeenCalled();
    });
  });
});
