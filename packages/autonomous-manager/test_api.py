#!/usr/bin/env python3
"""
TradingView Autonomous Manager - Comprehensive Test Suite
"""
import urllib.request
import json
import sys

BASE_URL = "http://localhost:8081"

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
        response = urllib.request.urlopen(req, timeout=10)
        return json.loads(response.read())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

def test_health():
    """Test 1: Health Check"""
    print_section("TEST 1: Health Status")
    health = api_call("GET", "/health")
    
    if "error" in health:
        print(f"  [FAIL] Error: {health['error']}")
        return False
    
    print(f"  Status: {health.get('status', 'unknown')}")
    print(f"  TV Connected: {health.get('tv_connected', False)}")
    print(f"  Sapphire URL: {health.get('sapphire_url', 'N/A')}")
    print(f"  Strategies Loaded: {health.get('strategies_loaded', 0)}")
    print(f"  Watchlists Loaded: {health.get('watchlists_loaded', 0)}")
    print(f"  Scripts Loaded: {health.get('scripts_loaded', 0)}")
    return True

def test_watchlists():
    """Test 2: Watchlists"""
    print_section("TEST 2: Watchlists")
    watchlists = api_call("GET", "/watchlists")
    
    if "error" in watchlists:
        print(f"  [FAIL] Error: {watchlists['error']}")
        return False
    
    if isinstance(watchlists, list):
        print(f"  Found {len(watchlists)} watchlist(s)")
        for w in watchlists:
            name = w.get('name', 'Unnamed')
            symbols = len(w.get('symbols', []))
            category = w.get('category', 'N/A')
            print(f"    - {name} ({symbols} symbols) [{category}]")
    return True

def test_strategies():
    """Test 3: Strategies"""
    print_section("TEST 3: Strategies")
    strategies = api_call("GET", "/strategies")
    
    if "error" in strategies:
        print(f"  [FAIL] Error: {strategies['error']}")
        return False
    
    if isinstance(strategies, list):
        print(f"  Found {len(strategies)} strategy(ies)")
        for s in strategies:
            name = s.get('name', 'Unnamed')
            category = s.get('category', 'N/A')
            active = 'ACTIVE' if s.get('is_active') else 'inactive'
            print(f"    - {name} [{category}] ({active})")
    return True

def test_scripts():
    """Test 4: Community Scripts"""
    print_section("TEST 4: Community Scripts")
    scripts = api_call("GET", "/scripts")
    
    if "error" in scripts:
        print(f"  [FAIL] Error: {scripts['error']}")
        return False
    
    if isinstance(scripts, list):
        print(f"  Found {len(scripts)} script(s)")
        for s in scripts:
            name = s.get('name', 'Unnamed')
            approved = 'APPROVED' if s.get('is_approved') else 'pending'
            print(f"    - {name} ({approved})")
    return True

def test_sapphire():
    """Test 5: Sapphire Connection"""
    print_section("TEST 5: Sapphire Integration")
    
    # Test status endpoint
    status = api_call("GET", "/sapphire/status")
    print(f"  Status Response: {status}")
    
    # Test heartbeat
    heartbeat = api_call("POST", "/sapphire/heartbeat")
    print(f"  Heartbeat Response: {heartbeat}")
    return True

def test_create_strategy():
    """Test 6: Create a sample strategy"""
    print_section("TEST 6: Create Sample Strategy")
    
    pine_code = '''//@version=5
strategy("Sapphire Auto Strategy", overlay=true)

// Inputs
fastLength = input.int(12, "Fast EMA Length")
slowLength = input.int(26, "Slow EMA Length")

// Calculations
fastEMA = ta.ema(close, fastLength)
slowEMA = ta.ema(close, slowLength)

// Signals
longCondition = ta.crossover(fastEMA, slowEMA)
shortCondition = ta.crossunder(fastEMA, slowEMA)

// Execute
if (longCondition)
    strategy.entry("Long", strategy.long)
if (shortCondition)
    strategy.entry("Short", strategy.short)

// Plot
plot(fastEMA, "Fast EMA", color.blue)
plot(slowEMA, "Slow EMA", color.red)
'''
    
    data = {
        "name": "Sapphire EMA Crossover",
        "pine_code": pine_code,
        "description": "Automated EMA crossover strategy for Sapphire",
        "author": "TV Autonomous Manager",
        "category": "strategy",
        "preferred_symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        "preferred_timeframes": ["1h", "4h"]
    }
    
    result = api_call("POST", "/strategies", data)
    if "error" in result:
        print(f"  [FAIL] Error: {result['error']}")
        return False
    
    print(f"  [OK] Created strategy: {result.get('name')}")
    print(f"     ID: {result.get('id')}")
    return True

def test_create_watchlist():
    """Test 7: Create a watchlist"""
    print_section("TEST 7: Create Sample Watchlist")
    
    data = {
        "name": "Sapphire Focus List",
        "category": "sapphire",
        "description": "High-priority symbols for Sapphire trading"
    }
    
    result = api_call("POST", "/watchlists", data)
    if "error" in result:
        print(f"  [FAIL] Error: {result['error']}")
        return False
    
    watchlist_id = result.get('id')
    print(f"  [OK] Created watchlist: {result.get('name')}")
    print(f"     ID: {watchlist_id}")
    
    # Add symbols
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "JUPUSDT", "PYTHUSDT"]
    for symbol in symbols:
        add_result = api_call("POST", f"/watchlists/{watchlist_id}/symbols/{symbol}")
        if "error" not in add_result:
            print(f"    + Added {symbol}")
    
    return True

def test_tv_connect():
    """Test 8: TradingView Desktop Connection"""
    print_section("TEST 8: TradingView Desktop Connection")
    print("  Attempting to connect to TradingView Desktop...")
    
    result = api_call("POST", "/tv/connect")
    if "error" in result:
        print(f"  [WARN]  Connection issue: {result['error']}")
        print("  [INFO]  Make sure TradingView Desktop is running")
        print("  [INFO]  Launch with: --remote-debugging-port=9222")
        return False
    
    print(f"  [OK] {result.get('message', 'Connected')}")
    return True

def main():
    print("\n" + "="*60)
    print("  TRADINGVIEW AUTONOMOUS MANAGER - TEST SUITE")
    print("="*60)
    print(f"\n  Base URL: {BASE_URL}")
    
    results = []
    
    # Run tests
    results.append(("Health", test_health()))
    results.append(("Watchlists", test_watchlists()))
    results.append(("Strategies", test_strategies()))
    results.append(("Scripts", test_scripts()))
    results.append(("Sapphire", test_sapphire()))
    results.append(("Create Strategy", test_create_strategy()))
    results.append(("Create Watchlist", test_create_watchlist()))
    results.append(("TV Connect", test_tv_connect()))
    
    # Summary
    print_section("TEST SUMMARY")
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "[OK] PASS" if result else "[FAIL] FAIL"
        print(f"  {status} - {name}")
    
    print(f"\n  Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n  [SUCCESS] All tests passed!")
    else:
        print("\n  [WARN]  Some tests failed. Check the details above.")

if __name__ == "__main__":
    main()
