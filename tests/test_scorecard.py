from datetime import datetime, timedelta, timezone

from market_atlas.pipelines.scorecard import (
    ScorecardThresholds,
    compute_metric_deltas,
    derive_go_no_go,
)


def test_compute_metric_deltas_uses_time_windows():
    now = datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc)
    history = [
        {
            "ts": (now - timedelta(hours=2)).isoformat(),
            "kpis": {
                "fill_rate_pct": 80.0,
                "reject_tax_pct": 5.0,
                "expected_value_error_pct": 1.0,
                "max_drawdown_pct": -30.0,
                "net_pnl_after_fees_pct": 25.0,
            },
        },
        {
            "ts": (now - timedelta(hours=7)).isoformat(),
            "kpis": {
                "fill_rate_pct": 70.0,
                "reject_tax_pct": 10.0,
                "expected_value_error_pct": 2.0,
                "max_drawdown_pct": -32.0,
                "net_pnl_after_fees_pct": 20.0,
            },
        },
        {
            "ts": (now - timedelta(hours=26)).isoformat(),
            "kpis": {
                "fill_rate_pct": 60.0,
                "reject_tax_pct": 20.0,
                "expected_value_error_pct": 4.0,
                "max_drawdown_pct": -36.0,
                "net_pnl_after_fees_pct": 10.0,
            },
        },
    ]
    current = {
        "fill_rate_pct": 90.0,
        "reject_tax_pct": 3.0,
        "expected_value_error_pct": 0.5,
        "max_drawdown_pct": -28.0,
        "net_pnl_after_fees_pct": 30.0,
    }
    deltas = compute_metric_deltas(current, history=history, now_utc=now)

    assert deltas["fill_rate_pct"]["delta_1h"] == 10.0
    assert deltas["fill_rate_pct"]["delta_6h"] == 20.0
    assert deltas["fill_rate_pct"]["delta_24h"] == 30.0
    assert deltas["reject_tax_pct"]["delta_1h"] == -2.0


def test_derive_go_no_go_blocks_on_fill_and_reject_tax():
    kpis = {
        "max_drawdown_pct": -20.0,
        "fill_rate_pct": 40.0,
        "reject_tax_pct": 35.0,
        "expected_value_error_pct": 1.0,
        "signals_received": 10.0,
        "trades_failed": 0.0,
    }
    decision = derive_go_no_go(
        kpis,
        ScorecardThresholds(
            max_drawdown_pct=-35.0,
            min_fill_rate_pct=70.0,
            max_reject_tax_pct=25.0,
            max_ev_error_pct=5.0,
        ),
    )
    assert decision["decision"] == "NO_GO"
    blocker_codes = {b["code"] for b in decision["blockers"]}
    assert "fill_rate_low" in blocker_codes
    assert "reject_tax_high" in blocker_codes


def test_derive_go_no_go_passes_clean_snapshot():
    kpis = {
        "max_drawdown_pct": -18.0,
        "fill_rate_pct": 100.0,
        "reject_tax_pct": 0.0,
        "expected_value_error_pct": 1.2,
        "signals_received": 8.0,
        "trades_failed": 0.0,
    }
    decision = derive_go_no_go(
        kpis,
        ScorecardThresholds(
            max_drawdown_pct=-35.0,
            min_fill_rate_pct=70.0,
            max_reject_tax_pct=25.0,
            max_ev_error_pct=5.0,
        ),
    )
    assert decision["decision"] == "GO"
    assert decision["blockers"] == []
