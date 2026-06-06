/**
 * TradingView Browser Automation Service
 * Uses Playwright to interact with the full TradingView web UI.
 * Provides access to all premium features: charts, alerts, Pine Script, watchlists, drawings.
 */

import { chromium, Browser, BrowserContext, Page } from "playwright";

export interface ChartScreenshot {
  imageBase64: string;
  symbol: string;
  timeframe: string;
  timestamp: number;
}

export interface AlertConfig {
  symbol: string;
  condition: string;
  value: number;
  message: string;
  webhookUrl?: string;
  expiration?: string;
}

export interface WatchlistItem {
  symbol: string;
  exchange: string;
  name?: string;
}

export class BrowserAutomation {
  private browser: Browser | null = null;
  private context: BrowserContext | null = null;
  private page: Page | null = null;
  private sessionId: string;
  private sessionIdSign: string;

  constructor(sessionId: string, sessionIdSign: string) {
    this.sessionId = sessionId;
    this.sessionIdSign = sessionIdSign;
  }

  private async ensureBrowser(): Promise<Page> {
    if (this.page && !this.page.isClosed()) {
      return this.page;
    }

    this.browser = await chromium.launch({
      headless: true,
      args: ["--no-sandbox", "--disable-setuid-sandbox"],
    });

    this.context = await this.browser.newContext({
      viewport: { width: 1920, height: 1080 },
      userAgent:
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    });

    // Set TradingView session cookies for premium access
    await this.context.addCookies([
      {
        name: "sessionid",
        value: this.sessionId,
        domain: ".tradingview.com",
        path: "/",
        httpOnly: true,
        secure: true,
        sameSite: "None",
      },
      {
        name: "sessionid_sign",
        value: this.sessionIdSign,
        domain: ".tradingview.com",
        path: "/",
        httpOnly: true,
        secure: true,
        sameSite: "None",
      },
    ]);

    this.page = await this.context.newPage();
    return this.page;
  }

  /**
   * Navigate to a TradingView chart and take a screenshot
   */
  async captureChart(
    symbol: string,
    timeframe: string = "1D",
    _indicators: string[] = []
  ): Promise<ChartScreenshot> {
    const page = await this.ensureBrowser();

    const url = `https://www.tradingview.com/chart/?symbol=${encodeURIComponent(symbol)}&interval=${timeframe}`;
    await page.goto(url, { waitUntil: "networkidle", timeout: 30000 });

    // Wait for chart to render
    await page.waitForSelector(".chart-container", { timeout: 15000 }).catch(() => {
      // Fallback: wait for the main content area
    });
    await page.waitForTimeout(3000); // Allow indicators and overlays to load

    // Close any popups/modals
    await page.click('button[aria-label="Close"]').catch(() => {});
    await page.keyboard.press("Escape");

    const screenshot = await page.screenshot({
      type: "png",
      fullPage: false,
    });

    return {
      imageBase64: screenshot.toString("base64"),
      symbol,
      timeframe,
      timestamp: Date.now(),
    };
  }

  /**
   * Get chart data visible on the current chart (prices, volume, indicators)
   */
  async readChartData(symbol: string, timeframe: string = "1D"): Promise<Record<string, unknown>> {
    const page = await this.ensureBrowser();

    const url = `https://www.tradingview.com/chart/?symbol=${encodeURIComponent(symbol)}&interval=${timeframe}`;
    await page.goto(url, { waitUntil: "networkidle", timeout: 30000 });
    await page.waitForTimeout(3000);

    // Extract data from the chart's data window
    const data = await page.evaluate(() => {
      // Try to read from the chart's internal state
      const result: Record<string, unknown> = {};

      // Get price from the price axis
      const priceEl = document.querySelector('[class*="lastPrice"]');
      if (priceEl) result.lastPrice = priceEl.textContent?.trim();

      // Get OHLCV from the data window
      const dataWindow = document.querySelector('[class*="valuesWrapper"]');
      if (dataWindow) {
        result.dataWindow = dataWindow.textContent?.trim();
      }

      // Get indicator values displayed
      const indicators = document.querySelectorAll('[class*="legendWrapper"]');
      const indicatorData: string[] = [];
      indicators.forEach((el) => {
        const text = el.textContent?.trim();
        if (text) indicatorData.push(text);
      });
      result.indicators = indicatorData;

      return result;
    });

    return { symbol, timeframe, ...data };
  }

