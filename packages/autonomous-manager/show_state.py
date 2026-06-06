#!/usr/bin/env python3
"""Show current state of TradingView Autonomous Manager"""
import urllib.request
import json

def api_get(endpoint):
    url = f"http://localhost:8081{endpoint}"
    try:
        response = urllib.request.urlopen(url, timeout=10)
        return json.loads(response.read())
    except Exception as e:
        return {"error": str(e)}

print("="*60)
print("  TRADINGVIEW AUTONOMOUS MANAGER - CURRENT STATE")
print("="*60)

# Health
print("\n[HEALTH]")
health = api_get("/health")
print(f"  Server: {health.get('status', 'unknown')}")
print(f"  TV Connected: {health.get('tv_connected', False)}")
print(f"  Sapphire: {health.get('sapphire_url', 'N/A')}")

# Strategies
print("\n[STRATEGIES]")
strategies = api_get("/strategies")
if isinstance(strategies, list):
    for s in strategies:
        print(f"  - {s.get('name')} [{s.get('id')[:8]}...]")
        print(f"    Active: {s.get('is_active')}")
        symbols = s.get('preferred_symbols', [])
        print(f"    Symbols: {', '.join(symbols) if symbols else 'None'}")

# Watchlists
print("\n[WATCHLISTS]")
watchlists = api_get("/watchlists")
if isinstance(watchlists, list):
    for w in watchlists:
        print(f"  - {w.get('name')} [{w.get('id')[:8]}...]")
        symbols = w.get('symbols', [])
        print(f"    Symbols ({len(symbols)}): {', '.join(symbols[:5])}{'...' if len(symbols) > 5 else ''}")

# Scripts
print("\n[COMMUNITY SCRIPTS]")
scripts = api_get("/scripts")
if isinstance(scripts, list):
    if scripts:
        for sc in scripts:
            print(f"  - {sc.get('name')} (Approved: {sc.get('is_approved', False)})")
    else:
        print("  No scripts loaded")

print("\n" + "="*60)
print("  API URL: http://100.71.10.48:8081")
print("="*60)
