from __future__ import annotations

import duckdb
import pandas as pd


REGIME_COLORS = {
    "Goldilocks": "#00c853",
    "Reflation": "#ff9800",
    "Slowdown": "#42a5f5",
    "Stagflation": "#ff1744",
    "Neutral": "#9e9e9e",
}

REGIME_SEASONS = {
    "Goldilocks": "Spring",
    "Reflation": "Summer",
    "Slowdown": "Autumn",
    "Stagflation": "Winter",
    "Neutral": "Interseason",
}


def _classify_row(growth: float, inflation: float, liquidity: float) -> tuple[str, float, str]:
    # Confidence is simple proxy from absolute aggregate z-score magnitude.
    confidence = float(min(1.0, (abs(growth) + abs(inflation) + abs(liquidity)) / 3.0))
    if growth >= 0 and inflation <= 0 and liquidity >= 0:
        return "Goldilocks", confidence, "growth up, inflation cooling, liquidity expanding"
    if growth >= 0 and inflation > 0 and liquidity >= 0:
        return "Reflation", confidence, "growth up with rising inflation and liquidity"
    if growth < 0 and inflation <= 0:
        return "Slowdown", confidence, "growth momentum weakening while inflation cools"
    if growth < 0 and inflation > 0:
        return "Stagflation", confidence, "growth down with sticky/rising inflation"
    return "Neutral", confidence, "mixed macro readings"


def _business_cycle_phase(growth: float, ism_pmi: float) -> str:
    if ism_pmi >= 50 and growth >= 0:
        return "Expansion"
    if ism_pmi < 50 and growth >= 0:
        return "Late Expansion"
    if ism_pmi < 50 and growth < 0:
        return "Contraction"
    return "Transition"


def _policy_stance(policy_rate: float, policy_rate_6m_ago: float) -> str:
    if pd.isna(policy_rate) or pd.isna(policy_rate_6m_ago):
        return "Unknown"
    delta = policy_rate - policy_rate_6m_ago
    if delta >= 0.25:
        return "Tightening"
    if delta <= -0.25:
        return "Easing"
    return "Neutral"


def rebuild_regimes(conn: duckdb.DuckDBPyConnection) -> int:
    features = conn.execute(
        """
        SELECT ts, AVG(ret_5d) AS growth_proxy
        FROM features
        WHERE symbol IN ('SPY', 'QQQ', 'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BTC-USD', 'ETH-USD', 'SOL-USD')
        GROUP BY ts
        ORDER BY ts
        """
    ).fetchdf()

    macro = conn.execute(
        """
        SELECT ts, metric, value
        FROM macro_series
        WHERE metric IN (
            'cpi',
            'm2',
            'fed_balance_sheet',
            'ism_pmi',
            'fed_funds',
            'oil_wti',
            'yield_curve_10y_2y',
            'high_yield_spread'
        )
        ORDER BY ts
        """
    ).fetchdf()

    if features.empty:
        conn.execute("DELETE FROM regimes")
        return 0

    macro_pivot = macro.pivot_table(index="ts", columns="metric", values="value", aggfunc="last").sort_index()
    macro_pivot = macro_pivot.ffill()
    macro_pivot = macro_pivot.reset_index()

    df = features.merge(macro_pivot, left_on="ts", right_on="ts", how="left")
    for col in (
        "cpi",
        "m2",
        "fed_balance_sheet",
        "ism_pmi",
        "fed_funds",
        "oil_wti",
        "yield_curve_10y_2y",
        "high_yield_spread",
    ):
        if col not in df.columns:
            df[col] = 0.0

    df["inflation"] = pd.to_numeric(df["cpi"], errors="coerce").pct_change(12).fillna(0.0)
    df["m2_yoy"] = pd.to_numeric(df["m2"], errors="coerce").pct_change(12).fillna(0.0)
    df["cb_liquidity_yoy"] = pd.to_numeric(df["fed_balance_sheet"], errors="coerce").pct_change(12).fillna(0.0)
    df["liquidity"] = ((df["m2_yoy"] + df["cb_liquidity_yoy"]) / 2.0).fillna(0.0)
    df["growth"] = pd.to_numeric(df["growth_proxy"], errors="coerce").fillna(0.0)
    df["ism_pmi"] = pd.to_numeric(df["ism_pmi"], errors="coerce").fillna(50.0)
    df["fed_funds"] = pd.to_numeric(df["fed_funds"], errors="coerce")
    df["fed_funds_6m_ago"] = df["fed_funds"].shift(6)

    regimes = []
    for row in df.itertuples(index=False):
        regime, confidence, rationale = _classify_row(row.growth, row.inflation, row.liquidity)
        season = REGIME_SEASONS[regime]
        cycle_phase = _business_cycle_phase(row.growth, row.ism_pmi)
        policy = _policy_stance(row.fed_funds, row.fed_funds_6m_ago)
        macro_rationale = (
            f"{rationale}; ism={round(float(row.ism_pmi), 2)}; "
            f"policy={policy}; cycle={cycle_phase}"
        )
        regimes.append(
            {
                "ts": row.ts,
                "regime": regime,
                "season": season,
                "color": REGIME_COLORS[regime],
                "confidence": confidence,
                "growth": float(row.growth),
                "inflation": float(row.inflation),
                "liquidity": float(row.liquidity),
                "policy_rate": float(row.fed_funds) if pd.notna(row.fed_funds) else None,
                "policy_stance": policy,
                "business_cycle_phase": cycle_phase,
                "rationale": macro_rationale,
            }
        )

    regime_df = pd.DataFrame(regimes)
    conn.execute("DELETE FROM regimes")
    conn.register("regime_df", regime_df)
    conn.execute(
        """
        INSERT INTO regimes (
            ts,
            regime,
            season,
            color,
            confidence,
            growth,
            inflation,
            liquidity,
            policy_rate,
            policy_stance,
            business_cycle_phase,
            rationale,
            created_at
        )
        SELECT
            ts,
            regime,
            season,
            color,
            confidence,
            growth,
            inflation,
            liquidity,
            policy_rate,
            policy_stance,
            business_cycle_phase,
            rationale,
            NOW()
        FROM regime_df
        """
    )
    conn.unregister("regime_df")

    return len(regime_df)
