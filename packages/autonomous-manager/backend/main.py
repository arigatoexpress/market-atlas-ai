"""
TradingView Desktop Autonomous Manager - FastAPI Backend
Integrates with Sapphire Trading System
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import our modules
from app.core.config_loader import get_config, AppConfig
from app.core.tv_desktop_controller import (
    TradingViewDesktopController, TradingSignal, TradingViewState, PineScript
)
from app.strategies.strategy_manager import (
    StrategyManager, Strategy, StrategyResult, get_strategy_manager
)
from app.watchlist.watchlist_manager import (
    WatchlistManager, Watchlist, get_watchlist_manager
)
from app.services.community_script_tester import (
    CommunityScriptTester, CommunityScript, get_script_tester
)
from app.integrations.sapphire_bridge import (
    SapphireBridge, SapphireConfig, get_sapphire_bridge
)

# Load configuration
config = get_config("../config/settings.yaml")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global state
tv_controller: Optional[TradingViewDesktopController] = None
strategy_manager: StrategyManager = get_strategy_manager("../strategies")
watchlist_manager: WatchlistManager = get_watchlist_manager("../watchlists")
script_tester: CommunityScriptTester = get_script_tester("../generated_scripts")
sapphire_bridge: SapphireBridge = get_sapphire_bridge()

# Configuration storage
_tv_config: Dict[str, Any] = {
    "headless": config.tradingview.headless,
    "cdp_port": config.tradingview.cdp_port,
    "viewport_width": config.tradingview.viewport_width,
    "viewport_height": config.tradingview.viewport_height,
    "timeout": config.tradingview.timeout,
    "sapphire": {
        "webhook_url": config.sapphire.webhook_url,
        "webhook_secret": config.sapphire.webhook_secret,
    }
}

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def broadcast(self, message: Dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        
        # Clean up disconnected
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()


# Pydantic models
class TVStateResponse(BaseModel):
    symbol: str
    timeframe: str
    active_indicators: List[str]
    active_strategies: List[str]
    is_chart_loaded: bool
    current_price: float
    timestamp: datetime


class SignalRequest(BaseModel):
    symbol: str
    direction: str
    entry_price: float = 0
    stop_loss: float = 0
    take_profit: float = 0
    confidence: float = 0.8
    timeframe: str = "1h"
    strategy: str = ""
    venue: str = ""
    quantity: float = 0


class StrategyCreateRequest(BaseModel):
    name: str
    pine_code: str
    description: str = ""
    author: str = ""
    category: str = "strategy"
    preferred_symbols: List[str] = []
    preferred_timeframes: List[str] = []


class WatchlistCreateRequest(BaseModel):
    name: str
    category: str = "custom"
    description: str = ""


class ScriptImportRequest(BaseModel):
    name: str
    pine_code: str
    author: str = ""
    source: str = "custom"
    script_type: str = "indicator"


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    global tv_controller
    
    logger.info("Starting TradingView Desktop Autonomous Manager...")
    
    # Initialize TradingView controller (but don't connect yet - wait for user)
    # tv_controller will be initialized on first use
    
    yield
    
    # Cleanup
    logger.info("Shutting down...")
    if tv_controller:
        await tv_controller.close()
    await sapphire_bridge.close()


# Create FastAPI app
app = FastAPI(
    title="TradingView Desktop Autonomous Manager",
    description="Autonomous management system for TradingView Desktop with Sapphire integration",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint with comprehensive status"""
    # Test Sapphire connection with timeout to avoid hanging
    sapphire_status = False
    sapphire_error = None
    try:
        import asyncio
        sapphire_status = await asyncio.wait_for(
            sapphire_bridge.test_connection(), 
            timeout=3.0
        )
    except asyncio.TimeoutError:
        sapphire_error = "Connection timeout"
        sapphire_status = False
    except Exception as e:
        sapphire_error = str(e)
        sapphire_status = False
    
    # Get TV controller status
    tv_status = {
        "connected": tv_controller is not None and tv_controller._is_connected,
        "symbol": "",
        "timeframe": ""
    }
    
    if tv_controller and tv_controller._is_connected:
        try:
            state = await asyncio.wait_for(tv_controller.get_current_state(), timeout=3.0)
            tv_status["symbol"] = state.symbol
            tv_status["timeframe"] = state.timeframe
        except Exception as e:
            tv_status["error"] = str(e)
    
    return {
        "status": "healthy" if sapphire_status or not tv_status["connected"] else "degraded",
        "timestamp": datetime.now().isoformat(),
        "version": config.version,
        "sapphire": {
            "connected": sapphire_status,
            "url": sapphire_bridge.config.webhook_url,
            "error": sapphire_error
        },
        "tradingview": tv_status,
        "data": {
            "strategies_loaded": len(strategy_manager.strategies),
            "watchlists_loaded": len(watchlist_manager.watchlists),
            "scripts_loaded": len(script_tester.scripts)
        },
        "config": {
            "tv_headless": config.tradingview.headless,
            "tv_cdp_port": config.tradingview.cdp_port,
            "sapphire_default_venue": config.sapphire.default_venue
        }
    }


