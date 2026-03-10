from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb


@dataclass
class PromotionThresholds:
    min_trades: int
    min_return_pct: float
    max_drawdown_pct: float
    min_win_rate_pct: float
    min_sharpe: float


def _parse_summary(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return {}
    return {}


def latest_backtest_summary(conn: duckdb.DuckDBPyConnection) -> dict | None:
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
        "summary": _parse_summary(row[5]),
    }


def evaluate_promotion_gate(payload: dict, thresholds: PromotionThresholds) -> dict:
    summary = payload.get("summary") or {}
    checks: list[dict] = []

    def check(name: str, ok: bool, value: float | int, threshold: float | int, op: str) -> None:
        checks.append(
            {
                "name": name,
                "pass": bool(ok),
                "value": value,
                "threshold": threshold,
                "operator": op,
            }
        )

    trades = float(summary.get("trades") or 0)
    total_return = float(summary.get("total_return_pct") or 0)
    max_drawdown = float(summary.get("max_drawdown_pct") or 0)
    win_rate = float(summary.get("win_rate_pct") or 0)
    sharpe = float(summary.get("sharpe_annualized") or 0)

    check("trades", trades >= thresholds.min_trades, trades, thresholds.min_trades, ">=")
    check("total_return_pct", total_return >= thresholds.min_return_pct, total_return, thresholds.min_return_pct, ">=")
    check(
        "max_drawdown_pct",
        max_drawdown >= thresholds.max_drawdown_pct,
        max_drawdown,
        thresholds.max_drawdown_pct,
        ">=",
    )
    check(
        "win_rate_pct",
        win_rate >= thresholds.min_win_rate_pct,
        win_rate,
        thresholds.min_win_rate_pct,
        ">=",
    )
    check(
        "sharpe_annualized",
        sharpe >= thresholds.min_sharpe,
        sharpe,
        thresholds.min_sharpe,
        ">=",
    )

    passed = all(c["pass"] for c in checks)
    failed_checks = [c for c in checks if not c["pass"]]

    return {
        "passed": passed,
        "checks": checks,
        "failed_checks": failed_checks,
        "run_id": payload.get("run_id"),
        "strategy": payload.get("strategy"),
        "window": {
            "start_date": payload.get("start_date"),
            "end_date": payload.get("end_date"),
        },
        "symbols": payload.get("symbols"),
    }


def write_gate_artifacts(gate: dict, output_json: str) -> dict:
    json_path = Path(output_json)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(gate, indent=2), encoding="utf-8")

    md_path = json_path.with_suffix(".md")
    lines = [
        "# Market Atlas Promotion Gate",
        "",
        f"- Status: `{'PASS' if gate.get('passed') else 'FAIL'}`",
        f"- Run ID: `{gate.get('run_id')}`",
        f"- Strategy: `{gate.get('strategy')}`",
        f"- Window: `{gate.get('window', {}).get('start_date')}` -> `{gate.get('window', {}).get('end_date')}`",
        f"- Symbols: `{gate.get('symbols')}`",
        "",
        "## Checks",
        "",
    ]
    for c in gate.get("checks", []):
        status = "PASS" if c.get("pass") else "FAIL"
        lines.append(
            f"- {status} `{c['name']}`: value `{c['value']}` {c['operator']} threshold `{c['threshold']}`"
        )

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {"json_path": str(json_path), "markdown_path": str(md_path)}
