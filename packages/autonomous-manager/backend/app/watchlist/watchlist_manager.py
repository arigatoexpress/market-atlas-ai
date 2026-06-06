"""
Watchlist Manager for TradingView
Handles watchlist operations and symbol management
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class SymbolInfo:
    """Symbol information"""
    symbol: str
    name: str = ""
    exchange: str = ""
    type: str = "crypto"  # crypto, forex, stock
    venue: str = ""  # ASTER, LIGHTER
    is_active: bool = True
    added_at: datetime = field(default_factory=datetime.now)
    notes: str = ""


@dataclass
class Watchlist:
    """TradingView watchlist"""
    id: str = ""
    name: str = ""
    symbols: List[str] = field(default_factory=list)
    symbol_info: Dict[str, SymbolInfo] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_default: bool = False
    is_synced: bool = False  # Synced with TradingView Desktop
    category: str = "custom"  # custom, crypto, forex, stocks
    description: str = ""
    
    def __post_init__(self):
        if not self.id:
            self.id = f"wl_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def add_symbol(self, symbol: str, **kwargs) -> bool:
        """Add symbol to watchlist"""
        if symbol not in self.symbols:
            self.symbols.append(symbol)
            self.symbol_info[symbol] = SymbolInfo(symbol=symbol, **kwargs)
            self.updated_at = datetime.now()
            self.is_synced = False
            return True
        return False
    
    def remove_symbol(self, symbol: str) -> bool:
        """Remove symbol from watchlist"""
        if symbol in self.symbols:
            self.symbols.remove(symbol)
            if symbol in self.symbol_info:
                del self.symbol_info[symbol]
            self.updated_at = datetime.now()
            self.is_synced = False
            return True
        return False
    
    def clear(self):
        """Clear all symbols"""
        self.symbols = []
        self.symbol_info = {}
        self.updated_at = datetime.now()
        self.is_synced = False
    
    def reorder(self, new_order: List[str]):
        """Reorder symbols"""
        self.symbols = [s for s in new_order if s in self.symbols]
        self.updated_at = datetime.now()
        self.is_synced = False
    
    def to_dict(self) -> Dict:
        return asdict(self)


class WatchlistManager:
    """Manages TradingView watchlists"""
    
    # Predefined symbol lists
    CRYPTO_PERPS = [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "DOGEUSDT",
        "XRPUSDT", "ADAUSDT", "DOTUSDT", "LINKUSDT", "MATICUSDT",
        "UNIUSDT", "LDOUSDT", "OPUSDT", "ARBUSDT", "SUIUSDT",
        "SEIUSDT", "TIAUSDT", "INJUSDT", "RNDRUSDT", "PYTHUSDT",
        "JUPUSDT", "WIFUSDT", "BONKUSDT", "PEPEUSDT", "SHIBUSDT"
    ]
    
    FOREX_MAJORS = [
        "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD",
        "USDCAD", "NZDUSD", "EURGBP", "EURJPY", "GBPJPY"
    ]
    
    ASTER_SYMBOLS = [
        "SOLUSDT", "JUPUSDT", "PYTHUSDT", "BONKUSDT", "WIFUSDT",
        "RNDRUSDT", "HNTUSDT", "SAMOUSDT"
    ]
    
    LIGHTER_SYMBOLS = [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "HYPEUSDT", "DOGEUSDT",
        "AVAXUSDT", "XRPUSDT", "ADAUSDT"
    ]
    
    def __init__(self, storage_path: str = "watchlists"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        self.watchlists: Dict[str, Watchlist] = {}
        self._load_watchlists()
        
        # Create default watchlists if none exist
        if not self.watchlists:
            self._create_defaults()
    
    def _load_watchlists(self):
        """Load watchlists from storage"""
        for file_path in self.storage_path.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    watchlist = Watchlist(**data)
                    # Convert datetime strings
                    if isinstance(watchlist.created_at, str):
                        watchlist.created_at = datetime.fromisoformat(watchlist.created_at)
                    if isinstance(watchlist.updated_at, str):
                        watchlist.updated_at = datetime.fromisoformat(watchlist.updated_at)
                    # Convert symbol_info
                    watchlist.symbol_info = {
                        k: SymbolInfo(**v) if isinstance(v, dict) else v
                        for k, v in watchlist.symbol_info.items()
                    }
                    self.watchlists[watchlist.id] = watchlist
            except Exception as e:
                logger.error(f"Error loading watchlist {file_path}: {e}")
        
        logger.info(f"Loaded {len(self.watchlists)} watchlists")
    
    def _save_watchlist(self, watchlist: Watchlist):
        """Save watchlist to disk"""
        file_path = self.storage_path / f"{watchlist.id}.json"
        with open(file_path, 'w') as f:
            json.dump(watchlist.to_dict(), f, indent=2, default=str)
    
    def _create_defaults(self):
        """Create default watchlists"""
        # Crypto Perps
        wl = self.create_watchlist(
            "Crypto Perps",
            category="crypto",
            description="Crypto perpetual futures for ASTER/LIGHTER"
        )
        for sym in self.CRYPTO_PERPS[:15]:
            venue = "ASTER" if sym in self.ASTER_SYMBOLS else "LIGHTER"
            wl.add_symbol(sym, type="crypto", venue=venue)
        self._save_watchlist(wl)
        
        # ASTER Focus
        wl = self.create_watchlist(
            "ASTER Focus",
            category="crypto",
            description="ASTER DEX primary symbols"
        )
        for sym in self.ASTER_SYMBOLS:
            wl.add_symbol(sym, type="crypto", venue="ASTER")
        self._save_watchlist(wl)
        
        # LIGHTER Focus
        wl = self.create_watchlist(
            "LIGHTER Focus",
            category="crypto",
            description="LIGHTER DEX primary symbols"
        )
        for sym in self.LIGHTER_SYMBOLS:
            wl.add_symbol(sym, type="crypto", venue="LIGHTER")
        self._save_watchlist(wl)
        
        # Forex Majors
        wl = self.create_watchlist(
            "Forex Majors",
            category="forex",
            description="Major forex pairs"
        )
        for sym in self.FOREX_MAJORS:
            wl.add_symbol(sym, type="forex", venue="")
        self._save_watchlist(wl)
    
    def create_watchlist(self, name: str, **kwargs) -> Watchlist:
        """Create a new watchlist"""
        watchlist = Watchlist(
            name=name,
            category=kwargs.get('category', 'custom'),
            description=kwargs.get('description', ''),
            is_default=kwargs.get('is_default', False)
        )
        
        self.watchlists[watchlist.id] = watchlist
        self._save_watchlist(watchlist)
        
        logger.info(f"Created watchlist: {name} ({watchlist.id})")
        return watchlist
    
    def get_watchlist(self, watchlist_id: str) -> Optional[Watchlist]:
        """Get watchlist by ID"""
        return self.watchlists.get(watchlist_id)
    
    def get_watchlist_by_name(self, name: str) -> Optional[Watchlist]:
        """Get watchlist by name"""
        for watchlist in self.watchlists.values():
            if watchlist.name.lower() == name.lower():
                return watchlist
        return None
    
    def list_watchlists(self, category: str = None) -> List[Watchlist]:
        """List all watchlists"""
        watchlists = list(self.watchlists.values())
        if category:
            watchlists = [w for w in watchlists if w.category == category]
        return sorted(watchlists, key=lambda w: w.updated_at, reverse=True)
    
    def update_watchlist(self, watchlist_id: str, **kwargs) -> Optional[Watchlist]:
        """Update watchlist"""
        watchlist = self.watchlists.get(watchlist_id)
        if not watchlist:
            return None
        
        for key, value in kwargs.items():
            if hasattr(watchlist, key) and key != 'id':
                setattr(watchlist, key, value)
        
        watchlist.updated_at = datetime.now()
        watchlist.is_synced = False
        self._save_watchlist(watchlist)
        return watchlist
    
    def delete_watchlist(self, watchlist_id: str) -> bool:
        """Delete watchlist"""
        if watchlist_id in self.watchlists:
            del self.watchlists[watchlist_id]
            file_path = self.storage_path / f"{watchlist_id}.json"
            if file_path.exists():
                file_path.unlink()
            return True
        return False
    
    def add_symbol(self, watchlist_id: str, symbol: str, **kwargs) -> bool:
        """Add symbol to watchlist"""
        watchlist = self.watchlists.get(watchlist_id)
        if watchlist:
            result = watchlist.add_symbol(symbol, **kwargs)
            if result:
                self._save_watchlist(watchlist)
            return result
        return False
    
    def remove_symbol(self, watchlist_id: str, symbol: str) -> bool:
        """Remove symbol from watchlist"""
        watchlist = self.watchlists.get(watchlist_id)
        if watchlist:
            result = watchlist.remove_symbol(symbol)
            if result:
                self._save_watchlist(watchlist)
            return result
        return False
    
    def clear_watchlist(self, watchlist_id: str) -> bool:
        """Clear all symbols from watchlist"""
        watchlist = self.watchlists.get(watchlist_id)
        if watchlist:
            watchlist.clear()
            self._save_watchlist(watchlist)
            return True
        return False
    
    def bulk_import_symbols(self, watchlist_id: str, symbols: List[str], **kwargs) -> int:
        """Bulk import symbols to watchlist"""
        watchlist = self.watchlists.get(watchlist_id)
        if not watchlist:
            return 0
        
        added = 0
        for symbol in symbols:
            if watchlist.add_symbol(symbol.strip(), **kwargs):
                added += 1
        
        if added > 0:
            self._save_watchlist(watchlist)
        
        return added
    
    def export_watchlist(self, watchlist_id: str, format: str = 'json') -> Optional[str]:
        """Export watchlist to string"""
        watchlist = self.watchlists.get(watchlist_id)
        if not watchlist:
            return None
        
        if format == 'json':
            return json.dumps(watchlist.to_dict(), indent=2, default=str)
        elif format == 'csv':
            return '\n'.join(['symbol,name,venue'] + [
                f"{s},{watchlist.symbol_info.get(s, SymbolInfo(s)).name},{watchlist.symbol_info.get(s, SymbolInfo(s)).venue}"
                for s in watchlist.symbols
            ])
        elif format == 'txt':
            return '\n'.join(watchlist.symbols)
        
        return None
    
    def import_from_text(self, name: str, text: str, **kwargs) -> Optional[Watchlist]:
        """Import watchlist from text (one symbol per line)"""
        symbols = [s.strip() for s in text.split('\n') if s.strip()]
        
        watchlist = self.create_watchlist(name, **kwargs)
        for sym in symbols:
            # Try to detect venue
            venue = ""
            if sym in self.ASTER_SYMBOLS:
                venue = "ASTER"
            elif sym in self.LIGHTER_SYMBOLS:
                venue = "LIGHTER"
            
            watchlist.add_symbol(sym, type="crypto", venue=venue)
        
        self._save_watchlist(watchlist)
        return watchlist
    
    def get_venue_symbols(self, venue: str) -> List[str]:
        """Get all symbols for a specific venue"""
        symbols = set()
        for watchlist in self.watchlists.values():
            for sym in watchlist.symbols:
                info = watchlist.symbol_info.get(sym, SymbolInfo(symbol=sym))
                if info.venue == venue:
                    symbols.add(sym)
        return sorted(list(symbols))
    
    def mark_synced(self, watchlist_id: str):
        """Mark watchlist as synced with TradingView"""
        watchlist = self.watchlists.get(watchlist_id)
        if watchlist:
            watchlist.is_synced = True
            self._save_watchlist(watchlist)


# Singleton
_manager: Optional[WatchlistManager] = None


def get_watchlist_manager(storage_path: str = "watchlists") -> WatchlistManager:
    """Get singleton watchlist manager"""
    global _manager
    if _manager is None:
        _manager = WatchlistManager(storage_path)
    return _manager
