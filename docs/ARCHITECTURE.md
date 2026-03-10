# Market Atlas AI Architecture

## Pipeline

1. **Ingest** raw multi-domain data to normalized tables
2. **Feature build** from bars/macro/news context
3. **Regime classification** (macro + liquidity + inflation + growth proxies)
4. **Backtest** regime-aware strategy over historical windows
5. **Export** actionable signals for agents/execution

## Core Tables

- `bars` – normalized OHLCV for all tradables
- `macro_series` – date/value macro metrics (FRED)
- `news_events` – world-news intelligence feed
- `oss_events` – open-source activity intelligence
- `betting_markets` – prediction market states
- `features` – engineered trading features
- `regimes` – market season labels + confidence
- `backtest_runs` / `backtest_trades` – strategy evidence and attribution

## Regime Model (Initial)

Color-coded market seasons:

- `Goldilocks` (green): growth up, inflation cooling
- `Reflation` (orange): liquidity up, inflation up
- `Slowdown` (blue): growth down, inflation cooling
- `Stagflation` (red): growth down, inflation up

Season mapping:
- `Goldilocks` -> `Spring`
- `Reflation` -> `Summer`
- `Slowdown` -> `Autumn`
- `Stagflation` -> `Winter`

Additional state fields:
- `business_cycle_phase`
- `policy_stance`
- `growth` / `inflation` / `liquidity` components

## Integration with Existing Agent / Trading Stack

- Signals exported as JSON with `symbol`, `action`, `confidence`, `edge`, `metadata`
- Risk envelope included in export (`take_profit`, `stop_loss`) from ATR context
- Output can be ingested by existing Sapphire gateway/alpha controls
- Promotion path expected: backtest evidence -> paper lane -> capped live lane

## Promotion + Publish Flow

1. `market-atlas backtest`
2. `market-atlas promotion-gate` (threshold checks)
3. `market-atlas publish-sapphire` (blocked automatically if gate fails unless `--force`)
4. `market-atlas scorecard` (hourly KPI digest + GO/NO-GO decision)

Gate artifact:
- `reports/latest/promotion_gate.json`

Publish artifact:
- `reports/latest/publish_results.json`

Scorecard artifacts:
- `reports/latest/sol_scorecard.json`
- `reports/latest/sol_scorecard.md`
- `reports/scorecards/sol_hourly_history.jsonl`

## Research Outputs

- Operator brief JSON/Markdown for daily decisioning
- Backtest report Markdown + chart artifacts
