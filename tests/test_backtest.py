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


def test_backtest_equity_aggregation_handles_sparse_symbol_timelines():
    # Disjoint symbol timelines should not create artificial drawdown cliffs.
    features = pd.DataFrame(
        {
            "ts": pd.to_datetime(
                [
                    "2024-01-01",
                    "2024-01-02",
                    "2024-01-03",
                    "2024-02-01",
                    "2024-02-02",
                    "2024-02-03",
                ]
            ),
            "symbol": ["BTCUSDT", "BTCUSDT", "BTCUSDT", "ETHUSDT", "ETHUSDT", "ETHUSDT"],
            "ret_1d": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "ret_5d": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "trend_50_200": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "close": [100, 100, 100, 200, 200, 200],
            "atr_14": [1, 1, 1, 1, 1, 1],
            "rsi_14": [50, 50, 50, 50, 50, 50],
            "breakout_20": [0, 0, 0, 0, 0, 0],
        }
    )
    regimes = pd.DataFrame(
        {
            "ts": pd.to_datetime(
                ["2024-01-01", "2024-01-02", "2024-01-03", "2024-02-01", "2024-02-02", "2024-02-03"]
            ),
            "regime": ["Neutral"] * 6,
            "color": ["#999999"] * 6,
            "confidence": [0.5] * 6,
            "rationale": ["test"] * 6,
        }
    )

    result = run(
        features=features,
        regimes=regimes,
        symbols=["BTCUSDT", "ETHUSDT"],
        fee_bps=6.0,
        slippage_bps=5.0,
        base_capital=10_000,
    )

    assert result.summary["trades"] == 0.0
    assert result.summary["max_drawdown_pct"] > -1.0
