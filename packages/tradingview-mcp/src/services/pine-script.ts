/**
 * Pine Script Intelligence Service
 * Validates, generates, and optimizes Pine Script v5/v6 code.
 * Works locally without needing browser automation.
 */

export interface PineScriptValidation {
  valid: boolean;
  errors: string[];
  warnings: string[];
  version: string;
}

export interface PineScriptTemplate {
  name: string;
  description: string;
  code: string;
  category: "indicator" | "strategy" | "library";
}

const _PINE_V5_KEYWORDS = [
  "indicator",
  "strategy",
  "library",
  "input",
  "plot",
  "plotshape",
  "ta.sma",
  "ta.ema",
  "ta.rsi",
  "ta.macd",
  "ta.stoch",
  "ta.bb",
  "ta.atr",
  "ta.cci",
  "ta.mfi",
  "ta.obv",
  "ta.vwap",
  "ta.crossover",
  "ta.crossunder",
  "ta.highest",
  "ta.lowest",
  "ta.change",
  "ta.valuewhen",
  "ta.barssince",
  "strategy.entry",
  "strategy.exit",
  "strategy.close",
  "strategy.order",
  "strategy.cancel",
  "request.security",
  "request.financial",
  "math.abs",
  "math.max",
  "math.min",
  "math.round",
  "str.tostring",
  "str.format",
  "array.new_float",
  "array.push",
  "array.get",
  "var",
  "varip",
  "export",
  "import",
  "switch",
  "type",
];

