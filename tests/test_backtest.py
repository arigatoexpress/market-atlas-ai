import pandas as pd

from market_atlas.strategies.momentum_regime import run


def test_backtest_returns_summary():
    features = pd.DataFrame(
        {
            "ts": pd.date_range("2024-01-01", periods=6, freq="D"),
            "symbol": ["BTCUSDT"] * 6,
            "ret_1d": [0.0, 0.01, 0.01, -0.005, 0.01, 0.0],
            "ret_5d": [0.0, 0.02, 0.03, 0.02, 0.03, 0.02],
            "trend_50_200": [0.02, 0.02, 0.02, 0.01, -0.02, -0.02],
        }
    )
    regimes = pd.DataFrame(
        {
            "ts": pd.date_range("2024-01-01", periods=6, freq="D"),
            "regime": ["Goldilocks", "Goldilocks", "Reflation", "Reflation", "Slowdown", "Slowdown"],
            "color": ["#00c853"] * 6,
            "confidence": [0.7] * 6,
            "rationale": ["test"] * 6,
        }
    )

    result = run(
        features=features,
        regimes=regimes,
        symbols=["BTCUSDT"],
        fee_bps=6.0,
        slippage_bps=5.0,
        base_capital=10_000,
    )

    assert "total_return_pct" in result.summary
    assert "max_drawdown_pct" in result.summary
    assert "trades" in result.summary
    assert "return_30d_pct" in result.summary
    assert "sharpe_annualized" in result.summary
