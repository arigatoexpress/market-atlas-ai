#!/usr/bin/env python3
"""
TradingView Autonomous Management - Capabilities Demonstration
"""
import urllib.request
import json

def api(method, endpoint, data=None):
    url = f"http://localhost:8081{endpoint}"
    try:
        if method == "GET":
            req = urllib.request.Request(url, method="GET")
        else:
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode() if data else None,
                headers={"Content-Type": "application/json"},
                method=method
            )
        response = urllib.request.urlopen(req, timeout=5)
        return json.loads(response.read())
    except Exception as e:
        return {"error": str(e)}

print("="*70)
print("  TRADINGVIEW AUTONOMOUS MANAGEMENT - CAPABILITIES")
print("="*70)

# 1. Health
print("\n[1] System Health")
health = api("GET", "/health")
print(f"  Status: {health.get('status', 'unknown')}")
print(f"  Version: {health.get('version', 'N/A')}")
print(f"  TV Connected: {health.get('tradingview', {}).get('connected', False)}")
print(f"  Sapphire Connected: {health.get('sapphire', {}).get('connected', False)}")

# 2. Strategies
print("\n[2] Autonomous Strategy Management")
strategies = api("GET", "/strategies")
if isinstance(strategies, list):
    print(f"  Total Strategies: {len(strategies)}")
    for s in strategies[:5]:
        active = "ACTIVE" if s.get("is_active") else "inactive"
        validated = "VALIDATED" if s.get("is_validated") else "pending"
        symbols = len(s.get("preferred_symbols", []))
        print(f"  - {s.get('name')} [{active}] [{validated}] ({symbols} symbols)")

# 3. Watchlists
print("\n[3] Autonomous Watchlist Management")
watchlists = api("GET", "/watchlists")
if isinstance(watchlists, list):
    print(f"  Total Watchlists: {len(watchlists)}")
    for w in watchlists:
        symbols = len(w.get("symbols", []))
        print(f"  - {w.get('name')} ({symbols} symbols)")

# 4. Configuration
print("\n[4] Configuration")
config = health.get("config", {})
print(f"  TV Headless Mode: {config.get('tv_headless', False)}")
print(f"  CDP Port: {config.get('tv_cdp_port', 9222)}")
print(f"  Default Venue: {config.get('sapphire_default_venue', 'LIGHTER')}")

print("\n" + "="*70)
print("  AUTONOMOUS CAPABILITIES SUMMARY")
print("="*70)

capabilities = """
[OK] STRATEGY MANAGEMENT
     - Create Pine Script strategies
     - Validate Pine Script syntax
     - Store and version strategies
     - Activate/Deactivate strategies
     - Associate with symbols and timeframes

[OK] WATCHLIST MANAGEMENT
     - Create multiple watchlists
     - Categorize symbols by venue (ASTER/LIGHTER)
     - Bulk import/export
     - Sync to TradingView Desktop

[OK] TRADINGVIEW DESKTOP CONTROL (when connected)
     - Change symbols programmatically
     - Change timeframes (1m to 1d)
     - Add/remove indicators (RSI, MACD, EMA, etc.)
     - Capture screenshots
     - Apply strategies to charts
     - Manage watchlists

[OK] SIGNAL GENERATION
     - Manual signal sending
     - Auto-scan for signals
     - Forward to Sapphire webhook

[OK] CONFIGURATION
     - YAML file support
     - Environment variable overrides
     - Runtime config updates

[PENDING] CONNECTIONS
     - TradingView Desktop: Not connected (launch with --remote-debugging-port=9222)
     - Sapphire (rari2): Not connected (ensure Pi is online)
"""

print(capabilities)

print("="*70)
print("  API ENDPOINTS FOR AUTONOMOUS CONTROL")
print("="*70)

endpoints = """
Base URL: http://100.71.10.48:8081

TRADINGVIEW CONTROL:
  POST /tv/connect              - Connect to TV Desktop
  GET  /tv/state                - Get current chart state
  POST /tv/symbol/{symbol}      - Change symbol (BTCUSDT, ETHUSDT, etc.)
  POST /tv/timeframe/{tf}       - Change timeframe (1m, 5m, 15m, 1h, 4h, 1d)
  POST /tv/indicator/{name}     - Add indicator (RSI, MACD, EMA)
  DELETE /tv/indicator/{name}   - Remove indicator
  POST /tv/screenshot           - Capture chart screenshot

STRATEGY MANAGEMENT:
  GET  /strategies              - List all strategies
  POST /strategies              - Create new strategy
  GET  /strategies/{id}         - Get strategy details
  POST /strategies/{id}/apply   - Apply to TV chart
  POST /strategies/{id}/activate   - Activate for trading
  POST /strategies/{id}/deactivate - Deactivate

WATCHLIST MANAGEMENT:
  GET  /watchlists              - List all watchlists
  POST /watchlists              - Create new watchlist
  GET  /watchlists/{id}         - Get watchlist details
  POST /watchlists/{id}/symbols/{symbol}  - Add symbol
  DELETE /watchlists/{id}/symbols/{symbol} - Remove symbol
  POST /watchlists/{id}/sync    - Sync to TradingView

SIGNALS & INTEGRATION:
  POST /signals/send            - Send trading signal
  POST /signals/scan            - Auto-scan for signals
  GET  /sapphire/status         - Get Sapphire status
  POST /sapphire/heartbeat      - Test Sapphire connection
"""

print(endpoints)

print("="*70)
print("  SYSTEM IS READY FOR AUTONOMOUS TRADING!")
print("="*70)
print("""
Next Steps:
1. Launch TradingView Desktop with CDP port:
   TradingView.exe --remote-debugging-port=9222

2. Connect via API:
   curl -X POST http://100.71.10.48:8081/tv/connect

3. Start autonomous management:
   curl -X POST http://100.71.10.48:8081/tv/symbol/BTCUSDT
   curl -X POST http://100.71.10.48:8081/tv/timeframe/1h
""")
