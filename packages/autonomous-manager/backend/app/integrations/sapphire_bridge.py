"""
Sapphire Bridge
Integrates TradingView Desktop Manager with Sapphire Trading System
"""

import json
import logging
import aiohttp
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class SapphireConfig:
    """Sapphire configuration"""
    webhook_url: str = "http://100.87.225.89:8080/tradingview/webhook"  # rari2
    api_url: str = "http://100.87.225.89:8080/api"
    webhook_secret: str = ""
    
    # Venue configuration
    default_venue: str = "LIGHTER"
    venue_mapping: Dict[str, str] = None
    
    def __post_init__(self):
        if self.venue_mapping is None:
            self.venue_mapping = {
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


class SapphireBridge:
    """Bridge between TradingView and Sapphire"""
    
    def __init__(self, config: SapphireConfig = None):
        self.config = config or SapphireConfig()
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={'Content-Type': 'application/json'}
            )
        return self.session
    
    def get_venue_for_symbol(self, symbol: str) -> str:
        """Determine venue based on symbol"""
        # Extract base symbol (remove USDT, USD, PERP)
        base = symbol.replace('USDT', '').replace('USD', '').replace('PERP', '')
        return self.config.venue_mapping.get(base, self.config.default_venue)
    
    async def send_signal(self, signal: Dict[str, Any]) -> bool:
        """Send trading signal to Sapphire"""
        try:
            # Format signal for Sapphire
            payload = {
                'action': signal.get('action', signal.get('direction', 'buy').lower()),
                'symbol': signal.get('symbol'),
                'venue': signal.get('venue', self.get_venue_for_symbol(signal.get('symbol', ''))),
                'quantity': signal.get('quantity', 0),
                'price': signal.get('entry_price', 0),
                'stop_loss': signal.get('stop_loss', 0),
                'take_profit': signal.get('take_profit', 0),
                'strategy': signal.get('strategy', 'tv_strategy'),
                'timeframe': signal.get('timeframe', '1h'),
                'confidence': signal.get('confidence', 0.8),
                'source': 'tradingview',
                'timestamp': datetime.now().isoformat(),
                'secret': self.config.webhook_secret
            }
            
            session = await self._get_session()
            async with session.post(
                self.config.webhook_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    logger.info(f"Signal sent to Sapphire: {payload['symbol']} {payload['action']}")
                    return True
                else:
                    text = await response.text()
                    logger.error(f"Sapphire webhook error: {response.status} - {text}")
                    return False
        
        except Exception as e:
            logger.error(f"Error sending signal to Sapphire: {e}")
            return False
    
    async def send_heartbeat(self) -> bool:
        """Send heartbeat to Sapphire"""
        try:
            payload = {
                'action': 'heartbeat',
                'source': 'tradingview',
                'strategy': 'tv-health-check',
                'secret': self.config.webhook_secret
            }
            
            session = await self._get_session()
            async with session.post(
                self.config.webhook_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                return response.status == 200
        
        except Exception as e:
            logger.error(f"Error sending heartbeat: {e}")
            return False
    
    async def get_status(self) -> Optional[Dict]:
        """Get Sapphire system status"""
        try:
            payload = {
                'action': 'status',
                'source': 'tradingview',
                'strategy': 'tv-status',
                'secret': self.config.webhook_secret
            }
            
            session = await self._get_session()
            async with session.post(
                self.config.webhook_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    return await response.json()
                return None
        
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return None
    
    async def watchlist_add(self, symbol: str, watchlist: str = "SAPPHIRE") -> bool:
        """Add symbol to Sapphire watchlist"""
        try:
            payload = {
                'action': 'tv_watchlist_add',
                'watchlist': watchlist,
                'symbol': symbol,
                'strategy': 'tv-watchlist-manager',
                'secret': self.config.webhook_secret
            }
            
            session = await self._get_session()
            async with session.post(
                self.config.webhook_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                return response.status == 200
        
        except Exception as e:
            logger.error(f"Error adding to watchlist: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """Test connection to Sapphire"""
        return await self.send_heartbeat()
    
    async def close(self):
        """Close HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()


# Singleton
_bridge: Optional[SapphireBridge] = None


def get_sapphire_bridge(config: SapphireConfig = None) -> SapphireBridge:
    """Get singleton Sapphire bridge"""
    global _bridge
    if _bridge is None:
        _bridge = SapphireBridge(config)
    return _bridge
