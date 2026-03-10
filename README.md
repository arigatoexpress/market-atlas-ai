# Market Atlas AI

Market Atlas AI is a **local-first intelligence and strategy lab** for:

- Crypto
- Equities
- Commodities / macro proxies
- World news
- Open-source intelligence
- Betting/prediction markets

The system ingests open-source data, normalizes it into a local DuckDB warehouse, builds features and regime labels, runs historical backtests across regimes, and exports structured signals for downstream trading agents.

## Principles

1. Local-first by default (DuckDB + files)
2. Deterministic, auditable pipelines
3. Data quality + regime awareness before signal generation
4. Clear separation: data -> features -> regimes -> strategy -> export

## Quick Start

```bash
cd /Users/aribs/Documents/Organized/Codex Projects/github/market-atlas-ai
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
market-atlas full-run --start-date 2024-01-01
```

## CLI Workflow

```bash
market-atlas init-db
market-atlas reset-db
market-atlas ingest --start-date 2024-01-01
market-atlas features
market-atlas regimes
market-atlas backtest --strategy momentum_regime --start-date 2024-01-01
market-atlas export-signals --output data/latest_signals.json
market-atlas brief --symbols BTCUSDT,ETHUSDT,SOLUSDT,SPY,QQQ,GLD,SLV,CL=F
market-atlas report --output-dir reports/latest
market-atlas promotion-gate --output reports/latest/promotion_gate.json
market-atlas publish-sapphire --symbols SOLUSDT
market-atlas scorecard --symbol SOLUSDT
```

## Data Domains Included

- **Crypto OHLCV:** Binance public Klines
  - automatic Yahoo Finance fallback if Binance is region-blocked
- **Equities + commodities:** Yahoo Finance
- **Macro:** FRED graph CSV endpoints
- **World news:** GDELT Doc API
- **Open-source intel:** GitHub Search API
- **Prediction markets:** Polymarket Gamma API

## Key Macro / Regime Inputs

- Monetary policy: `FEDFUNDS`
- ISM cycle proxy: `NAPM`
- Inflation: `CPIAUCSL`
- Liquidity proxies: `M2SL`, `WALCL`
- Commodities / stress: `DCOILWTICO`, high-yield spread
- Curve / dollar context: `T10Y2Y`, `DTWEXBGS`

Regime output includes:
- `regime` (Goldilocks / Reflation / Slowdown / Stagflation)
- `season` (Spring / Summer / Autumn / Winter)
- `business_cycle_phase`
- `policy_stance`
- confidence + rationale

## Output Artifacts

- Signals: `data/latest_signals.json`
- Operator brief: `reports/latest/operator_brief.{json,md}`
- Backtest report: `reports/latest/report.md`
- Charts:
  - `reports/latest/equity_curve.png`
  - `reports/latest/trade_pnl_distribution.png`

## Integration Surface

Signal export schema in `/Users/aribs/Documents/Organized/Codex Projects/github/market-atlas-ai/src/market_atlas/exports/sapphire_signal.py` is designed to plug into your existing agent/trading orchestration.

For local Sapphire stack integration:

- publishes to `POST /api/signals/create` on local gateway
- includes strategy/timeframe metadata passthrough
- enforces backtest promotion gate by default before publish
- use `--force` only for deliberate paper-lane overrides

Example:

```bash
market-atlas promotion-gate --output reports/latest/promotion_gate.json
market-atlas publish-sapphire \
  --symbols SOLUSDT \
  --gateway-url http://127.0.0.1:18080
```

If your gateway requires auth:

```bash
export SAPPHIRE_GATEWAY_API_TOKEN='...'
market-atlas publish-sapphire --symbols SOLUSDT
```

Strict local paper loop (SOL-only default):

```bash
bash scripts/run_local_cycle.sh
# optional override to multi-symbol research publish:
# STRICT_LIVE_MODE=false SYMBOLS=BTCUSDT,ETHUSDT,SOLUSDT bash scripts/run_local_cycle.sh
```

Hourly SOL scorecard loop (includes publish + KPI digest):

```bash
bash scripts/run_hourly_sol_scorecard.sh
```

This writes:
- `reports/latest/sol_scorecard.json`
- `reports/latest/sol_scorecard.md`
- `reports/scorecards/sol_hourly_history.jsonl`

## Project Layout

- `/Users/aribs/Documents/Organized/Codex Projects/github/market-atlas-ai/src/market_atlas/connectors` – source adapters
- `/Users/aribs/Documents/Organized/Codex Projects/github/market-atlas-ai/src/market_atlas/pipelines` – ETL + feature + regime + backtest flows
- `/Users/aribs/Documents/Organized/Codex Projects/github/market-atlas-ai/src/market_atlas/strategies` – strategy implementations
- `/Users/aribs/Documents/Organized/Codex Projects/github/market-atlas-ai/src/market_atlas/core` – config + DB primitives
- `/Users/aribs/Documents/Organized/Codex Projects/github/market-atlas-ai/tests` – regression tests

## Next Build Stages

1. Add data quality dashboard (freshness / missingness / drift)
2. Add probabilistic EV ranking (P(win) * payoff - costs)
3. Add strategy promotion gates (backtest -> paper -> capped live)
4. Add live bridge publisher to local Sapphire gateway