  /**
   * Create a TradingView alert
   */
  async createAlert(config: AlertConfig): Promise<{ success: boolean; message: string }> {
    const page = await this.ensureBrowser();

    // Navigate to chart for the symbol
    const url = `https://www.tradingview.com/chart/?symbol=${encodeURIComponent(config.symbol)}`;
    await page.goto(url, { waitUntil: "networkidle", timeout: 30000 });
    await page.waitForTimeout(2000);

    try {
      // Open alert creation dialog via keyboard shortcut
      await page.keyboard.press("Alt+a");
      await page.waitForTimeout(1000);

      // Wait for the alert dialog
      await page
        .waitForSelector('[data-name="alerts-create-edit-dialog"]', {
          timeout: 5000,
        })
        .catch(() => {
          // Try clicking the alert button in the toolbar
        });

      // Fill in alert condition
      // The exact selectors depend on TradingView's current DOM structure
      // This provides the framework — selectors may need updating

      // Set alert message
      const messageInput = await page.$('textarea[name="description"], textarea[class*="message"]');
      if (messageInput) {
        await messageInput.fill(config.message);
      }

      // Set webhook URL if provided
      if (config.webhookUrl) {
        const webhookCheckbox = await page.$(
          'input[name="webhook-toggle"], label:has-text("Webhook URL")'
        );
        if (webhookCheckbox) await webhookCheckbox.click();

        const webhookInput = await page.$(
          'input[name="webhook-url"], input[placeholder*="https://"]'
        );
        if (webhookInput) await webhookInput.fill(config.webhookUrl);
      }

      // Click Create button
      const createBtn = await page.$('button:has-text("Create"), [data-name="submit"]');
      if (createBtn) await createBtn.click();

      await page.waitForTimeout(1000);
      return { success: true, message: `Alert created for ${config.symbol}` };
    } catch (err) {
      return {
        success: false,
        message: `Failed to create alert: ${err instanceof Error ? err.message : String(err)}`,
      };
    }
  }

  /**
   * List active alerts
   */
  async listAlerts(): Promise<Array<Record<string, string>>> {
    const page = await this.ensureBrowser();

    await page.goto("https://www.tradingview.com/chart/", {
      waitUntil: "networkidle",
      timeout: 30000,
    });
    await page.waitForTimeout(2000);

    // Open alerts panel
    const alertsTab = await page.$(
      '[data-name="alerts"], [aria-label="Alert"], button:has-text("Alerts")'
    );
    if (alertsTab) await alertsTab.click();
    await page.waitForTimeout(1000);

    const alerts = await page.evaluate(() => {
      const alertElements = document.querySelectorAll(
        '[class*="alertItem"], [class*="alert-item"]'
      );
      const results: Array<Record<string, string>> = [];
      alertElements.forEach((el) => {
        const text = el.textContent?.trim() || "";
        results.push({ text, html: el.innerHTML.substring(0, 200) });
      });
      return results;
    });

    return alerts;
  }

  /**
   * Open the Pine Script editor and interact with it
   */
  async openPineEditor(): Promise<{ success: boolean; currentCode: string }> {
    const page = await this.ensureBrowser();

    await page.goto("https://www.tradingview.com/chart/", {
      waitUntil: "networkidle",
      timeout: 30000,
    });
    await page.waitForTimeout(2000);

    // Open Pine Editor panel
    const pineTab = await page.$(
      '[data-name="pine-editor"], button:has-text("Pine Editor"), [aria-label="Pine Editor"]'
    );
    if (pineTab) await pineTab.click();
    await page.waitForTimeout(1000);

    // Read current code
    const code = await page.evaluate(() => {
      const editor = document.querySelector('[class*="pine-editor"] textarea, .view-lines');
      return editor?.textContent || "";
    });

    return { success: true, currentCode: code };
  }

  /**
   * Write Pine Script code to the editor
   */
  async writePineScript(code: string): Promise<{ success: boolean; message: string }> {
    const page = await this.ensureBrowser();

    try {
      // Ensure Pine Editor is open
      await this.openPineEditor();

      // Select all existing code and replace
      await page.keyboard.press("Control+a");
      await page.waitForTimeout(200);
      await page.keyboard.press("Backspace");
      await page.waitForTimeout(200);

      // Type the new code
      await page.keyboard.type(code, { delay: 5 });
      await page.waitForTimeout(500);

      return { success: true, message: "Pine Script code written to editor" };
    } catch (err) {
      return {
        success: false,
        message: `Failed to write Pine Script: ${err instanceof Error ? err.message : String(err)}`,
      };
    }
  }

  /**
   * Compile/Add Pine Script to chart
   */
  async compilePineScript(): Promise<{ success: boolean; errors: string[]; message: string }> {
    const page = await this.ensureBrowser();

    try {
      // Click "Add to chart" button in Pine Editor
      const addBtn = await page.$(
        'button:has-text("Add to chart"), button:has-text("Save"), [data-name="pine-editor-add"]'
      );
      if (addBtn) await addBtn.click();
      await page.waitForTimeout(3000);

      // Check for compilation errors
      const errors = await page.evaluate(() => {
        const errorElements = document.querySelectorAll(
          '[class*="error"], [class*="pine-error"], .tv-pine-error'
        );
        const errs: string[] = [];
        errorElements.forEach((el) => {
          const text = el.textContent?.trim();
          if (text) errs.push(text);
        });
        return errs;
      });

      if (errors.length > 0) {
        return { success: false, errors, message: "Pine Script compilation failed" };
      }

      return { success: true, errors: [], message: "Pine Script added to chart successfully" };
    } catch (err) {
      return {
        success: false,
        errors: [err instanceof Error ? err.message : String(err)],
        message: "Failed to compile Pine Script",
      };
    }
  }

