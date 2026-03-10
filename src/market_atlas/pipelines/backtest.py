from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import List

import duckdb

from market_atlas.strategies import momentum_regime


def run_backtest(
    conn: duckdb.DuckDBPyConnection,
    strategy_name: str,
    symbols: List[str],
    start_date: str,
    end_date: str,
    fee_bps: float,
    slippage_bps: float,
    base_capital: float,
) -> dict:
    if strategy_name != "momentum_regime":
        raise ValueError(f"Unsupported strategy: {strategy_name}")

    features = conn.execute(
        """
        SELECT * FROM features
        WHERE ts BETWEEN ? AND ?
        ORDER BY ts
        """,
        [start_date, end_date],
    ).fetchdf()

    regimes = conn.execute(
        """
        SELECT ts, regime, color, confidence, rationale
        FROM regimes
        WHERE ts BETWEEN ? AND ?
        ORDER BY ts
        """,
        [start_date, end_date],
    ).fetchdf()

    result = momentum_regime.run(
        features=features,
        regimes=regimes,
        symbols=symbols,
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
        base_capital=base_capital,
    )

    run_id = str(uuid.uuid4())
    started = datetime.now(timezone.utc)
    ended = datetime.now(timezone.utc)

    conn.execute(
        """
        INSERT INTO backtest_runs (run_id, strategy, started_at, ended_at, start_date, end_date, symbols, summary)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            run_id,
            strategy_name,
            started,
            ended,
            start_date,
            end_date,
            ",".join(symbols),
            json.dumps(result.summary),
        ],
    )

    if not result.trades.empty:
        trades = result.trades.copy()
        trades["run_id"] = run_id
        trades["metadata"] = trades["metadata"].map(json.dumps)
        conn.register("tmp_trades", trades)
        conn.execute(
            """
            INSERT INTO backtest_trades (run_id, ts, symbol, side, qty, entry, exit, pnl_pct, regime, metadata)
            SELECT run_id, ts, symbol, side, qty, entry, exit, pnl_pct, regime, metadata
            FROM tmp_trades
            """
        )
        conn.unregister("tmp_trades")

    return {"run_id": run_id, **result.summary}
