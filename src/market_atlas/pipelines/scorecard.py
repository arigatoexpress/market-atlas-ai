from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import duckdb
import requests

from market_atlas.exports.sapphire_signal import build_signals
from market_atlas.pipelines.promotion import (
    PromotionThresholds,
    evaluate_promotion_gate,
    latest_backtest_summary,
)


@dataclass
class ScorecardThresholds:
    max_drawdown_pct: float = -35.0
    min_fill_rate_pct: float = 70.0
    max_reject_tax_pct: float = 25.0
    max_ev_error_pct: float = 5.0


def _as_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_ts(value: str) -> Optional[datetime]:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def fetch_bot_status(status_url: str, timeout_seconds: float = 8.0) -> Dict[str, Any]:
    try:
        resp = requests.get(status_url, timeout=timeout_seconds)
        resp.raise_for_status()
        if "application/json" not in resp.headers.get("Content-Type", ""):
            return {}
        return resp.json()
    except Exception:
        return {}


def latest_symbol_trade_stats(
    conn: duckdb.DuckDBPyConnection, run_id: str, symbol: str
) -> Dict[str, Optional[float]]:
    row = conn.execute(
        """
        SELECT
            COUNT(*)::DOUBLE AS trades,
            AVG(pnl_pct) AS avg_trade_pnl_pct,
            SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END)::DOUBLE
                / NULLIF(COUNT(*), 0)::DOUBLE * 100.0 AS win_rate_pct
        FROM backtest_trades
        WHERE run_id = ? AND UPPER(symbol) = UPPER(?)
        """,
        [run_id, symbol],
    ).fetchone()
    if not row:
        return {"trades": 0.0, "avg_trade_pnl_pct": None, "win_rate_pct": None}
    return {
        "trades": _as_float(row[0]) or 0.0,
        "avg_trade_pnl_pct": _as_float(row[1]),
        "win_rate_pct": _as_float(row[2]),
    }


def signal_expectation_snapshot(conn: duckdb.DuckDBPyConnection, symbol: str) -> Dict[str, Any]:
    signals = build_signals(conn, [symbol])
    if not signals:
        return {}

    signal = signals[0]
    action = str(signal.get("action", "")).upper()
    entry = _as_float(signal.get("entry_price"))
    take_profit = _as_float(signal.get("take_profit"))
    stop_loss = _as_float(signal.get("stop_loss"))
    confidence = _as_float(signal.get("confidence")) or 0.0
    edge = _as_float(signal.get("edge"))

    tp_pct = None
    sl_pct = None
    expected_ev_pct = None
    if entry and entry > 0 and take_profit is not None and stop_loss is not None:
        tp_pct = abs(take_profit - entry) / entry * 100.0
        sl_pct = abs(entry - stop_loss) / entry * 100.0
        expected_ev_pct = confidence * tp_pct - (1.0 - confidence) * sl_pct

    return {
        "symbol": symbol.upper(),
        "action": action,
        "entry_price": entry,
        "take_profit": take_profit,
        "stop_loss": stop_loss,
        "confidence": confidence,
        "edge_pct": edge * 100.0 if edge is not None else None,
        "tp_pct": tp_pct,
        "sl_pct": sl_pct,
        "expected_ev_pct": expected_ev_pct,
    }


def compute_metric_deltas(
    current_kpis: Dict[str, Optional[float]],
    history: Iterable[Dict[str, Any]],
    now_utc: datetime,
    windows_hours: Iterable[int] = (1, 6, 24),
) -> Dict[str, Dict[str, Optional[float]]]:
    metric_keys = [
        "net_pnl_after_fees_pct",
        "max_drawdown_pct",
        "fill_rate_pct",
        "reject_tax_pct",
        "expected_value_error_pct",
    ]
    snapshots: List[tuple[datetime, Dict[str, Any]]] = []
    for item in history:
        ts = _parse_ts(str(item.get("ts", "")))
        if ts is None:
            continue
        snapshots.append((ts, item))
    snapshots.sort(key=lambda x: x[0])

    deltas: Dict[str, Dict[str, Optional[float]]] = {}
    for key in metric_keys:
        current = _as_float(current_kpis.get(key))
        metric_delta: Dict[str, Optional[float]] = {}
        for hours in windows_hours:
            label = f"delta_{hours}h"
            baseline: Optional[float] = None
            target = now_utc - timedelta(hours=hours)
            for ts, item in reversed(snapshots):
                if ts <= target:
                    baseline = _as_float((item.get("kpis") or {}).get(key))
                    break
            metric_delta[label] = (
                round(current - baseline, 4) if current is not None and baseline is not None else None
            )
        deltas[key] = metric_delta
    return deltas


