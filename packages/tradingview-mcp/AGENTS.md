# TradingView MCP — Agent Guidelines

## What this repo does

TypeScript/Node MCP server connecting Claude Code to TradingView via Playwright browser automation and WebSocket data feeds. It exposes 26+ tools across market data, charts, alerts, watchlists, Pine Script, and webhooks.

## Key directories and files

| Path | Purpose |
|------|---------|
| `src/index.ts` | MCP server entrypoint, tool registration, stdio transport |
| `src/tools/` | Tool definitions: market-data, chart, alert, watchlist, pine-script, webhook |
| `src/services/` | Browser automation, TradingView client, webhook server |
| `src/types/` | Shared TypeScript types |
| `src/__tests__/` | Module-adjacent unit tests |
| `tests/` | Integration-style tests |

## How to run tests / dev server

```bash
npm run dev          # tsx watch, no build step
npm test             # vitest run
npm run typecheck    # tsc --noEmit
npm run lint         # eslint
npm run build        # compile to dist/
```

## Safety boundaries

1. **Never change TradingView DOM selectors** without verifying them in a live Playwright session. Selectors are brittle and break silently.
2. **Never log session cookies** (`sessionid`, `sessionid_sign`) or the `WEBHOOK_SECRET`.
3. **Never commit `.env` files** — use `.env.example` for documentation only.
4. Browser automation methods should use `page.evaluate()` sparingly; prefer explicit Playwright actions where possible.
5. The webhook server listens on `127.0.0.1` by default — do not expose to `0.0.0.0` in production without authentication.

## Dependency policy

- Do not add runtime dependencies without justification.
- `@anthropic-ai/sdk` was removed because it is unused — do not re-add without a concrete use case.
- Keep `playwright` as a standard (non-dev) dependency because the server launches browsers at runtime.

## Current status

Production-ready. All tools are unit-tested with mocked Playwright and Express. No live browser or network calls in tests.
