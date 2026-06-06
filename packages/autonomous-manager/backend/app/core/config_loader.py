"""
Configuration Loader
Loads and manages application configuration
"""
import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TVConfig:
    """TradingView configuration"""
    headless: bool = False
    cdp_port: int = 9222
    viewport_width: int = 1920
    viewport_height: int = 1080
    timeout: int = 30000
    windows_path: str = r"C:\Users\%USERNAME%\AppData\Local\Programs\TradingView\TradingView.exe"


@dataclass
class SapphireConfig:
    """Sapphire integration configuration"""
    webhook_url: str = "http://100.87.225.89:8080/tradingview/webhook"
    api_url: str = "http://100.87.225.89:8080/api"
    webhook_secret: str = ""
    default_venue: str = "LIGHTER"


@dataclass
class AppConfig:
    """Application configuration"""
    name: str = "TradingView Autonomous Manager"
    version: str = "1.0.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8081
    log_level: str = "INFO"
    
    # Sub-configs
    tradingview: TVConfig = field(default_factory=TVConfig)
    sapphire: SapphireConfig = field(default_factory=SapphireConfig)


class ConfigLoader:
    """Loads configuration from files and environment variables"""
    
    def __init__(self, config_path: str = "../config/settings.yaml"):
        self.config_path = Path(config_path)
        self.config: AppConfig = AppConfig()
        
    def load(self) -> AppConfig:
        """Load configuration from all sources"""
        # Start with defaults
        self.config = AppConfig()
        
        # Load from YAML file if exists
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    data = yaml.safe_load(f)
                    if data:
                        self._update_from_dict(data)
                        logger.info(f"Loaded config from {self.config_path}")
            except Exception as e:
                logger.warning(f"Error loading config file: {e}")
        
        # Override with environment variables
        self._load_from_env()
        
        return self.config
    
    def _update_from_dict(self, data: Dict[str, Any]):
        """Update config from dictionary"""
        # App settings
        if 'app' in data:
            app_data = data['app']
            self.config.name = app_data.get('name', self.config.name)
            self.config.version = app_data.get('version', self.config.version)
            self.config.debug = app_data.get('debug', self.config.debug)
            self.config.host = app_data.get('host', self.config.host)
            self.config.port = app_data.get('port', self.config.port)
        
        # TradingView settings
        if 'tradingview' in data:
            tv_data = data['tradingview']
            self.config.tradingview.headless = tv_data.get('headless', self.config.tradingview.headless)
            self.config.tradingview.cdp_port = tv_data.get('cdp_port', self.config.tradingview.cdp_port)
            self.config.tradingview.viewport_width = tv_data.get('viewport_width', self.config.tradingview.viewport_width)
            self.config.tradingview.viewport_height = tv_data.get('viewport_height', self.config.tradingview.viewport_height)
            self.config.tradingview.timeout = tv_data.get('timeout', self.config.tradingview.timeout)
            self.config.tradingview.windows_path = tv_data.get('windows_path', self.config.tradingview.windows_path)
        
        # Sapphire settings
        if 'sapphire' in data:
            sap_data = data['sapphire']
            self.config.sapphire.webhook_url = sap_data.get('webhook_url', self.config.sapphire.webhook_url)
            self.config.sapphire.api_url = sap_data.get('api_url', self.config.sapphire.api_url)
            self.config.sapphire.webhook_secret = sap_data.get('webhook_secret', self.config.sapphire.webhook_secret)
            self.config.sapphire.default_venue = sap_data.get('default_venue', self.config.sapphire.default_venue)
    
    def _load_from_env(self):
        """Override config with environment variables"""
        # App
        if os.getenv('TV_DEBUG'):
            self.config.debug = os.getenv('TV_DEBUG', '').lower() == 'true'
        if os.getenv('TV_PORT'):
            self.config.port = int(os.getenv('TV_PORT'))
        if os.getenv('TV_LOG_LEVEL'):
            self.config.log_level = os.getenv('TV_LOG_LEVEL')
        
        # TradingView
        if os.getenv('TV_HEADLESS'):
            self.config.tradingview.headless = os.getenv('TV_HEADLESS', '').lower() == 'true'
        if os.getenv('TV_CDP_PORT'):
            self.config.tradingview.cdp_port = int(os.getenv('TV_CDP_PORT'))
        
        # Sapphire
        if os.getenv('SAPPHIRE_WEBHOOK_URL'):
            self.config.sapphire.webhook_url = os.getenv('SAPPHIRE_WEBHOOK_URL')
        if os.getenv('SAPPHIRE_WEBHOOK_SECRET'):
            self.config.sapphire.webhook_secret = os.getenv('SAPPHIRE_WEBHOOK_SECRET')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            'name': self.config.name,
            'version': self.config.version,
            'debug': self.config.debug,
            'host': self.config.host,
            'port': self.config.port,
            'log_level': self.config.log_level,
            'tradingview': {
                'headless': self.config.tradingview.headless,
                'cdp_port': self.config.tradingview.cdp_port,
                'viewport_width': self.config.tradingview.viewport_width,
                'viewport_height': self.config.tradingview.viewport_height,
                'timeout': self.config.tradingview.timeout,
                'windows_path': self.config.tradingview.windows_path,
            },
            'sapphire': {
                'webhook_url': self.config.sapphire.webhook_url,
                'api_url': self.config.sapphire.api_url,
                'webhook_secret': '***' if self.config.sapphire.webhook_secret else '',
                'default_venue': self.config.sapphire.default_venue,
            }
        }


# Global config instance
_config_loader: Optional[ConfigLoader] = None

def get_config(config_path: str = "../config/settings.yaml") -> AppConfig:
    """Get singleton config instance"""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader(config_path)
        _config_loader.load()
    return _config_loader.config


def reload_config(config_path: str = "../config/settings.yaml") -> AppConfig:
    """Reload configuration"""
    global _config_loader
    _config_loader = ConfigLoader(config_path)
    return _config_loader.load()
