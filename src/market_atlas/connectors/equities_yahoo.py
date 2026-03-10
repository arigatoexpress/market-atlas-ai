from __future__ import annotations

from typing import List

import pandas as pd
import yfinance as yf


def fetch_daily_bars(symbols: List[str], start_date: str) -> pd.DataFrame:
    frames = []
    for symbol in symbols:
        data = yf.download(symbol, start=start_date, interval="1d", auto_adjust=False, progress=False)
        if data.empty:
            continue
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = [c[0] for c in data.columns]
        data = data.reset_index()
        data["asset_class"] = "equity" if "=" not in symbol else "commodity"
        data["symbol"] = symbol
        data["timeframe"] = "1d"
        data["source"] = "yahoo_finance"
        frames.append(
            data.rename(
                columns={
                    "Date": "ts",
                    "Open": "open",
                    "High": "high",
                    "Low": "low",
                    "Close": "close",
                    "Volume": "volume",
                }
            )[
                ["asset_class", "symbol", "timeframe", "ts", "open", "high", "low", "close", "volume", "source"]
            ]
        )

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)
