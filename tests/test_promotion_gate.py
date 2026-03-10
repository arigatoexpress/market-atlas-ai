from market_atlas.pipelines.promotion import PromotionThresholds, evaluate_promotion_gate


def test_promotion_gate_fail_on_drawdown():
    payload = {
        "run_id": "r1",
        "strategy": "momentum_regime",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "symbols": "BTCUSDT,ETHUSDT,SOLUSDT",
        "summary": {
            "trades": 120,
            "total_return_pct": 32.0,
            "max_drawdown_pct": -55.0,
            "win_rate_pct": 49.0,
            "sharpe_annualized": 1.8,
        },
    }
    thresholds = PromotionThresholds(
        min_trades=60,
        min_return_pct=20.0,
        max_drawdown_pct=-35.0,
        min_win_rate_pct=45.0,
        min_sharpe=1.2,
    )
    gate = evaluate_promotion_gate(payload, thresholds)
    assert gate["passed"] is False
    assert any(c["name"] == "max_drawdown_pct" and c["pass"] is False for c in gate["checks"])


def test_promotion_gate_pass():
    payload = {
        "run_id": "r2",
        "strategy": "momentum_regime",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "symbols": "BTCUSDT,ETHUSDT,SOLUSDT",
        "summary": {
            "trades": 180,
            "total_return_pct": 48.0,
            "max_drawdown_pct": -22.0,
            "win_rate_pct": 54.0,
            "sharpe_annualized": 2.1,
        },
    }
    thresholds = PromotionThresholds(
        min_trades=60,
        min_return_pct=20.0,
        max_drawdown_pct=-35.0,
        min_win_rate_pct=45.0,
        min_sharpe=1.2,
    )
    gate = evaluate_promotion_gate(payload, thresholds)
    assert gate["passed"] is True