def derive_go_no_go(
    kpis: Dict[str, Optional[float]],
    thresholds: ScorecardThresholds,
    promotion_gate: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    blockers: List[Dict[str, str]] = []

    max_drawdown = _as_float(kpis.get("max_drawdown_pct"))
    if max_drawdown is not None and max_drawdown < thresholds.max_drawdown_pct:
        blockers.append(
            {
                "code": "drawdown_limit",
                "message": (
                    f"Max drawdown {max_drawdown:.2f}% breached threshold "
                    f"{thresholds.max_drawdown_pct:.2f}%"
                ),
            }
        )

    fill_rate = _as_float(kpis.get("fill_rate_pct"))
    signals_received = _as_float(kpis.get("signals_received")) or 0.0
    if signals_received > 0 and fill_rate is not None and fill_rate < thresholds.min_fill_rate_pct:
        blockers.append(
            {
                "code": "fill_rate_low",
                "message": (
                    f"Fill rate {fill_rate:.2f}% below threshold "
                    f"{thresholds.min_fill_rate_pct:.2f}%"
                ),
            }
        )

    reject_tax = _as_float(kpis.get("reject_tax_pct"))
    if reject_tax is not None and reject_tax > thresholds.max_reject_tax_pct:
        blockers.append(
            {
                "code": "reject_tax_high",
                "message": (
                    f"Reject tax {reject_tax:.2f}% above threshold "
                    f"{thresholds.max_reject_tax_pct:.2f}%"
                ),
            }
        )

    ev_error = _as_float(kpis.get("expected_value_error_pct"))
    if ev_error is not None and abs(ev_error) > thresholds.max_ev_error_pct:
        blockers.append(
            {
                "code": "ev_error_high",
                "message": (
                    f"EV error {ev_error:.2f}pp above threshold "
                    f"{thresholds.max_ev_error_pct:.2f}pp"
                ),
            }
        )

    failed_trades = _as_float(kpis.get("trades_failed")) or 0.0
    if failed_trades > 0:
        blockers.append(
            {
                "code": "trade_failures_present",
                "message": f"Execution failures observed ({int(failed_trades)})",
            }
        )

    if promotion_gate and not promotion_gate.get("passed", False):
        failed_checks = promotion_gate.get("failed_checks") or []
        failed_names = [str(c.get("name")) for c in failed_checks if c.get("name")]
        gate_msg = ", ".join(failed_names) if failed_names else "promotion threshold checks failed"
        blockers.append(
            {
                "code": "promotion_gate_fail",
                "message": f"Promotion gate failed: {gate_msg}",
            }
        )

    action_map = {
        "drawdown_limit": "Keep lane in paper mode and tighten stop-loss envelope before promotion.",
        "fill_rate_low": "Inspect venue connectivity/reject reasons before raising notional.",
        "reject_tax_high": "Reduce symbol scope and align publisher symbols to locked execution symbol.",
        "ev_error_high": "Recalibrate signal confidence and TP/SL model against realized outcomes.",
        "trade_failures_present": "Stabilize order routing and retries before any scale-up.",
        "promotion_gate_fail": "Keep lane in paper mode and improve return/risk metrics before promotion.",
    }
    if blockers:
        top_actions = [action_map[b["code"]] for b in blockers[:3]]
        decision = "NO_GO"
    else:
        top_actions = [
            "Maintain SOL-only lane and continue hourly scorecard monitoring.",
            "If stable for 24h, increase notional cap one step and re-check reject-tax.",
            "Keep promotion gate closed until drawdown and EV error stay within thresholds.",
        ]
        decision = "GO"

    return {"decision": decision, "blockers": blockers, "top_actions": top_actions}


def _load_history(history_path: Path) -> List[Dict[str, Any]]:
    if not history_path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    for line in history_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _write_markdown(scorecard: Dict[str, Any], md_path: Path) -> None:
    kpis = scorecard.get("kpis", {})
    decision = scorecard.get("decision", {})
    lines = [
        "# SOL Hourly Scorecard",
        "",
        f"- Timestamp: `{scorecard.get('ts')}`",
        f"- Decision: `{decision.get('decision', 'NO_GO')}`",
        "",
        "## KPI Snapshot",
        "",
        f"- net_pnl_after_fees_pct: `{kpis.get('net_pnl_after_fees_pct')}`",
        f"- max_drawdown_pct: `{kpis.get('max_drawdown_pct')}`",
        f"- fill_rate_pct: `{kpis.get('fill_rate_pct')}`",
        f"- reject_tax_pct: `{kpis.get('reject_tax_pct')}`",
        f"- expected_value_error_pct: `{kpis.get('expected_value_error_pct')}`",
        "",
        "## Hard Blockers",
        "",
    ]
    blockers = decision.get("blockers") or []
    if blockers:
        for blocker in blockers:
            lines.append(f"- `{blocker.get('code')}`: {blocker.get('message')}")
    else:
        lines.append("- none")

    lines.extend(["", "## Top Actions", ""])
    for action in decision.get("top_actions") or []:
        lines.append(f"- {action}")

    md_path.write_text("\n".join(lines), encoding="utf-8")


def build_sol_scorecard(
    conn: duckdb.DuckDBPyConnection,
    symbol: str,
    bot_status_url: str,
    output_path: str,
    history_path: str,
    thresholds: ScorecardThresholds,
    append_history: bool = True,
) -> Dict[str, Any]:
    payload = latest_backtest_summary(conn)
    if not payload:
        raise ValueError("No backtest run found. Run `market-atlas backtest` first.")

    run_id = str(payload.get("run_id"))
    summary = payload.get("summary") or {}
    promotion_gate = evaluate_promotion_gate(
        payload,
        thresholds=PromotionThresholds(
            min_trades=60,
            min_return_pct=20.0,
            max_drawdown_pct=-35.0,
            min_win_rate_pct=45.0,
            min_sharpe=1.2,
        ),
    )
    trade_stats = latest_symbol_trade_stats(conn, run_id=run_id, symbol=symbol)
    expectation = signal_expectation_snapshot(conn, symbol=symbol)
    bot_status = fetch_bot_status(bot_status_url)
    reject_tax = bot_status.get("reject_tax") or {}

    signals_received = _as_float(reject_tax.get("signals_received")) or 0.0
    signals_executed = _as_float(reject_tax.get("signals_executed")) or 0.0
    fill_rate = (signals_executed / signals_received * 100.0) if signals_received > 0 else 0.0

    expected_ev_pct = _as_float(expectation.get("expected_ev_pct"))
    realized_avg = _as_float(trade_stats.get("avg_trade_pnl_pct"))
    ev_error = realized_avg - expected_ev_pct if expected_ev_pct is not None and realized_avg is not None else None

    kpis: Dict[str, Optional[float]] = {
        "net_pnl_after_fees_pct": _as_float(summary.get("total_return_pct")),
        "max_drawdown_pct": _as_float(summary.get("max_drawdown_pct")),
        "fill_rate_pct": round(fill_rate, 4),
        "reject_tax_pct": _as_float(reject_tax.get("policy_block_rate_pct")),
        "expected_value_error_pct": round(ev_error, 4) if ev_error is not None else None,
        "signals_received": signals_received,
        "signals_executed": signals_executed,
        "trades_executed": _as_float(bot_status.get("trades_executed")) or 0.0,
        "trades_failed": _as_float(bot_status.get("trades_failed")) or 0.0,
    }

    now_utc = datetime.now(timezone.utc)
    history_file = Path(history_path)
    history = _load_history(history_file)
    deltas = compute_metric_deltas(kpis, history=history, now_utc=now_utc)
    decision = derive_go_no_go(kpis, thresholds=thresholds, promotion_gate=promotion_gate)

    scorecard = {
        "ts": now_utc.isoformat(),
        "symbol": symbol.upper(),
        "run_id": run_id,
        "strategy": payload.get("strategy"),
        "window": {
            "start_date": payload.get("start_date"),
            "end_date": payload.get("end_date"),
        },
        "kpis": kpis,
        "kpi_deltas": deltas,
        "signal_expectation": expectation,
        "symbol_trade_stats": trade_stats,
        "decision": decision,
        "promotion_gate": promotion_gate,
        "thresholds": {
            "max_drawdown_pct": thresholds.max_drawdown_pct,
            "min_fill_rate_pct": thresholds.min_fill_rate_pct,
            "max_reject_tax_pct": thresholds.max_reject_tax_pct,
            "max_ev_error_pct": thresholds.max_ev_error_pct,
        },
    }

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(scorecard, indent=2), encoding="utf-8")

    if append_history:
        history_file.parent.mkdir(parents=True, exist_ok=True)
        with history_file.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps({"ts": scorecard["ts"], "kpis": kpis, "decision": decision}) + "\n")

    _write_markdown(scorecard, out.with_suffix(".md"))
    return {
        "json_path": str(out),
        "markdown_path": str(out.with_suffix(".md")),
        "history_path": str(history_file),
        "decision": decision.get("decision"),
        "blockers": decision.get("blockers", []),
    }
