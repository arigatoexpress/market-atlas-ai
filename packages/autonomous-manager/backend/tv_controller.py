"""
TradingView Desktop Controller
Automates TradingView Desktop application using Playwright
"""

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass
from datetime import datetime

try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext
except ImportError:
    print("Playwright not installed. Install with: pip install playwright")
    print("Then run: playwright install chromium")
    raise

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TradingViewState:
    """Current state of TradingView Desktop"""
    symbol: str = ""
    timeframe: str = ""
    watchlist: str = ""
    active_indicators: List[str] = None
    is_chart_loaded: bool = False
    
    def __post_init__(self):
        if self.active_indicators is None:
            self.active_indicators = []


@dataclass
class Signal:
    """Trading signal structure"""
    symbol: str
    direction: str  # "LONG", "SHORT", "NEUTRAL"
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float
    timeframe: str
    strategy: str
    indicators: Dict[str, Any]
    timestamp: datetime
    source: str  # "indicator", "strategy", "ai_analysis"


class TradingViewController:
    """
    Controller for TradingView Desktop automation
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.state = TradingViewState()
        self._callbacks: List[Callable] = []
        self._is_connected = False
        
    async def initialize(self) -> bool:
        """Initialize Playwright and connect to TradingView Desktop"""
        try:
            logger.info("Initializing TradingView Desktop Controller...")
            
            playwright = await async_playwright().start()
            
            # Connect to existing Chrome/Edge with remote debugging
            # TradingView Desktop uses Electron which exposes CDP on port 9222 if launched with --remote-debugging-port
            try:
                self.browser = await playwright.chromium.connect_over_cdp(
                    "http://localhost:9222"
                )
                logger.info("Connected to TradingView Desktop via CDP")
            except Exception as e:
                logger.warning(f"Could not connect via CDP: {e}")
                logger.info("Launching new browser instance...")
                
                # Launch TradingView Desktop if not running
                self.browser = await playwright.chromium.launch(
                    headless=self.config.get('headless', False),
                    args=['--disable-blink-features=AutomationControlled']
                )
            
            # Create context with viewport
            self.context = await self.browser.new_context(
                viewport={
                    'width': self.config.get('viewport_width', 1920),
                    'height': self.config.get('viewport_height', 1080)
                }
            )
            
            # Get or create page
            pages = self.context.pages
            if pages:
                self.page = pages[0]
            else:
                self.page = await self.context.new_page()
            
            # Navigate to TradingView if not already there
            if 'tradingview.com' not in self.page.url:
                await self.page.goto('https://www.tradingview.com/chart/')
                await asyncio.sleep(3)
            
            # Inject helper script
            await self._inject_helper_script()
            
            self._is_connected = True
            logger.info("TradingView Controller initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            return False
    
    async def _inject_helper_script(self):
        """Inject JavaScript helper for chart interaction"""
        helper_script = """
        window.TVHelper = {
            getCurrentSymbol() {
                const title = document.querySelector('.chart-gui-wrapper .title-wrapper');
                return title ? title.textContent : '';
            },
            
            getTimeframe() {
                const tfBtn = document.querySelector('[data-name="time-interval-menu"]');
                return tfBtn ? tfBtn.textContent.trim() : '';
            },
            
            async setSymbol(symbol) {
                const searchBtn = document.querySelector('.search-HYXXFK3E');
                if (searchBtn) {
                    searchBtn.click();
                    await new Promise(r => setTimeout(r, 500));
                    const input = document.querySelector('input[data-role="search"]');
                    if (input) {
                        input.value = symbol;
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                        await new Promise(r => setTimeout(r, 500));
                        const firstResult = document.querySelector('.item-KF4gJkYV');
                        if (firstResult) firstResult.click();
                    }
                }
            },
            
            async setTimeframe(tf) {
                const tfBtn = document.querySelector('[data-name="time-interval-menu"]');
                if (tfBtn) {
                    tfBtn.click();
                    await new Promise(r => setTimeout(r, 300));
                    const items = document.querySelectorAll('[data-value]');
                    for (let item of items) {
                        if (item.textContent.includes(tf)) {
                            item.click();
                            break;
                        }
                    }
                }
            },
            
            getIndicators() {
                const indicators = [];
                const pills = document.querySelectorAll('[data-name="legend-source-title"]');
                pills.forEach(p => indicators.push(p.textContent));
                return indicators;
            },
            
            async addIndicator(name) {
                // Open indicator menu
                const indBtn = document.querySelector('[data-name="indicator-menus"]');
                if (indBtn) indBtn.click();
                await new Promise(r => setTimeout(r, 500));
                
                // Search for indicator
                const search = document.querySelector('input[placeholder*="Search"]');
                if (search) {
                    search.value = name;
                    search.dispatchEvent(new Event('input', { bubbles: true }));
                    await new Promise(r => setTimeout(r, 500));
                    const result = document.querySelector('.item-JLr4OzO6');
                    if (result) result.click();
                }
            },
            
            async removeIndicator(name) {
                const indicators = document.querySelectorAll('[data-name="legend-source-item"]');
                for (let ind of indicators) {
                    const title = ind.querySelector('[data-name="legend-source-title"]');
                    if (title && title.textContent.includes(name)) {
                        const closeBtn = ind.querySelector('[data-name="legend-remove-action"]');
                        if (closeBtn) closeBtn.click();
                        break;
                    }
                }
            },
            
            getPrice() {
                const price = document.querySelector('.chart-gui-wrapper .price-value');
                return price ? parseFloat(price.textContent.replace(/,/g, '')) : null;
            },
            
            async takeScreenshot() {
                const canvas = document.querySelector('canvas.chart-gui-canvas');
                if (canvas) {
                    return canvas.toDataURL('image/png');
                }
                return null;
            },
            
            async openPineEditor() {
                const btn = document.querySelector('[data-name="script-editor"]');
                if (btn) btn.click();
            },
            
            async addStrategyToChart(strategyCode) {
                await this.openPineEditor();
                await new Promise(r => setTimeout(r, 1000));
                
                // Find editor and set code
                const editor = document.querySelector('.monaco-editor');
                if (editor) {
                    // Clear and type new code
                    const textarea = editor.querySelector('textarea');
                    if (textarea) {
                        textarea.value = strategyCode;
                        textarea.dispatchEvent(new Event('input', { bubbles: true }));
                    }
                }
                
                // Add to chart
                const addBtn = document.querySelector('[data-name="add-script-to-chart"]');
                if (addBtn) addBtn.click();
            }
        };
        """
        await self.page.evaluate(helper_script)
    
    async def get_current_state(self) -> TradingViewState:
        """Get current chart state"""
        if not self.page:
            return TradingViewState()
        
        try:
            state = await self.page.evaluate("""
                () => ({
                    symbol: window.TVHelper?.getCurrentSymbol() || '',
                    timeframe: window.TVHelper?.getTimeframe() || '',
                    indicators: window.TVHelper?.getIndicators() || [],
                    price: window.TVHelper?.getPrice()
                })
            """)
            
            self.state = TradingViewState(
                symbol=state.get('symbol', ''),
                timeframe=state.get('timeframe', ''),
                active_indicators=state.get('indicators', []),
                is_chart_loaded=bool(state.get('price'))
            )
            return self.state
            
        except Exception as e:
            logger.error(f"Error getting state: {e}")
            return self.state
    
    async def set_symbol(self, symbol: str) -> bool:
        """Change chart symbol"""
        try:
            logger.info(f"Setting symbol to: {symbol}")
            await self.page.evaluate(f"window.TVHelper.setSymbol('{symbol}')")
            await asyncio.sleep(2)
            self.state.symbol = symbol
            return True
        except Exception as e:
            logger.error(f"Error setting symbol: {e}")
            return False
    
    async def set_timeframe(self, timeframe: str) -> bool:
        """Change chart timeframe"""
        try:
            logger.info(f"Setting timeframe to: {timeframe}")
            await self.page.evaluate(f"window.TVHelper.setTimeframe('{timeframe}')")
            await asyncio.sleep(1)
            self.state.timeframe = timeframe
            return True
        except Exception as e:
            logger.error(f"Error setting timeframe: {e}")
            return False
    
    async def add_indicator(self, indicator_name: str) -> bool:
        """Add indicator to chart"""
        try:
            logger.info(f"Adding indicator: {indicator_name}")
            await self.page.evaluate(f"window.TVHelper.addIndicator('{indicator_name}')")
            await asyncio.sleep(2)
            return True
        except Exception as e:
            logger.error(f"Error adding indicator: {e}")
            return False
    
    async def remove_indicator(self, indicator_name: str) -> bool:
        """Remove indicator from chart"""
        try:
            logger.info(f"Removing indicator: {indicator_name}")
            await self.page.evaluate(f"window.TVHelper.removeIndicator('{indicator_name}')")
            await asyncio.sleep(1)
            return True
        except Exception as e:
            logger.error(f"Error removing indicator: {e}")
            return False
    
    async def apply_strategy(self, pine_script: str, strategy_name: str) -> bool:
        """Apply a Pine Script strategy to the chart"""
        try:
            logger.info(f"Applying strategy: {strategy_name}")
            
            # Escape the script for JavaScript
            escaped_script = pine_script.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n')
            
            await self.page.evaluate(f"""
                window.TVHelper.addStrategyToChart(`{escaped_script}`)
            """)
            
            await asyncio.sleep(3)
            return True
            
        except Exception as e:
            logger.error(f"Error applying strategy: {e}")
            return False
    
    async def capture_chart(self) -> Optional[str]:
        """Capture chart screenshot as base64"""
        try:
            screenshot = await self.page.evaluate("window.TVHelper.takeScreenshot()")
            return screenshot
        except Exception as e:
            logger.error(f"Error capturing chart: {e}")
            return None
    
    async def get_watchlist_symbols(self) -> List[str]:
        """Get symbols from current watchlist"""
        try:
            symbols = await self.page.evaluate("""
                () => {
                    const symbols = [];
                    const rows = document.querySelectorAll('.watchlist-item');
                    rows.forEach(row => {
                        const sym = row.querySelector('.symbol');
                        if (sym) symbols.push(sym.textContent.trim());
                    });
                    return symbols;
                }
            """)
            return symbols
        except Exception as e:
            logger.error(f"Error getting watchlist: {e}")
            return []
    
    async def clear_watchlist(self) -> bool:
        """Clear all symbols from watchlist"""
        try:
            logger.info("Clearing watchlist...")
            await self.page.evaluate("""
                () => {
                    const items = document.querySelectorAll('.watchlist-item [data-name="remove"]');
                    items.forEach(item => item.click());
                }
            """)
            return True
        except Exception as e:
            logger.error(f"Error clearing watchlist: {e}")
            return False
    
    async def add_to_watchlist(self, symbol: str) -> bool:
        """Add symbol to watchlist"""
        try:
            logger.info(f"Adding {symbol} to watchlist")
            await self.page.evaluate(f"""
                () => {{
                    const addBtn = document.querySelector('[data-name="add-symbol-button"]');
                    if (addBtn) addBtn.click();
                    setTimeout(() => {{
                        const input = document.querySelector('input[placeholder*="Add"]');
                        if (input) {{
                            input.value = '{symbol}';
                            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            setTimeout(() => {{
                                const result = document.querySelector('.symbol-search-result');
                                if (result) result.click();
                            }}, 500);
                        }}
                    }}, 500);
                }}
            """)
            return True
        except Exception as e:
            logger.error(f"Error adding to watchlist: {e}")
            return False
    
    async def scan_for_signals(self, strategy_config: Dict) -> List[Signal]:
        """Scan current chart for trading signals"""
        signals = []
        
        try:
            # Get chart data
            state = await self.get_current_state()
            
            if not state.is_chart_loaded:
                logger.warning("Chart not loaded, cannot scan for signals")
                return signals
            
            # Check for strategy signals in DOM
            signal_data = await self.page.evaluate("""
                () => {
                    const signals = [];
                    // Look for strategy panel entries
                    const entries = document.querySelectorAll('[data-name="strategy-report-item"]');
                    entries.forEach(entry => {
                        const type = entry.querySelector('.direction');
                        const price = entry.querySelector('.price');
                        if (type && price) {
                            signals.push({
                                direction: type.textContent.trim(),
                                price: parseFloat(price.textContent)
                            });
                        }
                    });
                    return signals;
                }
            """)
            
            for sig in signal_data:
                signal = Signal(
                    symbol=state.symbol,
                    direction=sig.get('direction', 'NEUTRAL').upper(),
                    entry_price=sig.get('price', 0),
                    stop_loss=0,  # Calculate based on ATR or strategy
                    take_profit=0,
                    confidence=0.8,
                    timeframe=state.timeframe,
                    strategy=strategy_config.get('name', 'Unknown'),
                    indicators={ind: {} for ind in state.active_indicators},
                    timestamp=datetime.now(),
                    source="strategy"
                )
                signals.append(signal)
            
            return signals
            
        except Exception as e:
            logger.error(f"Error scanning for signals: {e}")
            return signals
    
    async def close(self):
        """Close browser connection"""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            self._is_connected = False
            logger.info("TradingView Controller closed")
        except Exception as e:
            logger.error(f"Error closing controller: {e}")


# Singleton instance
_controller: Optional[TradingViewController] = None


async def get_controller(config: Dict = None) -> TradingViewController:
    """Get or create singleton controller instance"""
    global _controller
    if _controller is None:
        _controller = TradingViewController(config or {})
        await _controller.initialize()
    return _controller
