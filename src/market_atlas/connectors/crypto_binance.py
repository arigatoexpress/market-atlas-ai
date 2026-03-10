from __future__ import annotations

from datetime import datetime
from typing import Dict, List

import pandas as pd
import requests
import yfinance as yf

BINANCE_KLINES = "https://api.binance.com/api/v3/klines"
YAHOO_CRYPTO_SUFFIX = "-USD"
DEFAULT_TIMEOUT = 20


def _to_yahoo_symbol(symbol: str) -> str:
    base = symbol.upper()
    if base.endswith("USDT"):
        base = base[:-4]
    return f"{base}{YAHOO_CRYPTO_SUFFIX}"


def _fetch_from_yahoo(symbol: str, start_date: str) -> pd.DataFrame:
    yahoo_symbol = _to_yahoo_symbol(symbol)
    data = yf.download(yahoo_symbol, start=start_date, interval="1d", auto_adjust=False, progress=False)
    if data.empty:
        return pd.DataFrame()
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [c[0] for c in data.columns]

    data = data.reset_index().rename(
        columns={
            "Date": "ts",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }
    )
    data["asset_class"] = "crypto"
    data["symbol"] = symbol
    data["timeframe"] = "1d"
    data["source"] = "yahoo_finance"

    cols = ["asset_class", "symbol", "timeframe", "ts", "open", "high", "low", "close", "volume", "source"]
    return data[cols]


def fetch_daily_bars(symbol: str, start_date: str) -> pd.DataFrame:
    start_ms = int(pd.Timestamp(start_date, tz="UTC").timestamp() * 1000)
    rows: List[Dict] = []
    next_start = start_ms

    while True:
        params = {
            "symbol": symbol,
            "interval": "1d",
            "startTime": next_start,
            "limit": 1000,
        }
        try:
            resp = requests.get(BINANCE_KLINES, params=params, timeout=DEFAULT_TIMEOUT)
            resp.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            if status_code == 451:
                return _fetch_from_yahoo(symbol, start_date)
            raise
        except requests.exceptions.RequestException:
            return _fetch_from_yahoo(symbol, start_date)
        payload = resp.json()
        if not payload:
            break

        for item in payload:
            rows.append(
                {
                    "asset_class": "crypto",
                    "symbol": symbol,
                    "timeframe": "1d",
                    "ts": datetime.utcfromtimestamp(item[0] / 1000),
                    "open": float(item[1]),
                    "high": float(item[2]),
                    "low": float(item[3]),
                    "close": float(item[4]),
                    "volume": float(item[5]),
                    "source": "binance",
                }
            )

        last_open = payload[-1][0]
        if len(payload) < 1000:
            break
        next_start = last_open + 86_400_000

    return pd.DataFrame(rows)
