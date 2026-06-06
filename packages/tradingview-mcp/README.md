# TradingView MCP

An MCP server that connects Claude Code to TradingView Premium via Playwright browser automation and real-time WebSocket feeds. It exposes 26+ tools for market data, chart capture, alerts, watchlists, and Pine Script development.

## What this does

This server lets Claude Code query live market data, capture TradingView charts, manage alerts and watchlists, develop Pine Script, and receive webhook signals — all through a standard Model Context Protocol (MCP) interface.

## Quick start

```bash
npm install
npx playwright install chromium
npm run build
```

Copy `.env.example` to `.env` and add your TradingView session cookies.

**Run in dev mode:**
```bash
npm run dev
```

**Run tests:**
```bash
npm test
npm run typecheck
npm run lint
```

## Architecture

```
Claude Code  ◄──stdio──►  TradingView MCP Server  ◄──Playwright──►  TradingView Web UI
                                                  │
                                                  ├── WebSocket ──►  @mathieuc/tradingview
                                                  │
                                                  └── HTTP webhook ──►  Sapphire / External
```

## Key features

- **Market data** — real-time quotes, OHLCV candles, technical indicators, screener results
- **Chart capture** — full TradingView screenshots with premium layouts and indicators
- **Alerts & watchlists** — create, list, and monitor through the web UI
- **Pine Script** — validate syntax, generate templates, write to the Pine Editor, compile strategies
- **Webhook signals** — listen for real-time strategy alerts and forward them to Claude

## Tech stack

- Node.js ≥ 20
- TypeScript 5.7+ (strict mode)
- MCP SDK
- Playwright
- Vitest
- Express (webhooks)

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `TRADINGVIEW_SESSION_ID` | Yes | `sessionid` cookie from tradingview.com |
| `TRADINGVIEW_SESSION_ID_SIGN` | Yes | `sessionid_sign` cookie from tradingview.com |
| `WEBHOOK_PORT` | No | Webhook listener port (default: `3456`) |
| `WEBHOOK_SECRET` | No | Secret token to validate incoming webhooks |

> Never commit `.env` or log cookie values.

## Usage with Claude Code

```bash
TRADINGVIEW_SESSION_ID=xxx TRADINGVIEW_SESSION_ID_SIGN=yyy npx @anthropic-ai/claude-code
# Then: /mcp add tradingview node dist/index.js
```

## Docker

```bash
docker build -t tradingview-mcp .
docker run -e TRADINGVIEW_SESSION_ID=xxx -e TRADINGVIEW_SESSION_ID_SIGN=yyy -p 3456:3456 tradingview-mcp
```

## Agent collaborators

See [AGENTS.md](AGENTS.md) for build rules, safety boundaries, and coding conventions.

## License

MIT
