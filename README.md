# Market Atlas AI

Local-first intelligence and strategy lab for crypto, equities, macro, and open-source data.

## Consolidated platform

Market Atlas AI is the consolidated trading flagship. Two formerly-standalone repos now live here as history-preserving subtrees under `packages/`:

- **`packages/tradingview-mcp`** — TypeScript MCP server exposing TradingView data/tooling to agents.
- **`packages/autonomous-manager`** — Python autonomous trading manager (strategies, webhook server, backend).

Each package keeps its own manifest and build (`package.json` / `pyproject.toml`), so build and test them in their own directories.

The platform is re-centered on **Hyperliquid, modern EVM/L2 perps, and prediction markets** — a strategic pivot off Sui.

## What this does

Market Atlas AI ingests public market and news data, normalizes it into a local DuckDB warehouse, builds regime-aware features, runs historical backtests, and exports structured signals for downstream trading agents. Everything runs locally by default; no cloud dependency required.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env

# Full pipeline
market-atlas full-run --start-date 2024-01-01
```

## CLI workflow

```bash
market-atlas init-db
market-atlas ingest --start-date 2024-01-01
market-atlas features
market-atlas regimes
market-atlas backtest --strategy momentum_regime --start-date 2024-01-01
market-atlas export-signals --output data/latest_signals.json
market-atlas scorecard --symbol SOLUSDT
```

## Architecture

```
Sources (Binance, Yahoo, FRED, GDELT, Polymarket)
        ↓
Connectors → DuckDB warehouse
        ↓
Pipelines (features → regimes → backtest → signals)
        ↓
Export (JSON signals, operator briefs, scorecards)
```

## Key features

- Multi-asset OHLCV: crypto (Binance) + equities/commodities (Yahoo Finance)
- Macro regime labeling: Goldilocks / Reflation / Slowdown / Stagflation
- Backtest engine with promotion gates
- SOL scorecard with hourly cron support
- Signal export compatible with Sapphire gateway

## Tech stack

Python · DuckDB · Pandas · Matplotlib · Pydantic

## Safety & disclaimers

- **Research/prototype software.** Not financial advice.
- **Paper trading first.** All signals require explicit promotion-gate approval before live use.
- **Fail-closed by default.** `publish-sapphire` enforces backtest gates; use `--force` only for deliberate paper-lane overrides.
- **Local data stays local.** `data/` and `reports/` contain operational artifacts—never commit them.

## Agent collaborators

See [AGENTS.md](AGENTS.md) for key paths, dev commands, and safety boundaries.
