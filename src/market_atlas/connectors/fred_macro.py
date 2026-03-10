from __future__ import annotations

from typing import Dict

import pandas as pd

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"

# Monthly/weekly macro set with monetary policy + cycles + liquidity proxies
DEFAULT_FRED_SERIES: Dict[str, str] = {
    "fed_funds": "FEDFUNDS",
    "ism_pmi": "NAPM",
    "cpi": "CPIAUCSL",
    "m2": "M2SL",
    "fed_balance_sheet": "WALCL",
    "oil_wti": "DCOILWTICO",
    "usd_index_broad": "DTWEXBGS",
    "yield_curve_10y_2y": "T10Y2Y",
    "yield_10y": "GS10",
    "yield_2y": "GS2",
    "unemployment": "UNRATE",
    "high_yield_spread": "BAMLH0A0HYM2",
}


def fetch_series(series_map: Dict[str, str], start_date: str) -> pd.DataFrame:
    frames = []
    for metric, series_id in series_map.items():
        url = FRED_CSV.format(series_id=series_id)
        try:
            df = pd.read_csv(url)
        except Exception:
            continue
        date_col = None
        if "DATE" in df.columns:
            date_col = "DATE"
        elif "observation_date" in df.columns:
            date_col = "observation_date"
        if date_col is None:
            continue
        value_candidates = [c for c in df.columns if c != date_col]
        if not value_candidates:
            continue
        value_col = value_candidates[0]
        if value_col == date_col:
            candidates = [c for c in df.columns if c != date_col]
            if not candidates:
                continue
            value_col = candidates[0]
        df = df.rename(columns={date_col: "ts", value_col: "value"})
        df["ts"] = pd.to_datetime(df["ts"], errors="coerce")
        df = df[df["ts"] >= pd.Timestamp(start_date)].copy()
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.dropna(subset=["ts", "value"])
        df["metric"] = metric
        df["source"] = f"fred:{series_id}"
        frames.append(df[["metric", "ts", "value", "source"]])

    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    out["ts"] = out["ts"].dt.date
    return out
