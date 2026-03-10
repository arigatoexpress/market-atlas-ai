from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List


def _csv_env(name: str, default: str) -> List[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass
class AppConfig:
    db_path: Path
    timeframe: str
    default_start_date: str
    crypto_symbols: List[str]
    equity_symbols: List[str]
    news_query: str
    github_token: str
    fee_bps: float
    slippage_bps: float
    base_capital: float
    sapphire_gateway_url: str
    sapphire_gateway_api_token: str
    promotion_min_trades: int
    promotion_min_return_pct: float
    promotion_max_drawdown_pct: float
    promotion_min_win_rate_pct: float
    promotion_min_sharpe: float

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            db_path=Path(os.getenv("MARKET_ATLAS_DB_PATH", "data/market_atlas.duckdb")),
            timeframe=os.getenv("MARKET_ATLAS_TIMEFRAME", "1d"),
            default_start_date=os.getenv("MARKET_ATLAS_DEFAULT_START_DATE", "2024-01-01"),
            crypto_symbols=_csv_env("MARKET_ATLAS_CRYPTO_SYMBOLS", "BTCUSDT,ETHUSDT,SOLUSDT"),
            equity_symbols=_csv_env("MARKET_ATLAS_EQUITY_SYMBOLS", "SPY,QQQ,TLT,DX-Y.NYB,GLD,SLV,CL=F"),
            news_query=os.getenv(
                "MARKET_ATLAS_NEWS_QUERY",
                "(crypto OR equities OR macro OR fed OR oil OR liquidity)",
            ),
            github_token=os.getenv("GITHUB_TOKEN", "").strip(),
            fee_bps=float(os.getenv("MARKET_ATLAS_FEE_BPS", "6.0")),
            slippage_bps=float(os.getenv("MARKET_ATLAS_SLIPPAGE_BPS", "5.0")),
            base_capital=float(os.getenv("MARKET_ATLAS_BASE_CAPITAL", "10000")),
            sapphire_gateway_url=os.getenv("SAPPHIRE_GATEWAY_URL", "http://127.0.0.1:18080").strip(),
            sapphire_gateway_api_token=os.getenv("SAPPHIRE_GATEWAY_API_TOKEN", "").strip(),
            promotion_min_trades=int(os.getenv("MARKET_ATLAS_PROMOTION_MIN_TRADES", "60")),
            promotion_min_return_pct=float(os.getenv("MARKET_ATLAS_PROMOTION_MIN_RETURN_PCT", "20")),
            promotion_max_drawdown_pct=float(os.getenv("MARKET_ATLAS_PROMOTION_MAX_DRAWDOWN_PCT", "-35")),
            promotion_min_win_rate_pct=float(os.getenv("MARKET_ATLAS_PROMOTION_MIN_WIN_RATE_PCT", "45")),
            promotion_min_sharpe=float(os.getenv("MARKET_ATLAS_PROMOTION_MIN_SHARPE", "1.2")),
        )
