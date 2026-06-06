"""
TradingView Desktop Controller
Controls TradingView Desktop application via Playwright using Native JS APIs
Integrates with Sapphire trading system
"""

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import base64
import hashlib

try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext
except ImportError:
    raise ImportError("Playwright not installed. Run: pip install playwright && playwright install chromium")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SignalDirection(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"
    EXIT = "EXIT"


class TimeFrame(Enum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"


@dataclass
class TradingViewState:
    """Current state of TradingView Desktop"""
    symbol: str = ""
    timeframe: str = ""
    watchlist: str = ""
    active_indicators: List[str] = field(default_factory=list)
    active_strategies: List[str] = field(default_factory=list)
    is_chart_loaded: bool = False
    current_price: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class TradingSignal:
    """Trading signal structure compatible with Sapphire"""
    id: str = field(default_factory=lambda: hashlib.md5(str(datetime.now()).encode()).hexdigest()[:12])
    symbol: str = ""
    direction: str = "NEUTRAL"
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    confidence: float = 0.0
    timeframe: str = "1h"
    strategy: str = ""
    indicators: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "tradingview"
    venue: str = ""  # ASTER or LIGHTER
    quantity: float = 0.0
    action: str = ""  # buy, sell, heartbeat, status
    secret: str = ""  # webhook secret for Sapphire
    
    def to_sapphire_webhook(self) -> Dict:
        """Convert to Sapphire webhook format"""
        return {
            "action": self.action or self.direction.lower(),
            "symbol": self.symbol,
            "venue": self.venue,
            "quantity": self.quantity,
            "strategy": self.strategy,
            "timeframe": self.timeframe,
            "secret": self.secret,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "confidence": self.confidence,
            "source": self.source,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class PineScript:
    """Pine Script representation"""
    name: str
    code: str
    version: str = "v5"
    category: str = "strategy"  # strategy, indicator, library
    author: str = ""
    description: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def validate(self) -> bool:
        """Basic Pine Script validation"""
        required_patterns = [
            r'//@version=' + self.version,
            r'(strategy|indicator|library)\s*\(\s*["\']' + re.escape(self.name) + r'["\']'
        ]
        for pattern in required_patterns:
            if not re.search(pattern, self.code, re.IGNORECASE):
                logger.warning(f"Pine Script validation failed: missing pattern {pattern}")
                return False
        return True


@dataclass
class CommunityScript:
    """Community script for testing"""
    name: str
    author: str
    source: str  # tradingview, github, custom
    script_id: str = ""
    pine_code: str = ""
    rating: float = 0.0
    installs: int = 0
    test_results: Dict[str, Any] = field(default_factory=dict)
    is_tested: bool = False
    

@dataclass
class Watchlist:
    """TradingView watchlist"""
    name: str
    symbols: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    is_default: bool = False
    
    def add_symbol(self, symbol: str):
        if symbol not in self.symbols:
            self.symbols.append(symbol)
    
    def remove_symbol(self, symbol: str):
        if symbol in self.symbols:
            self.symbols.remove(symbol)
    
    def clear(self):
        self.symbols = []


class TradingViewDesktopController:
    """
    Controller for TradingView Desktop automation using Native JavaScript APIs
    Integrates with Sapphire trading system
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.state = TradingViewState()
        self._callbacks: List[Callable] = []
        self._is_connected = False
        self._playwright = None
        
        # Sapphire integration config
        self.sapphire_config = config.get('sapphire', {})
        self.webhook_secret = self.sapphire_config.get('webhook_secret', '')
        self.webhook_url = self.sapphire_config.get('webhook_url', '')
        
        # Default venues
        self.default_venues = {
            'SOL': 'ASTER',
            'JUP': 'ASTER',
            'PYTH': 'ASTER',
            'BONK': 'ASTER',
            'WIF': 'ASTER',
            'BTC': 'LIGHTER',
            'ETH': 'LIGHTER',
            'HYPE': 'LIGHTER',
            'DOGE': 'LIGHTER',
            'AVAX': 'LIGHTER'
        }
        
    async def initialize(self, max_retries: int = 2) -> bool:
        """Initialize Playwright and connect to TradingView Desktop with retry logic"""
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"Initializing TradingView Desktop Controller (attempt {attempt + 1}/{max_retries + 1})...")
                
                if self._playwright is None:
                    self._playwright = await async_playwright().start()
                
                # Try to connect to existing Chrome/Edge with remote debugging
                cdp_port = self.config.get('cdp_port', 9222)
                
                if self.browser is None:
                    try:
                        self.browser = await self._playwright.chromium.connect_over_cdp(
                            f"http://localhost:{cdp_port}",
                            timeout=10000
                        )
                        logger.info(f"Connected to TradingView Desktop via CDP on port {cdp_port}")
                    except Exception as e:
                        if attempt < max_retries:
                            logger.warning(f"Could not connect via CDP: {e}. Retrying...")
                            await asyncio.sleep(2)
                            continue
                        else:
                            logger.error(f"Failed to connect via CDP after {max_retries + 1} attempts: {e}")
                            logger.info("Ensure TradingView Desktop is running with: --remote-debugging-port=9222")
                            return False
                
                # Create context with viewport if needed
                if self.context is None:
                    self.context = await self.browser.new_context(
                        viewport={
                            'width': self.config.get('viewport_width', 1920),
                            'height': self.config.get('viewport_height', 1080)
                        },
                        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    )
                
                # Get or create page
                if self.page is None:
                    pages = self.context.pages
                    if pages:
                        self.page = pages[0]
                        logger.info(f"Using existing page: {self.page.url}")
                    else:
                        self.page = await self.context.new_page()
                
                # Navigate to TradingView if not already there
                if 'tradingview.com' not in self.page.url:
                    logger.info("Navigating to TradingView...")
                    await self.page.goto('https://www.tradingview.com/chart/', timeout=60000)
                    await asyncio.sleep(3)
                
                # Wait for chart to load
                await self._wait_for_chart()
                
                # Inject enhanced helper script using native APIs
                await self._inject_enhanced_helper_script()
                
                # Update state
                await self.get_current_state()
                
                self._is_connected = True
                logger.info("TradingView Controller initialized successfully")
                return True
                
            except Exception as e:
                logger.error(f"Initialization error (attempt {attempt + 1}): {e}")
                if attempt < max_retries:
                    logger.info(f"Retrying in 2 seconds...")
                    await asyncio.sleep(2)
                else:
                    logger.error(f"Failed to initialize after {max_retries + 1} attempts")
                    return False
        
        return False
    
    async def _wait_for_chart(self, timeout: int = 30):
        """Wait for chart to load using native widget detection"""
        try:
            # Wait for TradingView widget to be available
            await self.page.wait_for_function(
                """() => {
                    return typeof window.tvWidget !== 'undefined' || 
                           document.querySelector('#chart-container iframe') !== null ||
                           document.querySelector('.chart-container') !== null;
                }""",
                timeout=timeout * 1000
            )
            logger.info("TradingView widget detected")
        except Exception as e:
            logger.warning(f"Widget detection timeout: {e}, continuing anyway")
    
    async def _inject_enhanced_helper_script(self):
        """Inject enhanced JavaScript helper using TradingView's native APIs"""
        helper_script = """
        // TradingView Native API Helper
        // Uses the official TradingView Charting Library API
        window.TVHelper = {
            // Get the TradingView widget instance
            getWidget() {
                // Try multiple ways to access the widget
                if (window.tvWidget) return window.tvWidget;
                if (window.TradingView && window.TradingView.widget) return window.TradingView.widget;
                
                // Try to find widget in chart container
                const container = document.querySelector('#chart-container');
                if (container && container._tvWidget) return container._tvWidget;
                
                // Try accessing via iframe
                const iframe = document.querySelector('#chart-container iframe');
                if (iframe && iframe.contentWindow) {
                    return iframe.contentWindow.tvWidget || 
                           iframe.contentWindow.TradingView?.widget;
                }
                
                return null;
            },
            
            // Get chart instance
            getChart() {
                const widget = this.getWidget();
                if (widget && widget.chart) {
                    return widget.chart();
                }
                return null;
            },
            
            // Get current symbol using native API
            getCurrentSymbol() {
                try {
                    const chart = this.getChart();
                    if (chart && chart.getSeries) {
                        const series = chart.getSeries();
                        if (series) {
                            // Try different properties
                            return series.symbol || 
                                   series.ticker || 
                                   series.name || 
                                   series.description || '';
                        }
                    }
                    
                    // Fallback to DOM
                    const titleEl = document.querySelector('.chart-gui-wrapper .title-wrapper, [data-name="legend-series-item"] .title');
                    if (titleEl) return titleEl.textContent.trim();
                    
                    return '';
                } catch (e) { 
                    console.error('getCurrentSymbol error:', e);
                    return ''; 
                }
            },
            
            // Get current timeframe/resolution
            getTimeframe() {
                try {
                    const chart = this.getChart();
                    if (chart && chart.getResolution) {
                        return chart.getResolution();
                    }
                    
                    // Fallback to DOM
                    const tfBtn = document.querySelector('[data-name="time-interval-menu"]');
                    return tfBtn ? tfBtn.textContent.trim() : '';
                } catch (e) { 
                    return ''; 
                }
            },
            
            // Set symbol using native TradingView API
            async setSymbol(symbol) {
                try {
                    console.log('Setting symbol to:', symbol);
                    const chart = this.getChart();
                    
                    // Method 1: Use native setSymbol if available
                    if (chart && chart.setSymbol) {
                        await new Promise((resolve, reject) => {
                            chart.setSymbol(symbol, () => {
                                console.log('Symbol set via native API:', symbol);
                                resolve();
                            });
                        });
                        return true;
                    }
                    
                    // Method 2: Use widget's headerReady
                    const widget = this.getWidget();
                    if (widget && widget.headerReady) {
                        await new Promise((resolve) => {
                            widget.headerReady(() => {
                                const symbolInput = document.querySelector('input[data-role="search"], .symbol-search input');
                                if (symbolInput) {
                                    symbolInput.value = symbol;
                                    symbolInput.dispatchEvent(new Event('input', { bubbles: true }));
                                    setTimeout(() => {
                                        const firstResult = document.querySelector('.symbol-search-result, [data-name="symbol-search-item"]');
                                        if (firstResult) firstResult.click();
                                        resolve();
                                    }, 500);
                                } else {
                                    resolve();
                                }
                            });
                        });
                        return true;
                    }
                    
                    // Method 3: Direct URL manipulation (most reliable)
                    const currentUrl = new URL(window.location.href);
                    currentUrl.searchParams.set('symbol', symbol);
                    window.history.pushState({}, '', currentUrl.toString());
                    
                    // Trigger symbol change event
                    window.dispatchEvent(new Event('symbolChange'));
                    
                    return true;
                } catch (e) { 
                    console.error('setSymbol error:', e);
                    return false; 
                }
            },
            
            // Set timeframe/resolution using native API
            async setTimeframe(tf) {
                try {
                    console.log('Setting timeframe to:', tf);
                    const chart = this.getChart();
                    
                    // Method 1: Native API
                    if (chart && chart.setResolution) {
                        await new Promise((resolve) => {
                            chart.setResolution(tf, () => {
                                console.log('Timeframe set via native API:', tf);
                                resolve();
                            });
                        });
                        return true;
                    }
                    
                    // Method 2: Widget API
                    const widget = this.getWidget();
                    if (widget && widget.changeResolution) {
                        widget.changeResolution(tf);
                        return true;
                    }
                    
                    // Method 3: Click on timeframe button
                    const tfBtn = document.querySelector('[data-name="time-interval-menu"]');
                    if (tfBtn) {
                        tfBtn.click();
                        await new Promise(r => setTimeout(r, 300));
                        
                        const items = document.querySelectorAll('[data-value]');
                        for (let item of items) {
                            if (item.textContent.trim() === tf || item.getAttribute('data-value') === tf) {
                                item.click();
                                await new Promise(r => setTimeout(r, 500));
                                return true;
                            }
                        }
                    }
                    
                    return false;
                } catch (e) { 
                    console.error('setTimeframe error:', e);
                    return false; 
                }
            },
            
            // Get all indicators using native API
            getIndicators() {
                try {
                    const chart = this.getChart();
                    if (chart && chart.getAllStudies) {
                        const studies = chart.getAllStudies();
                        return studies.map(s => s.name || s.id || 'Unknown');
                    }
                    
                    // Fallback to DOM
                    const indicators = [];
                    const pills = document.querySelectorAll('[data-name="legend-source-title"]');
                    pills.forEach(p => indicators.push(p.textContent.trim()));
                    return indicators;
                } catch (e) { 
                    return []; 
                }
            },
            
            // Get active strategies
            getStrategies() {
                try {
                    const strategies = [];
                    const strategyElements = document.querySelectorAll('[data-name="strategy-tab"]');
                    strategyElements.forEach(s => strategies.push(s.textContent.trim()));
                    return strategies;
                } catch (e) { 
                    return []; 
                }
            },
            
            // Add indicator using native API
            async addIndicator(name) {
                try {
                    const chart = this.getChart();
                    
                    // Try native API first
                    if (chart && chart.createStudy) {
                        await new Promise((resolve, reject) => {
                            chart.createStudy(name, false, false, [], (entityId) => {
                                console.log('Study created:', entityId);
                                resolve(entityId);
                            });
                        });
                        return true;
                    }
                    
                    // Fallback to UI
                    const indBtn = document.querySelector('[data-name="indicator-menus"], [data-name="insert-indicator"]');
                    if (indBtn) indBtn.click();
                    await new Promise(r => setTimeout(r, 500));
                    
                    const search = document.querySelector('input[placeholder*="Search"]');
                    if (search) {
                        search.value = name;
                        search.dispatchEvent(new Event('input', { bubbles: true }));
                        await new Promise(r => setTimeout(r, 500));
                        
                        const result = document.querySelector('.indicator-search-result, [data-name="study"]');
                        if (result) {
                            result.click();
                            await new Promise(r => setTimeout(r, 1500));
                            return true;
                        }
                    }
                    return false;
                } catch (e) { 
                    console.error('addIndicator error:', e);
                    return false; 
                }
            },
            
            // Remove indicator using native API
            async removeIndicator(name) {
                try {
                    const chart = this.getChart();
                    
                    if (chart && chart.removeEntity) {
                        const studies = chart.getAllStudies();
                        const study = studies.find(s => (s.name || s.id) === name);
                        if (study && study.id) {
                            chart.removeEntity(study.id);
                            return true;
                        }
                    }
                    
                    // Fallback to DOM
                    const indicators = document.querySelectorAll('[data-name="legend-source-item"]');
                    for (let ind of indicators) {
                        const title = ind.querySelector('[data-name="legend-source-title"]');
                        if (title && title.textContent.includes(name)) {
                            const closeBtn = ind.querySelector('[data-name="legend-remove-action"]');
                            if (closeBtn) {
                                closeBtn.click();
                                await new Promise(r => setTimeout(r, 500));
                                return true;
                            }
                        }
                    }
                    return false;
                } catch (e) { 
                    console.error('removeIndicator error:', e);
                    return false; 
                }
            },
            
            // Get current price using native API
            getPrice() {
                try {
                    const chart = this.getChart();
                    if (chart && chart.getSeries) {
                        const series = chart.getSeries();
                        if (series && series.price) {
                            return parseFloat(series.price());
                        }
                    }
                    
                    // Fallback to DOM
                    const price = document.querySelector('.chart-gui-wrapper .price-value, [data-name="legend-series-item"] .value');
                    return price ? parseFloat(price.textContent.replace(/,/g, '')) : null;
                } catch (e) { 
                    return null; 
                }
            },
            
            // Get OHLCV data for current visible range
            getVisibleRangeData() {
                try {
                    const chart = this.getChart();
                    if (chart && chart.getData) {
                        return chart.getData();
                    }
                    return null;
                } catch (e) {
                    console.error('getVisibleRangeData error:', e);
                    return null;
                }
            },
            
            // Get chart properties
            getChartProperties() {
                try {
                    const chart = this.getChart();
                    if (!chart) return null;
                    
                    return {
                        timezone: chart.getTimezone ? chart.getTimezone() : null,
                        priceScaleMode: chart.getPriceScaleMode ? chart.getPriceScaleMode() : null,
                        crossHairMode: chart.getCrossHairMode ? chart.getCrossHairMode() : null
                    };
                } catch (e) {
                    return null;
                }
            },
            
            // Take screenshot using native API
            async takeScreenshot() {
                try {
                    const widget = this.getWidget();
                    
                    // Try widget's screenshot method
                    if (widget && widget.takeScreenshot) {
                        return await widget.takeScreenshot();
                    }
                    
                    // Fallback to canvas
                    const canvas = document.querySelector('canvas.chart-gui-canvas');
                    if (canvas) {
                        return canvas.toDataURL('image/png');
                    }
                } catch (e) { 
                    console.error('screenshot error:', e);
                }
                return null;
            },
            
            // Open Pine Editor
            async openPineEditor() {
                try {
                    const widget = this.getWidget();
                    
                    if (widget && widget.showPineEditor) {
                        widget.showPineEditor();
                        return true;
                    }
                    
                    const btn = document.querySelector('[data-name="script-editor"], [data-name="pine-editor-toggle"]');
                    if (btn) {
                        btn.click();
                        await new Promise(r => setTimeout(r, 1000));
                        return true;
                    }
                } catch (e) { 
                    console.error('openPineEditor error:', e);
                }
                return false;
            },
            
            // Get watchlist symbols
            getWatchlistSymbols() {
                try {
                    const symbols = [];
                    const rows = document.querySelectorAll('.watchlist-item, [data-name="watchlist-item"]');
                    rows.forEach(row => {
                        const sym = row.querySelector('.symbol, [data-name="symbol"]');
                        if (sym) symbols.push(sym.textContent.trim());
                    });
                    return symbols;
                } catch (e) { 
                    return []; 
                }
            },
            
            // Clear watchlist
            async clearWatchlist() {
                try {
                    const items = document.querySelectorAll('.watchlist-item [data-name="remove"], [data-name="watchlist-item"] [data-name="remove"]');
                    items.forEach(item => item.click());
                    await new Promise(r => setTimeout(r, 500));
                    return true;
                } catch (e) { 
                    return false; 
                }
            },
            
            // Add to watchlist
            async addToWatchlist(symbol) {
                try {
                    const addBtn = document.querySelector('[data-name="add-symbol-button"], .add-symbol-button');
                    if (addBtn) {
                        addBtn.click();
                        await new Promise(r => setTimeout(r, 500));
                        
                        const input = document.querySelector('input[placeholder*="Add"], input[placeholder*="Search"]');
                        if (input) {
                            input.value = symbol;
                            input.dispatchEvent(new Event('input', { bubbles: true }));
                            await new Promise(r => setTimeout(r, 500));
                            
                            const result = document.querySelector('.symbol-search-result, .watchlist-search-result');
                            if (result) {
                                result.click();
                                await new Promise(r => setTimeout(r, 500));
                                return true;
                            }
                        }
                    }
                    return false;
                } catch (e) { 
                    return false; 
                }
            },
            
            // Apply Pine Script
            async applyPineScript(code) {
                try {
                    await this.openPineEditor();
                    await new Promise(r => setTimeout(r, 1500));
                    
                    const editor = document.querySelector('.monaco-editor');
                    if (editor) {
                        const textarea = editor.querySelector('textarea');
                        if (textarea) {
                            textarea.value = code;
                            textarea.dispatchEvent(new Event('input', { bubbles: true }));
                            await new Promise(r => setTimeout(r, 500));
                            
                            const addBtn = document.querySelector('[data-name="add-script-to-chart"], [data-name="apply-script"]');
                            if (addBtn) {
                                addBtn.click();
                                await new Promise(r => setTimeout(r, 2000));
                                return true;
                            }
                        }
                    }
                    return false;
                } catch (e) { 
                    return false; 
                }
            },
            
            // Execute custom function on chart
            executeOnChart(fn) {
                try {
                    const chart = this.getChart();
                    if (chart) {
                        return fn(chart);
                    }
                    return null;
                } catch (e) {
                    console.error('executeOnChart error:', e);
                    return null;
                }
            }
        };
        
        console.log('TradingView Native API Helper injected successfully');
        """
        await self.page.evaluate(helper_script)
        logger.info("Enhanced helper script with native TradingView APIs injected")
    
    async def get_current_state(self) -> TradingViewState:
        """Get current chart state with error handling"""
        if not self.page:
            return TradingViewState()
        
        try:
            # Check if TVHelper exists first
            helper_exists = await self.page.evaluate("typeof window.TVHelper !== 'undefined'")
            
            if not helper_exists:
                logger.warning("TVHelper not found, re-injecting...")
                await self._inject_enhanced_helper_script()
                await asyncio.sleep(0.5)
            
            state = await self.page.evaluate("""
                () => {
                    try {
                        const chart = window.TVHelper.getChart();
                        const properties = window.TVHelper.getChartProperties();
                        
                        return {
                            symbol: window.TVHelper.getCurrentSymbol(),
                            timeframe: window.TVHelper.getTimeframe(),
                            indicators: window.TVHelper.getIndicators(),
                            strategies: window.TVHelper.getStrategies(),
                            price: window.TVHelper.getPrice(),
                            properties: properties,
                            error: null
                        };
                    } catch (e) {
                        return { error: e.toString() };
                    }
                }
            """)
            
            if state.get('error'):
                logger.error(f"JavaScript error getting state: {state['error']}")
                return self.state
            
            self.state = TradingViewState(
                symbol=state.get('symbol', ''),
                timeframe=state.get('timeframe', ''),
                active_indicators=state.get('indicators', []),
                active_strategies=state.get('strategies', []),
                is_chart_loaded=bool(state.get('price')),
                current_price=state.get('price', 0.0) or 0.0,
                timestamp=datetime.now()
            )
            
            logger.info(f"State updated: {self.state.symbol} @ {self.state.timeframe}, price: {self.state.current_price}")
            return self.state
            
        except Exception as e:
            logger.error(f"Error getting state: {e}")
            return self.state
    
    async def set_symbol(self, symbol: str) -> bool:
        """Change chart symbol using native TradingView API"""
        try:
            logger.info(f"Setting symbol to: {symbol}")
            result = await self.page.evaluate(f"window.TVHelper.setSymbol('{symbol}')")
            await asyncio.sleep(2)
            await self.get_current_state()  # Refresh state
            return result
        except Exception as e:
            logger.error(f"Error setting symbol: {e}")
            return False
    
    async def set_timeframe(self, timeframe: str) -> bool:
        """Change chart timeframe using native TradingView API"""
        try:
            logger.info(f"Setting timeframe to: {timeframe}")
            result = await self.page.evaluate(f"window.TVHelper.setTimeframe('{timeframe}')")
            await asyncio.sleep(1)
            await self.get_current_state()  # Refresh state
            return result
        except Exception as e:
            logger.error(f"Error setting timeframe: {e}")
            return False
    
    async def add_indicator(self, indicator_name: str) -> bool:
        """Add indicator to chart using native API"""
        try:
            logger.info(f"Adding indicator: {indicator_name}")
            result = await self.page.evaluate(f"window.TVHelper.addIndicator('{indicator_name}')")
            await self.get_current_state()
            return result
        except Exception as e:
            logger.error(f"Error adding indicator: {e}")
            return False
    
    async def remove_indicator(self, indicator_name: str) -> bool:
        """Remove indicator from chart using native API"""
        try:
            logger.info(f"Removing indicator: {indicator_name}")
            result = await self.page.evaluate(f"window.TVHelper.removeIndicator('{indicator_name}')")
            await self.get_current_state()
            return result
        except Exception as e:
            logger.error(f"Error removing indicator: {e}")
            return False
    
    async def apply_pine_script(self, pine_script: PineScript) -> bool:
        """Apply a Pine Script to the chart"""
        try:
            logger.info(f"Applying Pine Script: {pine_script.name}")
            
            if not pine_script.validate():
                logger.error("Pine Script validation failed")
                return False
            
            # Escape the script for JavaScript
            escaped_code = pine_script.code.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n')
            
            result = await self.page.evaluate(f"window.TVHelper.applyPineScript('{escaped_code}')")
            return result
            
        except Exception as e:
            logger.error(f"Error applying Pine Script: {e}")
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
            symbols = await self.page.evaluate("window.TVHelper.getWatchlistSymbols()")
            return symbols
        except Exception as e:
            logger.error(f"Error getting watchlist: {e}")
            return []
    
    async def clear_watchlist(self) -> bool:
        """Clear all symbols from watchlist"""
        try:
            logger.info("Clearing watchlist...")
            result = await self.page.evaluate("window.TVHelper.clearWatchlist()")
            return result
        except Exception as e:
            logger.error(f"Error clearing watchlist: {e}")
            return False
    
    async def add_to_watchlist(self, symbol: str) -> bool:
        """Add symbol to watchlist"""
        try:
            logger.info(f"Adding {symbol} to watchlist")
            result = await self.page.evaluate(f"window.TVHelper.addToWatchlist('{symbol}')")
            return result
        except Exception as e:
            logger.error(f"Error adding to watchlist: {e}")
            return False
    
    async def get_chart_data(self) -> Optional[Dict]:
        """Get OHLCV data from current chart"""
        try:
            data = await self.page.evaluate("window.TVHelper.getVisibleRangeData()")
            return data
        except Exception as e:
            logger.error(f"Error getting chart data: {e}")
            return None
    
    async def execute_custom_js(self, js_code: str) -> Any:
        """Execute custom JavaScript with access to TradingView widget"""
        try:
            wrapper = f"""
                (function() {{
                    const widget = window.TVHelper.getWidget();
                    const chart = window.TVHelper.getChart();
                    {js_code}
                }})()
            """
            return await self.page.evaluate(wrapper)
        except Exception as e:
            logger.error(f"Error executing custom JS: {e}")
            return None
    
    async def scan_for_signals(self, strategy_config: Dict = None) -> List[TradingSignal]:
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
                    
                    // Method 1: Check for study/strategy output in chart
                    const chart = window.TVHelper.getChart();
                    if (chart && chart.getAllStudies) {
                        const studies = chart.getAllStudies();
                        studies.forEach(study => {
                            if (study.isStrategy || study.name?.toLowerCase().includes('strategy')) {
                                signals.push({
                                    direction: study.output || 'NEUTRAL',
                                    price: study.price || null,
                                    name: study.name
                                });
                            }
                        });
                    }
                    
                    // Method 2: Look for strategy panel entries
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
                    
                    // Method 3: Look for alert markers on chart
                    const markers = document.querySelectorAll('.alert-marker, [data-name="alert"]');
                    markers.forEach(marker => {
                        const label = marker.getAttribute('data-label') || marker.textContent;
                        if (label) {
                            signals.push({
                                direction: label.includes('Buy') || label.includes('Long') ? 'buy' : 'sell',
                                price: null,
                                label: label
                            });
                        }
                    });
                    
                    return signals;
                }
            """)
            
            for sig in signal_data:
                direction = sig.get('direction', 'neutral').upper()
                if direction in ['BUY', 'LONG']:
                    direction = 'LONG'
                elif direction in ['SELL', 'SHORT']:
                    direction = 'SHORT'
                else:
                    direction = 'NEUTRAL'
                
                # Determine venue based on symbol
                symbol = state.symbol
                base_symbol = symbol.replace('USDT', '').replace('USD', '').replace('PERP', '')
                venue = self.default_venues.get(base_symbol, 'LIGHTER')
                
                signal = TradingSignal(
                    symbol=symbol,
                    direction=direction,
                    entry_price=sig.get('price', state.current_price),
                    stop_loss=0,
                    take_profit=0,
                    confidence=0.8,
                    timeframe=state.timeframe,
                    strategy=strategy_config.get('name', 'tradingview_strategy') if strategy_config else 'tradingview_strategy',
                    indicators={ind: {} for ind in state.active_indicators},
                    timestamp=datetime.now(),
                    source="tradingview",
                    venue=venue,
                    quantity=0,
                    action=direction.lower(),
                    secret=self.webhook_secret
                )
                signals.append(signal)
            
            return signals
            
        except Exception as e:
            logger.error(f"Error scanning for signals: {e}")
            return signals
    
    async def send_signal_to_sapphire(self, signal: TradingSignal) -> bool:
        """Send trading signal to Sapphire via webhook"""
        try:
            import aiohttp
            
            payload = signal.to_sapphire_webhook()
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    headers={'Content-Type': 'application/json'}
                ) as response:
                    if response.status == 200:
                        logger.info(f"Signal sent to Sapphire: {signal.symbol} {signal.direction}")
                        return True
                    else:
                        logger.error(f"Failed to send signal: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Error sending signal to Sapphire: {e}")
            return False
    
    async def close(self):
        """Close browser connection"""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self._playwright:
                await self._playwright.stop()
            self._is_connected = False
            logger.info("TradingView Controller closed")
        except Exception as e:
            logger.error(f"Error closing controller: {e}")


# Singleton instance
_controller: Optional[TradingViewDesktopController] = None


def get_controller(config: Dict = None) -> TradingViewDesktopController:
    """
    Get or create singleton controller instance.
    Note: This does NOT initialize - call initialize() separately.
    """
    global _controller
    if _controller is None:
        _controller = TradingViewDesktopController(config or {})
    return _controller


async def init_controller(config: Dict = None) -> TradingViewDesktopController:
    """
    Get and initialize controller in one call.
    Use this if you want auto-initialization.
    """
    controller = get_controller(config)
    if not controller._is_connected:
        await controller.initialize()
    return controller
