#!/usr/bin/env python3
"""
TradingView Autonomous Manager - Live Status Dashboard
Real-time monitoring of the autonomous trading system
"""
import urllib.request
import json
import time
import os
from datetime import datetime

BASE_URL = "http://localhost:8081"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def api_call(method, endpoint, data=None):
    """Make API call"""
    url = f"{BASE_URL}{endpoint}"
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

def format_status(connected):
    return "[ONLINE]" if connected else "[OFFLINE]"

def draw_dashboard():
    """Draw the status dashboard"""
    clear_screen()
    
    # Get health data
    health = api_call("GET", "/health")
    
    if "error" in health:
        print("\n" + "="*60)
        print("  ERROR: Cannot connect to API server")
        print("="*60)
        print(f"\n  Error: {health.get('error')}")
        print("\n  Make sure the server is running:")
        print("  uvicorn main:app --host 0.0.0.0 --port 8081")
        return
    
    tv = health.get("tradingview", {})
    sapphire = health.get("sapphire", {})
    data = health.get("data", {})
    config = health.get("config", {})
    
    # Header
    print("\n" + "="*60)
    print(f"  TRADINGVIEW AUTONOMOUS MANAGER - STATUS")
    print("="*60)
    print(f"\n  Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Server: {health.get('status', 'unknown').upper()}")
    print(f"  Version: {health.get('version', 'N/A')}")
    
    # Component Status
    print("\n" + "-"*60)
    print("  COMPONENT STATUS")
    print("-"*60)
    
    print(f"\n  TradingView Desktop  {format_status(tv.get('connected', False))}")
    if tv.get('connected'):
        print(f"    Symbol:     {tv.get('symbol', 'N/A')}")
        print(f"    Timeframe:  {tv.get('timeframe', 'N/A')}")
    else:
        print(f"    To connect: Launch TV with --remote-debugging-port=9222")
    
    print(f"\n  Sapphire Integration {format_status(sapphire.get('connected', False))}")
    print(f"    Webhook: {sapphire.get('url', 'N/A')}")
    if not sapphire.get('connected'):
        print(f"    Status:  Ensure rari2 (100.87.225.89) is online")
    
    # Data Summary
    print("\n" + "-"*60)
    print("  DATA SUMMARY")
    print("-"*60)
    print(f"\n  Strategies:  {data.get('strategies_loaded', 0)}")
    print(f"  Watchlists:  {data.get('watchlists_loaded', 0)}")
    print(f"  Scripts:     {data.get('scripts_loaded', 0)}")
    
    # Configuration
    print("\n" + "-"*60)
    print("  CONFIGURATION")
    print("-"*60)
    print(f"\n  TV Headless: {config.get('tv_headless', 'N/A')}")
    print(f"  TV CDP Port: {config.get('tv_cdp_port', 'N/A')}")
    print(f"  Default Venue: {config.get('sapphire_default_venue', 'N/A')}")
    
    # Quick Actions
    print("\n" + "-"*60)
    print("  QUICK ACTIONS")
    print("-"*60)
    print("\n  API Endpoints:")
    print(f"    Health:     GET  http://100.71.10.48:8081/health")
    print(f"    Connect TV: POST http://100.71.10.48:8081/tv/connect")
    print(f"    Strategies: GET  http://100.71.10.48:8081/strategies")
    print(f"    Watchlists: GET  http://100.71.10.48:8081/watchlists")
    
    # Test Commands
    print("\n  Test Commands (from Mac):")
    print("  # Check health")
    print("  curl http://100.71.10.48:8081/health")
    print("\n  # Connect to TradingView")
    print("  curl -X POST http://100.71.10.48:8081/tv/connect")
    print("\n  # Change symbol")
    print("  curl -X POST http://100.71.10.48:8081/tv/symbol/BTCUSDT")
    print("\n  # List strategies")
    print("  curl http://100.71.10.48:8081/strategies")
    
    print("\n" + "="*60)
    print("  Press Ctrl+C to exit dashboard")
    print("="*60)

def main():
    print("Starting Status Dashboard...")
    print("Press Ctrl+C to exit\n")
    
    try:
        while True:
            draw_dashboard()
            time.sleep(5)  # Update every 5 seconds
    except KeyboardInterrupt:
        print("\n\nDashboard stopped.")

if __name__ == "__main__":
    main()
