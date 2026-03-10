from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd


def _safe_summary(summary_raw: Any) -> dict:
    if isinstance(summary_raw, dict):
        return summary_raw
    if isinstance(summary_raw, str):
        try:
            return json.loads(summary_raw)
        except json.JSONDecodeError:
            return {}
    return {}


def _latest_run(conn: duckdb.DuckDBPyConnection) -> dict | None:
    row = conn.execute(
        """
        SELECT run_id, strategy, start_date, end_date, symbols, summary
        FROM backtest_runs
        ORDER BY ended_at DESC
        LIMIT 1
        """
    ).fetchone()
    if not row:
        return None
    return {
        "run_id": row[0],
        "strategy": row[1],
        "start_date": str(row[2]),
        "end_date": str(row[3]),
        "symbols": row[4],
        "summary": _safe_summary(row[5]),
    }


def _fetch_regime_mix(conn: duckdb.DuckDBPyConnection, start_date: str, end_date: str) -> pd.DataFrame:
    return conn.execute(
        """
        SELECT regime, season, COUNT(*) AS points
        FROM regimes
        WHERE ts BETWEEN ? AND ?
        GROUP BY regime, season
        ORDER BY points DESC
        """,
        [start_date, end_date],
    ).fetchdf()


def _plot_equity_curve(curve: pd.DataFrame, out_path: Path) -> None:
    import matplotlib.pyplot as plt

    if curve.empty:
        return
    x = pd.to_datetime(curve["ts"])
    y = pd.to_numeric(curve["equity"], errors="coerce")

    plt.figure(figsize=(12, 5))
    plt.plot(x, y, linewidth=1.8)
    plt.title("Backtest Equity Curve")
    plt.xlabel("Date")
    plt.ylabel("Equity")
    plt.grid(alpha=0.2)
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()


def _plot_trade_distribution(trades: pd.DataFrame, out_path: Path) -> None:
    import matplotlib.pyplot as plt

    if trades.empty:
        return

    pnl = pd.to_numeric(trades["pnl_pct"], errors="coerce").dropna()
    if pnl.empty:
        return

    plt.figure(figsize=(10, 5))
    plt.hist(pnl, bins=30)
    plt.title("Trade PnL Distribution (%)")
    plt.xlabel("Trade PnL %")
    plt.ylabel("Count")
    plt.grid(alpha=0.2)
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()


def build_report(conn: duckdb.DuckDBPyConnection, run_id: str | None, output_dir: str) -> dict:
    run = None
    if run_id:
        row = conn.execute(
            """
            SELECT run_id, strategy, start_date, end_date, symbols, summary
            FROM backtest_runs
            WHERE run_id = ?
            LIMIT 1
            """,
            [run_id],
        ).fetchone()
        if row:
            run = {
                "run_id": row[0],
                "strategy": row[1],
                "start_date": str(row[2]),
                "end_date": str(row[3]),
                "symbols": row[4],
                "summary": _safe_summary(row[5]),
            }
    else:
        run = _latest_run(conn)

    if not run:
        raise ValueError("No backtest run found. Execute `market-atlas backtest` first.")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    trades = conn.execute(
        """
        SELECT ts, symbol, side, qty, entry, exit, pnl_pct, regime
        FROM backtest_trades
        WHERE run_id = ?
        ORDER BY ts
        """,
        [run["run_id"]],
    ).fetchdf()

    curve = conn.execute(
        """
        SELECT ts, SUM(equity) AS equity
        FROM (
            SELECT f.ts, f.symbol, f.close * COALESCE(t.qty, 0.0) AS equity
            FROM features f
            LEFT JOIN (
                SELECT symbol, qty, MIN(ts) AS ts
                FROM backtest_trades
                WHERE run_id = ?
                GROUP BY symbol, qty
            ) t ON t.symbol = f.symbol AND f.ts >= t.ts
            WHERE f.ts BETWEEN ? AND ?
        )
        GROUP BY ts
        ORDER BY ts
        """,
        [run["run_id"], run["start_date"], run["end_date"]],
    ).fetchdf()

    if curve.empty:
        # Fallback to a synthetic curve from trade sequence if price-joined curve has sparse coverage.
        start_equity = 100.0
        pts = [{"ts": run["start_date"], "equity": start_equity}]
        eq = start_equity
        for row in trades.itertuples(index=False):
            eq *= 1 + (float(row.pnl_pct) / 100.0)
            pts.append({"ts": row.ts, "equity": eq})
        curve = pd.DataFrame(pts)

    regime_mix = _fetch_regime_mix(conn, run["start_date"], run["end_date"])

    equity_png = out_dir / "equity_curve.png"
    trades_png = out_dir / "trade_pnl_distribution.png"
    _plot_equity_curve(curve, equity_png)
    _plot_trade_distribution(trades, trades_png)

    summary = run["summary"]
    report_path = out_dir / "report.md"
    report = [
        "# Market Atlas Backtest Report",
        "",
        f"- Run ID: `{run['run_id']}`",
        f"- Strategy: `{run['strategy']}`",
        f"- Window: `{run['start_date']}` to `{run['end_date']}`",
        f"- Symbols: `{run['symbols']}`",
        "",
        "## Performance Summary",
        "",
        f"- Total return %: `{summary.get('total_return_pct', 0.0):.2f}`",
        f"- Max drawdown %: `{summary.get('max_drawdown_pct', 0.0):.2f}`",
        f"- Win rate %: `{summary.get('win_rate_pct', 0.0):.2f}`",
        f"- Annualized Sharpe: `{summary.get('sharpe_annualized', 0.0):.2f}`",
        f"- Return 7d %: `{summary.get('return_7d_pct', 0.0):.2f}`",
        f"- Return 30d %: `{summary.get('return_30d_pct', 0.0):.2f}`",
        f"- Return 90d %: `{summary.get('return_90d_pct', 0.0):.2f}`",
        "",
        "## Regime Mix",
        "",
    ]
    if regime_mix.empty:
        report.append("- No regime rows available for this window.")
    else:
        for row in regime_mix.itertuples(index=False):
            report.append(f"- {row.regime} ({row.season}): {int(row.points)} points")

    report.extend(
        [
            "",
            "## Artifacts",
            "",
            f"- Equity curve: `{equity_png}`",
            f"- Trade PnL distribution: `{trades_png}`",
        ]
    )

    report_path.write_text("\n".join(report), encoding="utf-8")

    return {
        "run_id": run["run_id"],
        "report_path": str(report_path),
        "equity_curve_png": str(equity_png),
        "trade_distribution_png": str(trades_png),
        "trades": int(len(trades)),
    }
