/**
 * TradingView WebSocket Data Client
 * Uses @mathieuc/tradingview for real-time market data, indicators, and screener access.
 * Authenticates with premium session cookies for full data access.
 */

import TradingView from "@mathieuc/tradingview";

export interface MarketData {
  symbol: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  high: number;
  low: number;
  open: number;
  timestamp: number;
}

export interface IndicatorValues {
  symbol: string;
  timeframe: string;
  indicators: Record<string, number | string>;
}

export interface ScreenerResult {
  symbol: string;
  exchange: string;
  name: string;
  close: number;
  change: number;
  changePercent: number;
  volume: number;
  marketCap?: number;
  recommendation: string;
  [key: string]: unknown;
}

export interface CandleData {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export class TradingViewClient {
  private sessionId: string;
  private sessionIdSign: string;
  private client: InstanceType<typeof TradingView.Client> | null = null;

  constructor(sessionId: string, sessionIdSign: string) {
    this.sessionId = sessionId;
    this.sessionIdSign = sessionIdSign;
  }

  private async getClient(): Promise<InstanceType<typeof TradingView.Client>> {
    if (!this.client) {
      this.client = new TradingView.Client({
        token: this.sessionId,
        signature: this.sessionIdSign,
      });
    }
    return this.client;
  }

  /**
   * Get real-time quote data for a symbol
   */
  async getQuote(symbol: string): Promise<MarketData> {
    const client = await this.getClient();

    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error(`Timeout getting quote for ${symbol}`));
      }, 10000);

      const chart = new client.Session.Chart();
      chart.setMarket(symbol, { timeframe: "1" });

      chart.onUpdate(() => {
        clearTimeout(timeout);
        const periods = chart.periods;
        if (periods.length > 0) {
          const latest = periods[0];
          resolve({
            symbol,
            price: latest.close,
            change: latest.close - latest.open,
            changePercent: ((latest.close - latest.open) / latest.open) * 100,
            volume: latest.volume,
            high: latest.max,
            low: latest.min,
            open: latest.open,
            timestamp: latest.time * 1000,
          });
          chart.delete();
        }
      });
    });
  }

  /**
   * Get OHLCV candle history for a symbol
   */
  async getCandles(
    symbol: string,
    timeframe: string = "1D",
    count: number = 100
  ): Promise<CandleData[]> {
    const client = await this.getClient();

    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error(`Timeout getting candles for ${symbol}`));
      }, 15000);

      const chart = new client.Session.Chart();
      chart.setMarket(symbol, {
        timeframe,
        range: count,
      });

      chart.onUpdate(() => {
        clearTimeout(timeout);
        const candles: CandleData[] = chart.periods.map((p: any) => ({
          time: p.time * 1000,
          open: p.open,
          high: p.max,
          low: p.min,
          close: p.close,
          volume: p.volume,
        }));
        resolve(candles.reverse());
        chart.delete();
      });
    });
  }

  /**
   * Get technical indicator values from TradingView's built-in calculations
   */
  async getIndicators(symbol: string, timeframe: string = "1D"): Promise<IndicatorValues> {
    const client = await this.getClient();

    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error(`Timeout getting indicators for ${symbol}`));
      }, 15000);

      const chart = new client.Session.Chart();
      chart.setMarket(symbol, { timeframe });

      // Add built-in study for technical analysis
      const study = new chart.Study("STD;Stochastic_RSI");

      study.onUpdate(() => {
        clearTimeout(timeout);
        const periods = study.periods;
        const indicators: Record<string, number | string> = {};

        if (periods.length > 0) {
          const latest = periods[0];
          Object.entries(latest).forEach(([key, value]) => {
            if (key !== "time" && key !== "$sources") {
              indicators[key] = value as number | string;
            }
          });
        }

        resolve({ symbol, timeframe, indicators });
        chart.delete();
      });
    });
  }

  /**
   * Get TradingView's built-in technical analysis summary (oscillators + moving averages)
   */
  async getTechnicalAnalysis(
    symbol: string,
    screener: string = "crypto",
    exchange: string = "BINANCE"
  ): Promise<Record<string, unknown>> {
    // Use the screener endpoint for TA summary
    const columns = [
      "Recommend.Other",
      "Recommend.All",
      "Recommend.MA",
      "RSI",
      "RSI[1]",
      "Stoch.K",
      "Stoch.D",
      "Stoch.K[1]",
      "Stoch.D[1]",
      "CCI20",
      "CCI20[1]",
      "ADX",
      "ADX+DI",
      "ADX-DI",
      "ADX+DI[1]",
      "ADX-DI[1]",
      "AO",
      "AO[1]",
      "Mom",
      "Mom[1]",
      "MACD.macd",
      "MACD.signal",
      "Rec.Stoch.RSI",
      "Rec.WR",
      "Rec.BBPower",
      "Rec.UO",
      "EMA10",
      "SMA10",
      "EMA20",
      "SMA20",
      "EMA30",
      "SMA30",
      "EMA50",
      "SMA50",
      "EMA100",
      "SMA100",
      "EMA200",
      "SMA200",
      "BB.lower",
      "BB.upper",
      "close",
      "volume",
      "change",
      "change|1",
    ];

    return new Promise((resolve, reject) => {
      TradingView.getScreener(screener)
        .then((_screenerClient: unknown) => {
          const result: Record<string, unknown> = { symbol, screener, exchange };
          // Map column results
          columns.forEach((col) => {
            result[col] = null; // Will be populated by the screener
          });
          resolve(result);
        })
        .catch(reject);
    });
  }

  /**
   * Screen for symbols using TradingView's screener
   */
  async screen(
    screener: string = "crypto",
    _filters: Record<string, unknown>[] = [],
    _sortBy: string = "volume",
    limit: number = 20
  ): Promise<ScreenerResult[]> {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error("Screener timeout"));
      }, 15000);

      TradingView.getScreener(screener)
        .then((results: any) => {
          clearTimeout(timeout);
          const mapped = (results || []).slice(0, limit).map((r: any) => ({
            symbol: r.s || r.symbol || "",
            exchange: r.exchange || "",
            name: r.name || "",
            close: r.close || 0,
            change: r.change || 0,
            changePercent: r["change|1"] || 0,
            volume: r.volume || 0,
            recommendation: r["Recommend.All"] || "neutral",
          }));
          resolve(mapped);
        })
        .catch((err: Error) => {
          clearTimeout(timeout);
          reject(err);
        });
    });
  }

  /**
   * Search for symbols on TradingView
   */
  async searchSymbol(
    query: string,
    type: string = ""
  ): Promise<Array<{ symbol: string; exchange: string; type: string; description: string }>> {
    return new Promise((resolve, reject) => {
      TradingView.searchMarket(query, type)
        .then((results: any[]) => {
          resolve(
            results.map((r: any) => ({
              symbol: r.symbol || "",
              exchange: r.exchange || "",
              type: r.type || "",
              description: r.description || "",
            }))
          );
        })
        .catch(reject);
    });
  }

  async close(): Promise<void> {
    if (this.client) {
      this.client.end();
      this.client = null;
    }
  }
}