# TradingView Controller endpoints
@app.post("/tv/connect")
async def connect_tv(config: Dict[str, Any] = None):
    """Connect to TradingView Desktop"""
    global tv_controller, _tv_config
    
    try:
        # Merge provided config with stored config
        merged_config = {**_tv_config, **(config or {})}
        
        if tv_controller is None:
            tv_controller = TradingViewDesktopController(merged_config)
        
        success = await tv_controller.initialize()
        
        if success:
            _tv_config = merged_config  # Store successful config
            return {
                "status": "connected", 
                "message": "TradingView Desktop connected",
                "config": {
                    "headless": merged_config.get("headless", False),
                    "cdp_port": merged_config.get("cdp_port", 9222),
                    "viewport": {
                        "width": merged_config.get("viewport_width", 1920),
                        "height": merged_config.get("viewport_height", 1080)
                    }
                }
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to connect to TradingView. Ensure TradingView Desktop is running with --remote-debugging-port=9222")
    
    except Exception as e:
        logger.error(f"Connection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tv/disconnect")
async def disconnect_tv():
    """Disconnect from TradingView Desktop"""
    global tv_controller
    
    if tv_controller:
        await tv_controller.close()
        tv_controller = None
    
    return {"status": "disconnected"}


@app.get("/tv/state", response_model=TVStateResponse)
async def get_tv_state():
    """Get current TradingView state"""
    if not tv_controller or not tv_controller._is_connected:
        raise HTTPException(status_code=503, detail="TradingView not connected")
    
    state = await tv_controller.get_current_state()
    return TVStateResponse(
        symbol=state.symbol,
        timeframe=state.timeframe,
        active_indicators=state.active_indicators,
        active_strategies=state.active_strategies,
        is_chart_loaded=state.is_chart_loaded,
        current_price=state.current_price,
        timestamp=state.timestamp
    )


@app.post("/tv/symbol/{symbol}")
async def set_symbol(symbol: str):
    """Set TradingView symbol"""
    if not tv_controller or not tv_controller._is_connected:
        raise HTTPException(status_code=503, detail="TradingView not connected")
    
    success = await tv_controller.set_symbol(symbol)
    if success:
        return {"status": "success", "symbol": symbol}
    else:
        raise HTTPException(status_code=500, detail="Failed to set symbol")


@app.post("/tv/timeframe/{timeframe}")
async def set_timeframe(timeframe: str):
    """Set TradingView timeframe"""
    if not tv_controller or not tv_controller._is_connected:
        raise HTTPException(status_code=503, detail="TradingView not connected")
    
    success = await tv_controller.set_timeframe(timeframe)
    if success:
        return {"status": "success", "timeframe": timeframe}
    else:
        raise HTTPException(status_code=500, detail="Failed to set timeframe")


@app.post("/tv/indicator/{indicator_name}")
async def add_indicator(indicator_name: str):
    """Add indicator to chart"""
    if not tv_controller or not tv_controller._is_connected:
        raise HTTPException(status_code=503, detail="TradingView not connected")
    
    success = await tv_controller.add_indicator(indicator_name)
    if success:
        return {"status": "success", "indicator": indicator_name}
    else:
        raise HTTPException(status_code=500, detail="Failed to add indicator")


@app.delete("/tv/indicator/{indicator_name}")
async def remove_indicator(indicator_name: str):
    """Remove indicator from chart"""
    if not tv_controller or not tv_controller._is_connected:
        raise HTTPException(status_code=503, detail="TradingView not connected")
    
    success = await tv_controller.remove_indicator(indicator_name)
    if success:
        return {"status": "success", "indicator": indicator_name}
    else:
        raise HTTPException(status_code=500, detail="Failed to remove indicator")


@app.post("/tv/screenshot")
async def capture_screenshot():
    """Capture chart screenshot"""
    if not tv_controller or not tv_controller._is_connected:
        raise HTTPException(status_code=503, detail="TradingView not connected")
    
    screenshot = await tv_controller.capture_chart()
    if screenshot:
        return {"status": "success", "screenshot": screenshot}
    else:
        raise HTTPException(status_code=500, detail="Failed to capture screenshot")


# Strategy endpoints
@app.get("/strategies")
async def list_strategies(category: str = None, active_only: bool = False):
    """List all strategies"""
    strategies = strategy_manager.list_strategies(category, active_only)
    return [s.to_dict() for s in strategies]


@app.post("/strategies")
async def create_strategy(request: StrategyCreateRequest):
    """Create a new strategy"""
    strategy = strategy_manager.create_strategy(
        name=request.name,
        pine_code=request.pine_code,
        description=request.description,
        author=request.author,
        category=request.category,
        preferred_symbols=request.preferred_symbols,
        preferred_timeframes=request.preferred_timeframes
    )
    return strategy.to_dict()


@app.get("/strategies/{strategy_id}")
async def get_strategy(strategy_id: str):
    """Get strategy by ID"""
    strategy = strategy_manager.get_strategy(strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strategy.to_dict()


@app.post("/strategies/{strategy_id}/apply")
async def apply_strategy(strategy_id: str):
    """Apply strategy to TradingView"""
    if not tv_controller or not tv_controller._is_connected:
        raise HTTPException(status_code=503, detail="TradingView not connected")
    
    strategy = strategy_manager.get_strategy(strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    pine_script = PineScript(
        name=strategy.name,
        code=strategy.pine_code,
        version=strategy.version,
        category=strategy.category
    )
    
    success = await tv_controller.apply_pine_script(pine_script)
    if success:
        return {"status": "success", "strategy": strategy.name}
    else:
        raise HTTPException(status_code=500, detail="Failed to apply strategy")


@app.post("/strategies/{strategy_id}/activate")
async def activate_strategy(strategy_id: str):
    """Activate strategy"""
    success = strategy_manager.activate_strategy(strategy_id)
    if success:
        return {"status": "success"}
    else:
        raise HTTPException(status_code=400, detail="Failed to activate strategy")


@app.post("/strategies/{strategy_id}/deactivate")
async def deactivate_strategy(strategy_id: str):
    """Deactivate strategy"""
    success = strategy_manager.deactivate_strategy(strategy_id)
    if success:
        return {"status": "success"}
    else:
        raise HTTPException(status_code=400, detail="Failed to deactivate strategy")


@app.delete("/strategies/{strategy_id}")
async def delete_strategy(strategy_id: str):
    """Delete strategy"""
    success = strategy_manager.delete_strategy(strategy_id)
    if success:
        return {"status": "success"}
    else:
        raise HTTPException(status_code=404, detail="Strategy not found")


# Watchlist endpoints
@app.get("/watchlists")
async def list_watchlists(category: str = None):
    """List all watchlists"""
    watchlists = watchlist_manager.list_watchlists(category)
    return [w.to_dict() for w in watchlists]


@app.post("/watchlists")
async def create_watchlist(request: WatchlistCreateRequest):
    """Create a new watchlist"""
    watchlist = watchlist_manager.create_watchlist(
        name=request.name,
        category=request.category,
        description=request.description
    )
    return watchlist.to_dict()


@app.get("/watchlists/{watchlist_id}")
async def get_watchlist(watchlist_id: str):
    """Get watchlist by ID"""
    watchlist = watchlist_manager.get_watchlist(watchlist_id)
    if not watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    return watchlist.to_dict()


@app.post("/watchlists/{watchlist_id}/symbols/{symbol}")
async def add_symbol_to_watchlist(watchlist_id: str, symbol: str, venue: str = ""):
    """Add symbol to watchlist"""
    success = watchlist_manager.add_symbol(
        watchlist_id, symbol,
        type="crypto", venue=venue
    )
    if success:
        return {"status": "success", "symbol": symbol}
    else:
        raise HTTPException(status_code=400, detail="Failed to add symbol")


@app.delete("/watchlists/{watchlist_id}/symbols/{symbol}")
async def remove_symbol_from_watchlist(watchlist_id: str, symbol: str):
    """Remove symbol from watchlist"""
    success = watchlist_manager.remove_symbol(watchlist_id, symbol)
    if success:
        return {"status": "success", "symbol": symbol}
    else:
        raise HTTPException(status_code=404, detail="Symbol not found in watchlist")


@app.post("/watchlists/{watchlist_id}/clear")
async def clear_watchlist(watchlist_id: str):
    """Clear all symbols from watchlist"""
    success = watchlist_manager.clear_watchlist(watchlist_id)
    if success:
        return {"status": "success"}
    else:
        raise HTTPException(status_code=404, detail="Watchlist not found")


@app.post("/watchlists/{watchlist_id}/sync")
async def sync_watchlist_to_tv(watchlist_id: str):
    """Sync watchlist to TradingView"""
    if not tv_controller or not tv_controller._is_connected:
        raise HTTPException(status_code=503, detail="TradingView not connected")
    
    watchlist = watchlist_manager.get_watchlist(watchlist_id)
    if not watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    
    # Clear current watchlist and add symbols
    await tv_controller.clear_watchlist()
    
    for symbol in watchlist.symbols:
        await tv_controller.add_to_watchlist(symbol)
        await asyncio.sleep(0.5)  # Rate limit
    
    watchlist_manager.mark_synced(watchlist_id)
    
    return {"status": "success", "symbols_synced": len(watchlist.symbols)}


# Community Script endpoints
@app.get("/scripts")
async def list_scripts(source: str = None, approved_only: bool = False):
    """List community scripts"""
    scripts = script_tester.list_scripts(source=source, approved_only=approved_only)
    return [s.to_dict() for s in scripts]


@app.post("/scripts")
async def import_script(request: ScriptImportRequest):
    """Import a community script"""
    script = script_tester.add_script(
        name=request.name,
        pine_code=request.pine_code,
        author=request.author,
        source=request.source,
        script_type=request.script_type
    )
    return script.to_dict()


@app.get("/scripts/{script_id}")
async def get_script(script_id: str):
    """Get script by ID"""
    script = script_tester.get_script(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return script.to_dict()


@app.post("/scripts/{script_id}/test")
async def test_script(script_id: str, background_tasks: BackgroundTasks):
    """Test a community script"""
    if not tv_controller or not tv_controller._is_connected:
        raise HTTPException(status_code=503, detail="TradingView not connected")
    
    # Run test in background
    async def run_test():
        result = await script_tester.test_script(script_id, tv_controller)
        # Broadcast result via WebSocket
        await manager.broadcast({
            "type": "test_completed",
            "script_id": script_id,
            "result": {
                "test_id": result.test_id,
                "status": result.status.value,
                "score": result.overall_score
            }
        })
    
    background_tasks.add_task(run_test)
    
    return {"status": "testing_started", "script_id": script_id}


@app.get("/scripts/{script_id}/report")
async def get_script_report(script_id: str):
    """Get test report for a script"""
    report = script_tester.get_test_report(script_id)
    if not report:
        raise HTTPException(status_code=404, detail="Script not found")
    return report


@app.post("/scripts/{script_id}/approve")
async def approve_script(script_id: str, symbols: List[str] = None, timeframes: List[str] = None):
    """Approve a script for Sapphire use"""
    success = script_tester.approve_script(
        script_id,
        approved_by="admin",
        symbols=symbols or [],
        timeframes=timeframes or ["1h", "4h"]
    )
    if success:
        return {"status": "approved"}
    else:
        raise HTTPException(status_code=400, detail="Failed to approve script")


# Signal endpoints
@app.post("/signals/send")
async def send_signal(request: SignalRequest):
    """Send trading signal to Sapphire"""
    signal = TradingSignal(
        symbol=request.symbol,
        direction=request.direction,
        entry_price=request.entry_price,
        stop_loss=request.stop_loss,
        take_profit=request.take_profit,
        confidence=request.confidence,
        timeframe=request.timeframe,
        strategy=request.strategy,
        venue=request.venue or sapphire_bridge.get_venue_for_symbol(request.symbol),
        quantity=request.quantity,
        action=request.direction.lower(),
        secret=sapphire_bridge.config.webhook_secret
    )
    
    success = await sapphire_bridge.send_signal(signal.to_sapphire_webhook())
    if success:
        return {"status": "success", "signal_sent": True}
    else:
        raise HTTPException(status_code=500, detail="Failed to send signal")


@app.post("/signals/scan")
async def scan_signals():
    """Scan TradingView for signals"""
    if not tv_controller or not tv_controller._is_connected:
        raise HTTPException(status_code=503, detail="TradingView not connected")
    
    signals = await tv_controller.scan_for_signals()
    
    # Send signals to Sapphire
    sent_count = 0
    for signal in signals:
        if signal.confidence > 0.7:  # Only high confidence signals
            success = await tv_controller.send_signal_to_sapphire(signal)
            if success:
                sent_count += 1
    
    return {
        "signals_found": len(signals),
        "signals_sent": sent_count,
        "signals": [s.to_sapphire_webhook() for s in signals]
    }


# Sapphire integration endpoints
@app.get("/sapphire/status")
async def get_sapphire_status():
    """Get Sapphire system status"""
    status = await sapphire_bridge.get_status()
    return status or {"status": "unknown"}


@app.post("/sapphire/heartbeat")
async def send_heartbeat():
    """Send heartbeat to Sapphire"""
    success = await sapphire_bridge.send_heartbeat()
    return {"success": success}


# WebSocket for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await manager.connect(websocket)
    
    try:
        # Send initial state
        if tv_controller and tv_controller._is_connected:
            state = await tv_controller.get_current_state()
            await websocket.send_json({
                "type": "tv_state",
                "data": {
                    "symbol": state.symbol,
                    "timeframe": state.timeframe,
                    "is_chart_loaded": state.is_chart_loaded
                }
            })
        
        # Listen for messages
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            
            elif message.get("type") == "get_state":
                if tv_controller and tv_controller._is_connected:
                    state = await tv_controller.get_current_state()
                    await websocket.send_json({
                        "type": "tv_state",
                        "data": {
                            "symbol": state.symbol,
                            "timeframe": state.timeframe,
                            "active_indicators": state.active_indicators,
                            "is_chart_loaded": state.is_chart_loaded
                        }
                    })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# Background task to broadcast TV state
async def broadcast_tv_state():
    """Broadcast TV state to all connected clients"""
    while True:
        try:
            if tv_controller and tv_controller._is_connected:
                state = await tv_controller.get_current_state()
                await manager.broadcast({
                    "type": "tv_state_update",
                    "data": {
                        "symbol": state.symbol,
                        "timeframe": state.timeframe,
                        "current_price": state.current_price,
                        "timestamp": state.timestamp.isoformat()
                    }
                })
            await asyncio.sleep(5)  # Update every 5 seconds
        except Exception as e:
            logger.error(f"Broadcast error: {e}")
            await asyncio.sleep(5)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
