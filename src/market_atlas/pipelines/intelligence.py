from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import duckdb


def _symbol_score(row) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 0.0

    trend = float(row.trend_50_200 or 0.0)
    breakout = float(row.breakout_20 or 0.0)
    rsi = float(row.rsi_14 or 50.0)
    regime = row.regime or "Neutral"

    score += max(-2.0, min(2.0, trend * 100))
    if trend > 0:
        reasons.append("positive trend")
    elif trend < 0:
        reasons.append("negative trend")

    score += max(-1.5, min(1.5, breakout * 50))
    if breakout > -0.01:
        reasons.append("near breakout range")
    else:
        reasons.append("below breakout threshold")

    if 45 <= rsi <= 70:
        score += 0.7
        reasons.append("healthy RSI regime")
    elif rsi > 80:
        score -= 0.8
        reasons.append("overbought RSI")
    elif rsi < 30:
        score += 0.3
        reasons.append("oversold RSI")

    if regime in {"Goldilocks", "Reflation"}:
        score += 1.0
        reasons.append(f"macro risk-on ({regime})")
    elif regime in {"Slowdown", "Stagflation"}:
        score -= 1.0
        reasons.append(f"macro risk-off ({regime})")

    return score, reasons


def build_operator_brief(conn: duckdb.DuckDBPyConnection, symbols: Iterable[str], output_path: str) -> dict:
    symbols = [s.strip() for s in symbols if s.strip()]
    if not symbols:
        raise ValueError("No symbols provided for operator brief.")

    latest = conn.execute(
        """
        SELECT
            f.symbol,
            f.ts,
            f.close,
            f.trend_50_200,
            f.breakout_20,
            f.rsi_14,
            f.atr_14,
            r.regime,
            r.season,
            r.business_cycle_phase,
            r.policy_stance,
            r.confidence
        FROM features f
        LEFT JOIN regimes r ON f.ts = r.ts
        WHERE f.symbol IN ({placeholders})
        QUALIFY ROW_NUMBER() OVER (PARTITION BY f.symbol ORDER BY f.ts DESC) = 1
        """.format(placeholders=",".join(["?"] * len(symbols))),
        symbols,
    ).fetchdf()

    if latest.empty:
        raise ValueError("No feature rows found. Run `market-atlas ingest` and `market-atlas features` first.")

    ranked = []
    for row in latest.itertuples(index=False):
        score, reasons = _symbol_score(row)
        stance = "LONG_BIAS" if score >= 1.0 else ("SHORT_BIAS" if score <= -1.0 else "NEUTRAL")
        ranked.append(
            {
                "symbol": row.symbol,
                "score": round(score, 3),
                "stance": stance,
                "close": float(row.close) if row.close is not None else None,
                "atr_14": float(row.atr_14) if row.atr_14 is not None else None,
                "regime": row.regime,
                "season": row.season,
                "cycle": row.business_cycle_phase,
                "policy": row.policy_stance,
                "confidence": float(row.confidence) if row.confidence is not None else None,
                "reasons": reasons,
                "ts": str(row.ts),
            }
        )

    ranked = sorted(ranked, key=lambda x: x["score"], reverse=True)
    top_long = next((r for r in ranked if r["stance"] == "LONG_BIAS"), None)
    top_short = next((r for r in reversed(ranked) if r["stance"] == "SHORT_BIAS"), None)

    macro = conn.execute(
        """
        SELECT ts, regime, season, business_cycle_phase, policy_stance, confidence, rationale
        FROM regimes
        ORDER BY ts DESC
        LIMIT 1
        """
    ).fetchone()

    macro_state = (
        {
            "ts": str(macro[0]),
            "regime": macro[1],
            "season": macro[2],
            "business_cycle_phase": macro[3],
            "policy_stance": macro[4],
            "confidence": float(macro[5]) if macro[5] is not None else None,
            "rationale": macro[6],
        }
        if macro
        else {}
    )

    brief = {
        "macro_state": macro_state,
        "ranking": ranked,
        "top_long_candidate": top_long,
        "top_short_candidate": top_short,
    }

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(brief, indent=2), encoding="utf-8")

    md_lines = [
        "# Market Atlas Operator Brief",
        "",
        "## Macro State",
        "",
        f"- Regime: `{macro_state.get('regime', 'n/a')}` ({macro_state.get('season', 'n/a')})",
        f"- Cycle: `{macro_state.get('business_cycle_phase', 'n/a')}`",
        f"- Policy: `{macro_state.get('policy_stance', 'n/a')}`",
        f"- Confidence: `{macro_state.get('confidence', 0.0)}`",
        f"- Rationale: {macro_state.get('rationale', 'n/a')}",
        "",
        "## Symbol Ranking",
        "",
    ]
    for item in ranked:
        reason = "; ".join(item["reasons"])
        md_lines.append(f"- `{item['symbol']}` | score `{item['score']}` | `{item['stance']}` | {reason}")

    md_path = out_path.with_suffix(".md")
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    return {"json_path": str(out_path), "markdown_path": str(md_path), "symbols_ranked": len(ranked)}
