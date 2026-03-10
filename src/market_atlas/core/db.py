from __future__ import annotations

import duckdb


def connect(db_path: str) -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect(db_path)
    conn.execute("PRAGMA threads=4;")
    return conn


def init_db(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS bars (
            asset_class VARCHAR,
            symbol VARCHAR,
            timeframe VARCHAR,
            ts TIMESTAMP,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            volume DOUBLE,
            source VARCHAR,
            ingested_at TIMESTAMP DEFAULT NOW()
        );
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS macro_series (
            metric VARCHAR,
            ts DATE,
            value DOUBLE,
            source VARCHAR,
            ingested_at TIMESTAMP DEFAULT NOW()
        );
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS news_events (
            ts TIMESTAMP,
            source VARCHAR,
            title VARCHAR,
            url VARCHAR,
            sentiment_hint VARCHAR,
            payload JSON,
            ingested_at TIMESTAMP DEFAULT NOW()
        );
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS oss_events (
            ts TIMESTAMP,
            source VARCHAR,
            topic VARCHAR,
            score DOUBLE,
            payload JSON,
            ingested_at TIMESTAMP DEFAULT NOW()
        );
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS betting_markets (
            ts TIMESTAMP,
            source VARCHAR,
            market_id VARCHAR,
            question VARCHAR,
            probability DOUBLE,
            volume DOUBLE,
            payload JSON,
            ingested_at TIMESTAMP DEFAULT NOW()
        );
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS features (
            ts DATE,
            symbol VARCHAR,
            close DOUBLE,
            ret_1d DOUBLE,
            ret_5d DOUBLE,
            vol_20d DOUBLE,
            ma_20 DOUBLE,
            ma_50 DOUBLE,
            ma_200 DOUBLE,
            trend_50_200 DOUBLE,
            atr_14 DOUBLE,
            rsi_14 DOUBLE,
            breakout_20 DOUBLE,
            source VARCHAR,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """
    )
    conn.execute("ALTER TABLE features ADD COLUMN IF NOT EXISTS close DOUBLE;")
    conn.execute("ALTER TABLE features ADD COLUMN IF NOT EXISTS atr_14 DOUBLE;")
    conn.execute("ALTER TABLE features ADD COLUMN IF NOT EXISTS rsi_14 DOUBLE;")
    conn.execute("ALTER TABLE features ADD COLUMN IF NOT EXISTS breakout_20 DOUBLE;")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS regimes (
            ts DATE,
            regime VARCHAR,
            season VARCHAR,
            color VARCHAR,
            confidence DOUBLE,
            growth DOUBLE,
            inflation DOUBLE,
            liquidity DOUBLE,
            policy_rate DOUBLE,
            policy_stance VARCHAR,
            business_cycle_phase VARCHAR,
            rationale VARCHAR,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """
    )
    conn.execute("ALTER TABLE regimes ADD COLUMN IF NOT EXISTS season VARCHAR;")
    conn.execute("ALTER TABLE regimes ADD COLUMN IF NOT EXISTS growth DOUBLE;")
    conn.execute("ALTER TABLE regimes ADD COLUMN IF NOT EXISTS inflation DOUBLE;")
    conn.execute("ALTER TABLE regimes ADD COLUMN IF NOT EXISTS liquidity DOUBLE;")
    conn.execute("ALTER TABLE regimes ADD COLUMN IF NOT EXISTS policy_rate DOUBLE;")
    conn.execute("ALTER TABLE regimes ADD COLUMN IF NOT EXISTS policy_stance VARCHAR;")
    conn.execute("ALTER TABLE regimes ADD COLUMN IF NOT EXISTS business_cycle_phase VARCHAR;")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS backtest_runs (
            run_id VARCHAR,
            strategy VARCHAR,
            started_at TIMESTAMP,
            ended_at TIMESTAMP,
            start_date DATE,
            end_date DATE,
            symbols VARCHAR,
            summary JSON
        );
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS backtest_trades (
            run_id VARCHAR,
            ts DATE,
            symbol VARCHAR,
            side VARCHAR,
            qty DOUBLE,
            entry DOUBLE,
            exit DOUBLE,
            pnl_pct DOUBLE,
            regime VARCHAR,
            metadata JSON
        );
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS exported_signals (
            exported_at TIMESTAMP DEFAULT NOW(),
            payload JSON
        );
        """
    )


def reset_db(conn: duckdb.DuckDBPyConnection) -> None:
    tables = [
        "exported_signals",
        "backtest_trades",
        "backtest_runs",
        "regimes",
        "features",
        "betting_markets",
        "oss_events",
        "news_events",
        "macro_series",
        "bars",
    ]
    for table in tables:
        conn.execute(f"DROP TABLE IF EXISTS {table}")
