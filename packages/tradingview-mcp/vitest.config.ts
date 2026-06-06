import { defineConfig } from "vitest/config";

/**
 * Vitest config for tradingview-mcp.
 *
 * Goals:
 *  - Pure unit tests only (no DOM, no live browser, no CDP)
 *  - tsconfig-aware via Vitest's built-in TS support (no extra build step)
 *  - Tests live under src __tests__ dirs and top-level tests dir
 */
export default defineConfig({
  test: {
    environment: "node",
    include: ["src/**/__tests__/**/*.test.ts", "tests/**/*.test.ts"],
    globals: false,
    reporters: ["default"],
    passWithNoTests: false,
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html"],
      exclude: ["node_modules/", "dist/", "tests/", "src/**/__tests__/"],
    },
  },
});
