from __future__ import annotations

import duckdb


def rebuild_features(conn: duckdb.DuckDBPyConnection) -> int:
    conn.execute("DELETE FROM features")

    conn.execute(
        """
        INSERT INTO features (
            ts,
            symbol,
            close,
            ret_1d,
            ret_5d,
            vol_20d,
            ma_20,
            ma_50,
            ma_200,
            trend_50_200,
            atr_14,
            rsi_14,
            breakout_20,
            source,
            created_at
        )
        WITH step1 AS (
            SELECT
                DATE(ts) AS d,
                symbol,
                high,
                low,
                close,
                LAG(close, 1) OVER (PARTITION BY symbol ORDER BY ts) AS close_l1,
                LAG(close, 5) OVER (PARTITION BY symbol ORDER BY ts) AS close_l5,
                AVG(close) OVER (
                    PARTITION BY symbol ORDER BY ts
                    ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                ) AS ma_20,
                AVG(close) OVER (
                    PARTITION BY symbol ORDER BY ts
                    ROWS BETWEEN 49 PRECEDING AND CURRENT ROW
                ) AS ma_50,
                AVG(close) OVER (
                    PARTITION BY symbol ORDER BY ts
                    ROWS BETWEEN 199 PRECEDING AND CURRENT ROW
                ) AS ma_200,
                MAX(high) OVER (
                    PARTITION BY symbol ORDER BY ts
                    ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                ) AS high_20
            FROM bars
            WHERE timeframe = '1d'
        ),
        step2 AS (
            SELECT
                d,
                symbol,
                high,
                low,
                close,
                close_l1,
                close_l5,
                ma_20,
                ma_50,
                ma_200,
                high_20,
                CASE WHEN close_l1 IS NULL OR close_l1 = 0 THEN NULL ELSE LN(close / close_l1) END AS log_ret_1d,
                CASE
                    WHEN close_l1 IS NULL THEN NULL
                    ELSE GREATEST(high - low, ABS(high - close_l1), ABS(low - close_l1))
                END AS tr_1d,
                CASE WHEN close_l1 IS NULL THEN NULL ELSE GREATEST(close - close_l1, 0) END AS gain_1d,
                CASE WHEN close_l1 IS NULL THEN NULL ELSE GREATEST(close_l1 - close, 0) END AS loss_1d
            FROM step1
        ),
        step3 AS (
            SELECT
                d,
                symbol,
                close,
                close_l1,
                close_l5,
                ma_20,
                ma_50,
                ma_200,
                high_20,
                STDDEV_POP(log_ret_1d) OVER (
                    PARTITION BY symbol ORDER BY d
                    ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                ) AS vol_20d,
                AVG(tr_1d) OVER (
                    PARTITION BY symbol ORDER BY d
                    ROWS BETWEEN 13 PRECEDING AND CURRENT ROW
                ) AS atr_14,
                AVG(gain_1d) OVER (
                    PARTITION BY symbol ORDER BY d
                    ROWS BETWEEN 13 PRECEDING AND CURRENT ROW
                ) AS avg_gain_14,
                AVG(loss_1d) OVER (
                    PARTITION BY symbol ORDER BY d
                    ROWS BETWEEN 13 PRECEDING AND CURRENT ROW
                ) AS avg_loss_14
            FROM step2
        )
        SELECT
            d AS ts,
            symbol,
            close,
            CASE WHEN close_l1 IS NULL OR close_l1 = 0 THEN NULL ELSE (close / close_l1 - 1) END AS ret_1d,
            CASE WHEN close_l5 IS NULL OR close_l5 = 0 THEN NULL ELSE (close / close_l5 - 1) END AS ret_5d,
            vol_20d,
            ma_20,
            ma_50,
            ma_200,
            CASE WHEN ma_200 IS NULL OR ma_200 = 0 THEN NULL ELSE (ma_50 / ma_200 - 1) END AS trend_50_200,
            atr_14,
            CASE
                WHEN avg_loss_14 IS NULL OR avg_loss_14 = 0 THEN NULL
                ELSE 100 - (100 / (1 + (avg_gain_14 / avg_loss_14)))
            END AS rsi_14,
            CASE WHEN high_20 IS NULL OR high_20 = 0 THEN NULL ELSE (close / high_20 - 1) END AS breakout_20,
            'feature_builder_v1' AS source,
            NOW() AS created_at
        FROM step3
        """
    )

    return int(conn.execute("SELECT COUNT(*) FROM features").fetchone()[0])
