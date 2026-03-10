import duckdb

from market_atlas.core.db import init_db
from market_atlas.exports.sapphire_signal import build_signals


def test_build_signals_includes_tp_sl_and_metadata():
    conn = duckdb.connect(":memory:")
    init_db(conn)

    conn.execute(
        """
        INSERT INTO features (
            ts, symbol, close, ret_1d, ret_5d, vol_20d, ma_20, ma_50, ma_200,
            trend_50_200, atr_14, rsi_14, breakout_20, source
        )
        VALUES
            ('2026-03-01', 'BTCUSDT', 100.0, 0.01, 0.03, 0.2, 95, 98, 90, 0.08, 2.0, 60, 0.01, 'test')
        """
    )
    conn.execute(
        """
        INSERT INTO regimes (
            ts, regime, season, color, confidence, growth, inflation, liquidity,
            policy_rate, policy_stance, business_cycle_phase, rationale
        )
        VALUES
            ('2026-03-01', 'Goldilocks', 'Spring', '#00c853', 0.8, 0.1, -0.02, 0.03, 4.5, 'Neutral', 'Expansion', 'test')
        """
    )

    signals = build_signals(conn, ["BTCUSDT"])
    assert len(signals) == 1

    sig = signals[0]
    assert sig["action"] == "BUY"
    assert sig["take_profit"] is not None
    assert sig["stop_loss"] is not None
    assert sig["metadata"]["season"] == "Spring"
