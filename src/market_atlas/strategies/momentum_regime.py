from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np
import pandas as pd


@dataclass
class BacktestResult:
    equity_curve: pd.DataFrame
    trades: pd.DataFrame
    summary: Dict[str, float]


def _window_return(agg_curve: pd.DataFrame, days: int) -> float:
    if agg_curve.empty or len(agg_curve) <= 1:
        return 0.0
    end_equity = float(agg_curve["equity"].iloc[-1])
    cutoff = pd.to_datetime(agg_curve["ts"].iloc[-1]) - pd.Timedelta(days=days)
    window = agg_curve[pd.to_datetime(agg_curve["ts"]) >= cutoff]
    if window.empty:
        return 0.0
    start_equity = float(window["equity"].iloc[0])
    if start_equity <= 0:
        return 0.0
    return float((end_equity / start_equity - 1.0) * 100)


def run(
    features: pd.DataFrame,
    regimes: pd.DataFrame,
    symbols: List[str],
    fee_bps: float,
    slippage_bps: float,
    base_capital: float,
) -> BacktestResult:
    if features.empty:
        empty = pd.DataFrame(columns=["ts", "equity"])
        return BacktestResult(empty, pd.DataFrame(), {"trades": 0, "total_return_pct": 0.0})

    merged = features.merge(regimes[["ts", "regime"]], on="ts", how="left")
    merged["regime"] = merged["regime"].fillna("Neutral")
    merged = merged[merged["symbol"].isin(symbols)].copy()
    merged = merged.sort_values(["symbol", "ts"])
    for col in ("close", "atr_14", "rsi_14", "breakout_20"):
        if col not in merged.columns:
            merged[col] = np.nan
    if merged["close"].isna().all():
        merged["close"] = (
            merged.groupby("symbol")["ret_1d"]
            .transform(lambda s: 100.0 * (1.0 + s.fillna(0.0)).cumprod())
            .astype(float)
        )

    cost = (fee_bps + slippage_bps) / 10000.0
    records = []
    trade_rows = []
    n_symbols = max(1, len(symbols))
    symbol_capital = base_capital / n_symbols

    for symbol, sdf in merged.groupby("symbol"):
        cash = symbol_capital
        units = 0.0
        entry_cash = np.nan
        entry_price = np.nan
        entry_date = None
        entry_atr = np.nan

        for row in sdf.itertuples(index=False):
            price = row.close if row.close is not None else np.nan
            if np.isnan(price) or price <= 0:
                continue

            trend = row.trend_50_200 if row.trend_50_200 is not None else 0.0
            breakout = row.breakout_20 if row.breakout_20 is not None else 0.0
            rsi = row.rsi_14 if row.rsi_14 is not None else 50.0
            atr = row.atr_14 if row.atr_14 is not None else 0.0
            risk_on = row.regime in {"Goldilocks", "Reflation"}

            in_pos = units > 0
            entry_signal = (trend > 0) and (breakout > -0.02) and (35 <= rsi <= 75) and risk_on and not in_pos
            exit_signal = in_pos and ((trend < 0) or (row.regime in {"Slowdown", "Stagflation"}))

            if in_pos and not np.isnan(entry_price) and atr > 0:
                stop_px = entry_price - 1.5 * atr
                tp_px = entry_price + 2.5 * atr
                if price <= stop_px or price >= tp_px:
                    exit_signal = True

            if entry_signal:
                exec_price = price * (1 + cost)
                units = cash / exec_price if exec_price > 0 else 0.0
                entry_price = exec_price
                entry_date = row.ts
                entry_cash = cash
                entry_atr = atr
                cash = 0.0

            if units > 0 and exit_signal:
                exec_price = price * (1 - cost)
                cash = units * exec_price
                pnl_pct = ((cash / entry_cash) - 1.0) * 100 if entry_cash and entry_cash > 0 else 0.0
                trade_rows.append(
                    {
                        "ts": row.ts,
                        "symbol": symbol,
                        "side": "LONG",
                        "qty": float(units),
                        "entry": entry_price,
                        "exit": exec_price,
                        "pnl_pct": float(pnl_pct),
                        "regime": row.regime,
                        "metadata": {
                            "entry_date": str(entry_date),
                            "entry_atr": float(entry_atr) if not np.isnan(entry_atr) else None,
                            "exit_reason": "trend_regime_or_risk_exit",
                        },
                    }
                )
                units = 0.0
                entry_price = np.nan
                entry_date = None
                entry_cash = np.nan
                entry_atr = np.nan

            equity = cash + (units * price)
            records.append({"ts": row.ts, "symbol": symbol, "equity": float(equity)})

    curve = pd.DataFrame(records)
    if curve.empty:
        return BacktestResult(curve, pd.DataFrame(), {"trades": 0, "total_return_pct": 0.0})

    agg = curve.groupby("ts", as_index=False)["equity"].sum().sort_values("ts")
    peak = agg["equity"].cummax()
    drawdown = (agg["equity"] / peak - 1.0)

    total_return_pct = float((agg["equity"].iloc[-1] / agg["equity"].iloc[0] - 1.0) * 100)
    daily_ret = agg["equity"].pct_change().dropna()
    ann_sharpe = 0.0
    if not daily_ret.empty and daily_ret.std() > 0:
        ann_sharpe = float((daily_ret.mean() / daily_ret.std()) * np.sqrt(252))

    trades_df = pd.DataFrame(trade_rows)
    win_rate = float(trades_df["pnl_pct"].gt(0).mean() * 100) if not trades_df.empty else 0.0
    summary = {
        "trades": float(len(trade_rows)),
        "total_return_pct": total_return_pct,
        "max_drawdown_pct": float(drawdown.min() * 100),
        "win_rate_pct": win_rate,
        "sharpe_annualized": ann_sharpe,
        "return_7d_pct": _window_return(agg, 7),
        "return_30d_pct": _window_return(agg, 30),
        "return_90d_pct": _window_return(agg, 90),
        "return_180d_pct": _window_return(agg, 180),
    }

    return BacktestResult(agg, trades_df, summary)
