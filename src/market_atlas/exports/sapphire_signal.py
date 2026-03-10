from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import duckdb


def build_signals(conn: duckdb.DuckDBPyConnection, symbols: List[str]) -> List[dict]:
    if not symbols:
        return []

    latest = conn.execute(
        """
        SELECT
            f.symbol,
            f.ts,
            f.close,
            f.ret_1d,
            f.ret_5d,
            f.trend_50_200,
            f.atr_14,
            f.rsi_14,
            f.breakout_20,
            r.regime,
            r.season,
            r.confidence,
            r.business_cycle_phase
        FROM features f
        LEFT JOIN regimes r ON f.ts = r.ts
        WHERE f.symbol IN ({placeholders})
        QUALIFY ROW_NUMBER() OVER (PARTITION BY f.symbol ORDER BY f.ts DESC) = 1
        """.format(placeholders=",".join(["?"] * len(symbols))),
        symbols,
    ).fetchdf()

    signals = []
    for row in latest.itertuples(index=False):
        trend = row.trend_50_200 if row.trend_50_200 is not None else 0.0
        confidence = float(max(0.0, min(1.0, 0.5 + trend * 5)))
        if row.confidence is not None:
            confidence = float(max(0.0, min(1.0, 0.6 * confidence + 0.4 * float(row.confidence))))
        action = "HOLD"
        if trend > 0.01 and row.regime in {"Goldilocks", "Reflation"}:
            action = "BUY"
        elif trend < -0.01 or row.regime in {"Slowdown", "Stagflation"}:
            action = "SELL"

        close = float(row.close) if row.close is not None else None
        atr = float(row.atr_14) if row.atr_14 is not None else None
        sl = None
        tp = None
        if close and atr and atr > 0:
            if action == "BUY":
                sl = round(close - 1.5 * atr, 6)
                tp = round(close + 2.5 * atr, 6)
            elif action == "SELL":
                sl = round(close + 1.5 * atr, 6)
                tp = round(close - 2.5 * atr, 6)

        signals.append(
            {
                "signal_id": f"atlas-{row.symbol}-{int(datetime.now(timezone.utc).timestamp())}",
                "symbol": row.symbol,
                "action": action,
                "confidence": round(confidence, 4),
                "edge": round((row.ret_5d or 0.0) - (row.ret_1d or 0.0), 6),
                "timeframe": "1d",
                "strategy": "momentum_regime",
                "take_profit": tp,
                "stop_loss": sl,
                "metadata": {
                    "regime": row.regime,
                    "season": row.season,
                    "regime_confidence": row.confidence,
                    "business_cycle_phase": row.business_cycle_phase,
                    "trend_50_200": trend,
                    "atr_14": atr,
                    "rsi_14": float(row.rsi_14) if row.rsi_14 is not None else None,
                    "breakout_20": float(row.breakout_20) if row.breakout_20 is not None else None,
                    "source": "market_atlas",
                    "ts": str(row.ts),
                },
            }
        )

    return signals


def export_signals(conn: duckdb.DuckDBPyConnection, symbols: List[str], output_path: str) -> List[dict]:
    signals = build_signals(conn, symbols)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(signals, indent=2), encoding="utf-8")

    for sig in signals:
        conn.execute("INSERT INTO exported_signals (payload) VALUES (?)", [json.dumps(sig)])

    return signals