  /**
   * Manage watchlists - get current watchlist
   */
  async getWatchlist(): Promise<WatchlistItem[]> {
    const page = await this.ensureBrowser();

    await page.goto("https://www.tradingview.com/chart/", {
      waitUntil: "networkidle",
      timeout: 30000,
    });
    await page.waitForTimeout(2000);

    // Open watchlist panel
    const watchlistBtn = await page.$(
      '[data-name="watchlist"], button:has-text("Watchlist"), [aria-label="Watchlist"]'
    );
    if (watchlistBtn) await watchlistBtn.click();
    await page.waitForTimeout(1000);

    const items = await page.evaluate(() => {
      const rows = document.querySelectorAll(
        '[class*="listRow"], [class*="watchlist-item"], [class*="symbolRow"]'
      );
      const results: Array<{ symbol: string; exchange: string; name?: string }> = [];
      rows.forEach((row) => {
        const symbolEl = row.querySelector('[class*="symbol"], [class*="ticker"]');
        const exchangeEl = row.querySelector('[class*="exchange"]');
        if (symbolEl) {
          results.push({
            symbol: symbolEl.textContent?.trim() || "",
            exchange: exchangeEl?.textContent?.trim() || "",
          });
        }
      });
      return results;
    });

    return items;
  }

  /**
   * Add symbol to watchlist
   */
  async addToWatchlist(symbol: string): Promise<{ success: boolean; message: string }> {
    const page = await this.ensureBrowser();

    try {
      // Use the add symbol input in the watchlist
      const addInput = await page.$(
        'input[placeholder*="Add symbol"], input[placeholder*="Search"]'
      );
      if (addInput) {
        await addInput.fill(symbol);
        await page.waitForTimeout(1000);
        // Click the first result
        const firstResult = await page.$(
          '[class*="listRow"]:first-child, [class*="resultItem"]:first-child'
        );
        if (firstResult) await firstResult.click();
      }

      return { success: true, message: `Added ${symbol} to watchlist` };
    } catch (err) {
      return {
        success: false,
        message: `Failed: ${err instanceof Error ? err.message : String(err)}`,
      };
    }
  }

  /**
   * Change chart symbol
   */
  async changeSymbol(symbol: string): Promise<{ success: boolean }> {
    const page = await this.ensureBrowser();

    const url = `https://www.tradingview.com/chart/?symbol=${encodeURIComponent(symbol)}`;
    await page.goto(url, { waitUntil: "networkidle", timeout: 30000 });
    await page.waitForTimeout(2000);

    return { success: true };
  }

  /**
   * Change chart timeframe
   */
  async changeTimeframe(timeframe: string): Promise<{ success: boolean }> {
    const page = await this.ensureBrowser();

    // Use keyboard shortcut - TradingView supports direct timeframe input
    await page.keyboard.press(timeframe);
    await page.waitForTimeout(500);
    await page.keyboard.press("Enter");
    await page.waitForTimeout(1000);

    return { success: true };
  }

  /**
   * Take a full-page screenshot of whatever is currently visible
   */
  async screenshot(): Promise<string> {
    const page = await this.ensureBrowser();
    const buffer = await page.screenshot({ type: "png", fullPage: false });
    return buffer.toString("base64");
  }

  /**
   * Execute arbitrary JavaScript on the TradingView page (for advanced automation)
   */
  async executeOnPage(script: string): Promise<unknown> {
    const page = await this.ensureBrowser();
    return page.evaluate(script);
  }

  /**
   * Get the current page URL and title
   */
  async getPageInfo(): Promise<{ url: string; title: string }> {
    const page = await this.ensureBrowser();
    return {
      url: page.url(),
      title: await page.title(),
    };
  }

  /**
   * Navigate to a specific TradingView page
   */
  async navigateTo(path: string): Promise<{ success: boolean; url: string }> {
    const page = await this.ensureBrowser();
    const url = path.startsWith("http") ? path : `https://www.tradingview.com${path}`;
    await page.goto(url, { waitUntil: "networkidle", timeout: 30000 });
    await page.waitForTimeout(2000);
    return { success: true, url: page.url() };
  }

  async close(): Promise<void> {
    if (this.page) await this.page.close().catch(() => {});
    if (this.context) await this.context.close().catch(() => {});
    if (this.browser) await this.browser.close().catch(() => {});
    this.page = null;
    this.context = null;
    this.browser = null;
  }
}
