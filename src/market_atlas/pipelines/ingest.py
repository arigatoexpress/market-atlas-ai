from __future__ import annotations

import logging
from typing import Iterable

import duckdb
import pandas as pd

from market_atlas.config import AppConfig
from market_atlas.connectors.crypto_binance import fetch_daily_bars as fetch_crypto
from market_atlas.connectors.equities_yahoo import fetch_daily_bars as fetch_equities
from market_atlas.connectors.fred_macro import DEFAULT_FRED_SERIES, fetch_series
from market_atlas.connectors.gdelt_news import fetch_news
from market_atlas.connectors.github_intel import fetch_open_source_intel
from market_atlas.connectors.polymarket import fetch_prediction_markets

logger = logging.getLogger(__name__)

TABLE_KEYS = {
    "bars": ["asset_class", "symbol", "timeframe", "ts", "source"],
    "macro_series": ["metric", "ts", "source"],
    "news_events": ["url", "ts"],
    "oss_events": ["topic", "ts"],
    "betting_markets": ["market_id", "ts"],
}


def _safe_fetch(fetcher, *args, **kwargs) -> pd.DataFrame:
    try:
        df = fetcher(*args, **kwargs)
    except Exception as exc:
        logger.warning("ingest fetch failed for %s: %s", getattr(fetcher, "__name__", "fetcher"), exc)
        return pd.DataFrame()
    return df if isinstance(df, pd.DataFrame) else pd.DataFrame()


def _insert_df(conn: duckdb.DuckDBPyConnection, table: str, df) -> int:
    if df is None or df.empty:
        return 0
    columns = []
    for col in df.columns:
        if isinstance(col, tuple):
            columns.append(str(col[0]))
        else:
            columns.append(str(col))
    normalized = df.copy()
    normalized.columns = columns

    before_count = int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    conn.register("tmp_df", normalized)
    col_list = ", ".join(columns)
    source_cols = ", ".join([f"s.{c}" for c in columns])
    key_cols = TABLE_KEYS.get(table, [])

    if key_cols:
        join_cond = " AND ".join([f"s.{c} = t.{c}" for c in key_cols])
        null_cond = " AND ".join([f"t.{c} IS NULL" for c in key_cols])
        conn.execute(
            f"""
            INSERT INTO {table} ({col_list})
            SELECT {source_cols}
            FROM tmp_df s
            LEFT JOIN {table} t
              ON {join_cond}
            WHERE {null_cond}
            """
        )
    else:
        conn.execute(f"INSERT INTO {table} ({col_list}) SELECT {source_cols} FROM tmp_df s")

    conn.unregister("tmp_df")
    after_count = int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    return max(0, after_count - before_count)


def ingest_all(conn: duckdb.DuckDBPyConnection, cfg: AppConfig, start_date: str) -> dict:
    stats = {}

    crypto_total = 0
    for symbol in cfg.crypto_symbols:
        df = _safe_fetch(fetch_crypto, symbol, start_date)
        crypto_total += _insert_df(conn, "bars", df)
    stats["crypto_bars"] = crypto_total

    eq_df = _safe_fetch(fetch_equities, cfg.equity_symbols, start_date)
    stats["equity_commodity_bars"] = _insert_df(conn, "bars", eq_df)

    macro_df = _safe_fetch(fetch_series, DEFAULT_FRED_SERIES, start_date)
    stats["macro_points"] = _insert_df(conn, "macro_series", macro_df)

    news_df = _safe_fetch(fetch_news, cfg.news_query)
    stats["news_events"] = _insert_df(conn, "news_events", news_df)

    oss_df = _safe_fetch(fetch_open_source_intel, cfg.github_token)
    stats["oss_events"] = _insert_df(conn, "oss_events", oss_df)

    betting_df = _safe_fetch(fetch_prediction_markets)
    stats["prediction_markets"] = _insert_df(conn, "betting_markets", betting_df)

    return stats


def ingest_domains(conn: duckdb.DuckDBPyConnection, cfg: AppConfig, start_date: str, domains: Iterable[str]) -> dict:
    selected = set([d.strip().lower() for d in domains])
    stats = {}

    if "crypto" in selected:
        total = 0
        for symbol in cfg.crypto_symbols:
            total += _insert_df(conn, "bars", _safe_fetch(fetch_crypto, symbol, start_date))
        stats["crypto_bars"] = total

    if "equities" in selected or "commodities" in selected:
        stats["equity_commodity_bars"] = _insert_df(
            conn,
            "bars",
            _safe_fetch(fetch_equities, cfg.equity_symbols, start_date),
        )

    if "macro" in selected:
        stats["macro_points"] = _insert_df(
            conn,
            "macro_series",
            _safe_fetch(fetch_series, DEFAULT_FRED_SERIES, start_date),
        )

    if "news" in selected:
        stats["news_events"] = _insert_df(conn, "news_events", _safe_fetch(fetch_news, cfg.news_query))

    if "oss" in selected:
        stats["oss_events"] = _insert_df(
            conn,
            "oss_events",
            _safe_fetch(fetch_open_source_intel, cfg.github_token),
        )

    if "betting" in selected:
        stats["prediction_markets"] = _insert_df(
            conn,
            "betting_markets",
            _safe_fetch(fetch_prediction_markets),
        )

    return stats