export class PineScriptService {
  /**
   * Validate Pine Script syntax (basic local validation)
   */
  validate(code: string): PineScriptValidation {
    const errors: string[] = [];
    const warnings: string[] = [];
    let version = "5";

    const lines = code.split("\n");

    // Check version declaration
    const versionLine = lines.find((l) => l.trim().startsWith("//@version="));
    if (!versionLine) {
      errors.push("Missing version declaration. Add //@version=5 or //@version=6 at the top.");
    } else {
      const match = versionLine.match(/\/\/@version=(\d+)/);
      if (match) version = match[1];
      if (!["4", "5", "6"].includes(version)) {
        errors.push(`Unsupported version: ${version}. Use 4, 5, or 6.`);
      }
    }

    // Check for required declaration (indicator/strategy/library)
    const hasDeclaration = lines.some(
      (l) =>
        l.trim().startsWith("indicator(") ||
        l.trim().startsWith("strategy(") ||
        l.trim().startsWith("library(")
    );
    if (!hasDeclaration) {
      errors.push("Missing indicator(), strategy(), or library() declaration.");
    }

    // Check for common v4 syntax used in v5/v6
    if (parseInt(version) >= 5) {
      lines.forEach((line, i) => {
        const trimmed = line.trim();
        if (trimmed.startsWith("//")) return;

        // Check for deprecated v4 functions
        if (/\bsma\(/.test(trimmed) && !/ta\.sma\(/.test(trimmed)) {
          warnings.push(`Line ${i + 1}: Use ta.sma() instead of sma() in v${version}`);
        }
        if (/\bema\(/.test(trimmed) && !/ta\.ema\(/.test(trimmed)) {
          warnings.push(`Line ${i + 1}: Use ta.ema() instead of ema() in v${version}`);
        }
        if (/\brsi\(/.test(trimmed) && !/ta\.rsi\(/.test(trimmed)) {
          warnings.push(`Line ${i + 1}: Use ta.rsi() instead of rsi() in v${version}`);
        }
        if (/\bmacd\(/.test(trimmed) && !/ta\.macd\(/.test(trimmed)) {
          warnings.push(`Line ${i + 1}: Use ta.macd() instead of macd() in v${version}`);
        }
        if (/\bcrosover\(/.test(trimmed)) {
          errors.push(`Line ${i + 1}: Typo 'crosover' — should be 'crossover'`);
        }
        if (/\bcross\(/.test(trimmed) && parseInt(version) >= 5) {
          warnings.push(`Line ${i + 1}: cross() is deprecated in v${version}, use ta.cross()`);
        }

        // Check for security() vs request.security()
        if (/\bsecurity\(/.test(trimmed) && !/request\.security\(/.test(trimmed)) {
          warnings.push(
            `Line ${i + 1}: Use request.security() instead of security() in v${version}`
          );
        }
      });
    }

    // Check for unclosed brackets
    let braces = 0,
      parens = 0,
      brackets = 0;
    for (const line of lines) {
      if (line.trim().startsWith("//")) continue;
      for (const char of line) {
        if (char === "{") braces++;
        if (char === "}") braces--;
        if (char === "(") parens++;
        if (char === ")") parens--;
        if (char === "[") brackets++;
        if (char === "]") brackets--;
      }
    }
    if (braces !== 0)
      errors.push(`Unmatched curly braces: ${braces > 0 ? "missing }" : "extra }"}`);
    if (parens !== 0) errors.push(`Unmatched parentheses: ${parens > 0 ? "missing )" : "extra )"}`);
    if (brackets !== 0)
      errors.push(`Unmatched brackets: ${brackets > 0 ? "missing ]" : "extra ]"}`);

    return {
      valid: errors.length === 0,
      errors,
      warnings,
      version,
    };
  }

  /**
   * Generate a Pine Script template
   */
  generateTemplate(
    type: "indicator" | "strategy" | "library",
    name: string,
    options: {
      version?: string;
      overlay?: boolean;
      indicators?: string[];
    } = {}
  ): string {
    const version = options.version || "5";
    const overlay = options.overlay ?? true;

    if (type === "strategy") {
      return `//@version=${version}
strategy("${name}", overlay=${overlay}, default_qty_type=strategy.percent_of_equity, default_qty_value=100, commission_type=strategy.commission.percent, commission_value=0.1)

// Inputs
fastLength = input.int(12, "Fast MA Length", minval=1)
slowLength = input.int(26, "Slow MA Length", minval=1)
signalLength = input.int(9, "Signal Length", minval=1)

// Calculations
fastMA = ta.ema(close, fastLength)
slowMA = ta.ema(close, slowLength)
macd = fastMA - slowMA
signal = ta.ema(macd, signalLength)
histogram = macd - signal

// Entry conditions
longCondition = ta.crossover(macd, signal) and macd < 0
shortCondition = ta.crossunder(macd, signal) and macd > 0

// Entries
if longCondition
    strategy.entry("Long", strategy.long)

if shortCondition
    strategy.entry("Short", strategy.short)

// Plot
plot(macd, "MACD", color=color.blue)
plot(signal, "Signal", color=color.orange)
plot(histogram, "Histogram", style=plot.style_histogram, color=histogram >= 0 ? color.green : color.red)
`;
    }

    if (type === "library") {
      return `//@version=${version}
// @description ${name} - Custom library for Sapphire trading system
library("${name}", overlay=${overlay})

// @function Calculate weighted moving average with custom weights
// @param src The source series
// @param length The lookback period
// @returns The weighted moving average value
export weightedMA(float src, int length) =>
    float sum = 0.0
    float weightSum = 0.0
    for i = 0 to length - 1
        float weight = length - i
        sum += src[i] * weight
        weightSum += weight
    sum / weightSum
`;
    }

    // Default: indicator
    return `//@version=${version}
indicator("${name}", overlay=${overlay})

// Inputs
length = input.int(14, "Length", minval=1)
source = input.source(close, "Source")

// Calculations
smaValue = ta.sma(source, length)
emaValue = ta.ema(source, length)
rsiValue = ta.rsi(source, length)

// Plots
plot(smaValue, "SMA", color=color.blue, linewidth=2)
plot(emaValue, "EMA", color=color.orange, linewidth=2)

// RSI in separate pane
// hline(70, "Overbought", color=color.red)
// hline(30, "Oversold", color=color.green)
// plot(rsiValue, "RSI", color=color.purple)
`;
  }

  /**
   * Generate a Sapphire-compatible Pine Script strategy with webhook alerts
   */
  generateSapphireStrategy(
    name: string,
    _config: {
      symbols?: string[];
      timeframes?: string[];
      indicatorLogic?: string;
      webhookUrl?: string;
    } = {}
  ): string {
    return `//@version=5
strategy("Sapphire: ${name}", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=100, commission_type=strategy.commission.percent, commission_value=0.1)

// ══════════════════════════════════════════
// Sapphire Trading System — ${name}
// Generates webhook alerts compatible with Sapphire signal format
// ══════════════════════════════════════════

// Inputs
fastLen = input.int(12, "Fast EMA", minval=1, group="Moving Averages")
slowLen = input.int(26, "Slow EMA", minval=1, group="Moving Averages")
rsiLen = input.int(14, "RSI Length", minval=1, group="Oscillators")
rsiOB = input.int(70, "RSI Overbought", minval=50, maxval=100, group="Oscillators")
rsiOS = input.int(30, "RSI Oversold", minval=0, maxval=50, group="Oscillators")
atrLen = input.int(14, "ATR Length", minval=1, group="Risk")
atrMult = input.float(2.0, "ATR Stop Multiplier", minval=0.5, step=0.1, group="Risk")

// Calculations
fastEMA = ta.ema(close, fastLen)
slowEMA = ta.ema(close, slowLen)
rsi = ta.rsi(close, rsiLen)
atr = ta.atr(atrLen)
[macdLine, signalLine, histLine] = ta.macd(close, 12, 26, 9)

// Trend detection
upTrend = fastEMA > slowEMA
downTrend = fastEMA < slowEMA
trendStrength = math.abs(fastEMA - slowEMA) / atr

// Entry signals
longSignal = ta.crossover(fastEMA, slowEMA) and rsi < rsiOB and rsi > rsiOS
shortSignal = ta.crossunder(fastEMA, slowEMA) and rsi > rsiOS and rsi < rsiOB

// Confidence calculation (0.0 - 1.0)
longConfidence = 0.0
longConfidence := longSignal ? math.min(1.0, 0.5 + (trendStrength * 0.1) + ((rsiOB - rsi) / 100.0) + (histLine > 0 ? 0.15 : 0.0)) : 0.0

shortConfidence = 0.0
shortConfidence := shortSignal ? math.min(1.0, 0.5 + (trendStrength * 0.1) + ((rsi - rsiOS) / 100.0) + (histLine < 0 ? 0.15 : 0.0)) : 0.0

// Strategy entries with alerts
if longSignal
    strategy.entry("Long", strategy.long)
    alert('{"symbol":"' + syminfo.ticker + '","action":"BUY","indicator":"${name}","confidence":' + str.tostring(longConfidence, "#.##") + ',"timeframe":"' + timeframe.period + '","price":' + str.tostring(close) + ',"timestamp":"' + str.format_time(timenow, "yyyy-MM-dd\\'T\\'HH:mm:ss\\'Z\\'", "UTC") + '"}', alert.freq_once_per_bar_close)

if shortSignal
    strategy.entry("Short", strategy.short)
    alert('{"symbol":"' + syminfo.ticker + '","action":"SELL","indicator":"${name}","confidence":' + str.tostring(shortConfidence, "#.##") + ',"timeframe":"' + timeframe.period + '","price":' + str.tostring(close) + ',"timestamp":"' + str.format_time(timenow, "yyyy-MM-dd\\'T\\'HH:mm:ss\\'Z\\'", "UTC") + '"}', alert.freq_once_per_bar_close)

// Exit on opposite signal
if strategy.position_size > 0 and shortSignal
    strategy.close("Long")
    alert('{"symbol":"' + syminfo.ticker + '","action":"CLOSE","indicator":"${name}","confidence":' + str.tostring(shortConfidence, "#.##") + ',"timeframe":"' + timeframe.period + '","price":' + str.tostring(close) + ',"timestamp":"' + str.format_time(timenow, "yyyy-MM-dd\\'T\\'HH:mm:ss\\'Z\\'", "UTC") + '"}', alert.freq_once_per_bar_close)

if strategy.position_size < 0 and longSignal
    strategy.close("Short")
    alert('{"symbol":"' + syminfo.ticker + '","action":"CLOSE","indicator":"${name}","confidence":' + str.tostring(longConfidence, "#.##") + ',"timeframe":"' + timeframe.period + '","price":' + str.tostring(close) + ',"timestamp":"' + str.format_time(timenow, "yyyy-MM-dd\\'T\\'HH:mm:ss\\'Z\\'", "UTC") + '"}', alert.freq_once_per_bar_close)

// ATR-based stop loss
stopLoss = atr * atrMult
if strategy.position_size > 0
    strategy.exit("Long SL", "Long", stop=strategy.position_avg_price - stopLoss)
if strategy.position_size < 0
    strategy.exit("Short SL", "Short", stop=strategy.position_avg_price + stopLoss)

// Plots
plot(fastEMA, "Fast EMA", color=color.new(color.blue, 0), linewidth=2)
plot(slowEMA, "Slow EMA", color=color.new(color.orange, 0), linewidth=2)
plotshape(longSignal, "Long Signal", shape.triangleup, location.belowbar, color.green, size=size.small)
plotshape(shortSignal, "Short Signal", shape.triangledown, location.abovebar, color.red, size=size.small)

// Background trend
bgcolor(upTrend ? color.new(color.green, 95) : downTrend ? color.new(color.red, 95) : na)

// Info table
var table infoTable = table.new(position.top_right, 2, 4, bgcolor=color.new(color.black, 80))
if barstate.islast
    table.cell(infoTable, 0, 0, "Sapphire", text_color=color.white, text_size=size.small)
    table.cell(infoTable, 1, 0, "${name}", text_color=color.yellow, text_size=size.small)
    table.cell(infoTable, 0, 1, "Trend", text_color=color.white, text_size=size.small)
    table.cell(infoTable, 1, 1, upTrend ? "BULLISH" : downTrend ? "BEARISH" : "NEUTRAL", text_color=upTrend ? color.green : downTrend ? color.red : color.gray, text_size=size.small)
    table.cell(infoTable, 0, 2, "RSI", text_color=color.white, text_size=size.small)
    table.cell(infoTable, 1, 2, str.tostring(rsi, "#.#"), text_color=rsi > rsiOB ? color.red : rsi < rsiOS ? color.green : color.white, text_size=size.small)
    table.cell(infoTable, 0, 3, "ATR", text_color=color.white, text_size=size.small)
    table.cell(infoTable, 1, 3, str.tostring(atr, "#.##"), text_color=color.white, text_size=size.small)
`;
  }

  /**
   * Get available Pine Script templates
   */
  getTemplates(): PineScriptTemplate[] {
    return [
      {
        name: "Basic Indicator",
        description: "SMA/EMA with RSI - good starting point for custom indicators",
        code: this.generateTemplate("indicator", "Custom Indicator"),
        category: "indicator",
      },
      {
        name: "MACD Strategy",
        description: "MACD crossover strategy with entry/exit signals",
        code: this.generateTemplate("strategy", "MACD Crossover Strategy"),
        category: "strategy",
      },
      {
        name: "Sapphire Signal Strategy",
        description: "Webhook-compatible strategy for Sapphire autonomous trading",
        code: this.generateSapphireStrategy("Signal Generator"),
        category: "strategy",
      },
      {
        name: "Custom Library",
        description: "Reusable library functions for Pine Script",
        code: this.generateTemplate("library", "SapphireLib"),
        category: "library",
      },
    ];
  }
}
