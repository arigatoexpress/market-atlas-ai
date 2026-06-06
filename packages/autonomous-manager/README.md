# TradingView Autonomous Manager

Autonomous TradingView Desktop control and signal forwarding for the Sapphire trading stack.

## What this does

This repo automates TradingView Desktop via Playwright, manages Pine Script strategies and watchlists, and forwards signals to the Sapphire bridge for paper or live execution on ASTER and LIGHTER DEXs. It runs on a Raspberry Pi mesh with a FastAPI backend.

## Quick start

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start the backend
uvicorn main:app --host 0.0.0.0 --port 8081

# Start TradingView Desktop with CDP
# macOS: open -a "TradingView" --args --remote-debugging-port=9222
# Windows: see launch_tv_with_cdp.ps1
```

## Architecture

```
TradingView Desktop  ←→  Playwright Controller  ←→  FastAPI Backend  ←→  Sapphire Bridge
         ↑                                                        ↓
    Pine Strategies                                      Dashboard / WebSocket
```

## Key features

- Playwright-based TradingView Desktop automation (symbol, timeframe, indicators)
- Pine Script strategy storage, validation, and deployment
- Watchlist management with venue categorization (ASTER / LIGHTER)
- Community script tester with repaint/lookahead detection
- Webhook signal forwarding to Sapphire with venue routing
- Real-time WebSocket updates

## Tech stack

Python · FastAPI · Playwright · React · Tailscale

## Safety & disclaimers

- **Research/prototype software.** Not financial advice.
- **Paper trading first.** Verify all strategies in paper mode before live execution.
- **Fail-closed by default.** Missing config or failed health checks stop signal flow.
- **No stored credentials.** TradingView Desktop app auth is used; no passwords are kept in config.

## Agent collaborators

See [AGENTS.md](AGENTS.md) for key paths, dev commands, and safety boundaries.
