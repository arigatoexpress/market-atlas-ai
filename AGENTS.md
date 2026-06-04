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

## Operating Charter

> Guiding principles for any AI agent (or human) working in this repo. Derived from the Andrej Karpathy engineering philosophy. Tool-neutral: applies whether you drive this repo with Claude Code, goose, or by hand.

### The four rules
1. **Simplicity first.** Write the minimum code that solves the task. No speculative abstractions, no unrequested features, no single-use platforms. Extract a shared module only when there are >= 2 real call-sites today.
2. **Surgical changes, one concern per PR.** Touch only what the task requires. Do not opportunistically reformat, bump unrelated deps, or fix adjacent dead code. Small, reviewable, independently revertable diffs.
3. **Evals are the spec.** Define and run the repo verification (tests, build, typecheck, smoke) BEFORE and AFTER a change. Nothing merges unless it stays green. Keep the generate->verify loop tight and reversible.
4. **Delete > add; fewer dependencies.** Removing code, repos, and dependencies is the highest-leverage move. Every dependency is attack surface you own. Pin and lock what remains. Humans stay in the loop for irreversible / outward-facing / production steps (deletes, credential rotation, infra teardown, deploys).

### Safety
- Never use `git add .` or `git add -A` — stage changed files by explicit path (avoids sweeping in WIP or secrets).
- Never commit secrets; `.env*` stays gitignored (except `.env.example`).
- Treat anything outward-facing or irreversible as draft-then-confirm.
