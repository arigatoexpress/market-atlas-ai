import { describe, expect, it } from "vitest";

import { PineScriptService } from "../services/pine-script.js";

/**
 * Pure unit tests for PineScriptService.validate().
 *
 * Why this is safe to test in isolation:
 *  - validate() is a pure function over a string input
 *  - No browser, no CDP, no network, no filesystem
 *  - Deterministic — given the same source code, returns the same result
 */
describe("PineScriptService.validate", () => {
  const service = new PineScriptService();

  it("flags missing version declaration as an error", () => {
    const result = service.validate(`indicator("Test", overlay=true)`);

    expect(result.valid).toBe(false);
    expect(result.errors).toEqual(
      expect.arrayContaining([expect.stringContaining("Missing version declaration")])
    );
  });

  it("flags missing indicator/strategy/library declaration as an error", () => {
    const result = service.validate(`//@version=5\nplot(close)`);

    expect(result.valid).toBe(false);
    expect(result.errors).toEqual(
      expect.arrayContaining([
        expect.stringContaining("Missing indicator(), strategy(), or library() declaration"),
      ])
    );
  });

  it("accepts a minimal valid v5 indicator with no errors or warnings", () => {
    const code = ["//@version=5", 'indicator("Minimal", overlay=true)', "plot(close)"].join("\n");

    const result = service.validate(code);

    expect(result.valid).toBe(true);
    expect(result.version).toBe("5");
    expect(result.errors).toEqual([]);
    expect(result.warnings).toEqual([]);
  });

  it("warns when v4-style sma()/ema() helpers are used in v5 source", () => {
    const code = [
      "//@version=5",
      'indicator("LegacyHelpers", overlay=true)',
      "fast = sma(close, 10)",
      "slow = ema(close, 20)",
      "plot(fast)",
      "plot(slow)",
    ].join("\n");

    const result = service.validate(code);

    // Both should produce warnings, not errors — script still parses.
    expect(result.errors).toEqual([]);
    expect(result.warnings.some((w) => w.includes("ta.sma()"))).toBe(true);
    expect(result.warnings.some((w) => w.includes("ta.ema()"))).toBe(true);
  });

  it("reports unmatched parentheses as an error", () => {
    const code = [
      "//@version=5",
      'indicator("Broken", overlay=true)',
      "x = ta.sma(close, 14",
      "plot(x)",
    ].join("\n");

    const result = service.validate(code);

    expect(result.valid).toBe(false);
    expect(result.errors).toEqual(
      expect.arrayContaining([expect.stringContaining("Unmatched parentheses")])
    );
  });
});
