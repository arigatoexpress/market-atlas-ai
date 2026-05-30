# Market Atlas AI — Agent Notes

Read this first before editing code, docs, or configuration.

## What this repo does

Local-first multi-asset intelligence platform that ingests public data, computes regime-aware features, runs backtests, and exports trading signals to Sapphire. Built for research and paper-trading workflows.

## Key directories and files

| Path | Purpose |
|---|---|
| `src/market_atlas/connectors/` | Data source adapters (Binance, Yahoo, FRED, GDELT, Polymarket, GitHub) |
| `src/market_atlas/pipelines/` | ETL, feature engineering, regime detection, backtest flows |
| `src/market_atlas/strategies/` | Strategy implementations |
| `src/market_atlas/core/` | Config, DB primitives, CLI entrypoint |
| `src/market_atlas/exports/` | Sapphire signal export schema |
| `tests/` | Regression tests |
| `scripts/` | Cron and automation scripts |
| `data/` | Local DuckDB + downloaded artifacts |
| `reports/` | Generated briefs, charts, scorecards |

## How to run tests / dev server

```bash
source .venv/bin/activate

# Run tests
pytest

# Run the full pipeline
market-atlas full-run --start-date 2024-01-01

# Lint
ruff check .
```

## Safety boundaries

- **Never** commit `.env`, `data/*.db`, `data/*.duckdb`, or `reports/` with live artifacts.
- **Never** bypass the promotion gate (`--force`) for signal publishing without explicit confirmation.
- **Never** delete `data/` or `reports/` directories that contain operational history.
- Do not change the Sapphire signal export schema without coordinating with `~/Code/Sapphire`.
