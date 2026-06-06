#!/usr/bin/env python3
"""
Comprehensive System Test for TradingView Autonomous Manager
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
    except Exception as e:
        return {"error": str(e)}

def test_health():
    """Test health endpoint"""
    print("\n[TEST] Health Endpoint")
    data = api_call("GET", "/health")
    
    if "error" in data:
        print(f"  FAIL: {data['error']}")
        return False
    
    print(f"  Status: {data.get('status', 'unknown')}")
    print(f"  Version: {data.get('version', 'unknown')}")
    print(f"  TV Connected: {data.get('tradingview', {}).get('connected', False)}")
    print(f"  Sapphire Connected: {data.get('sapphire', {}).get('connected', False)}")
    print(f"  Strategies: {data.get('data', {}).get('strategies_loaded', 0)}")
    print(f"  Watchlists: {data.get('data', {}).get('watchlists_loaded', 0)}")
    return True

def test_strategies():
    """Test strategy endpoints"""
    print("\n[TEST] Strategy Management")
    
    # List strategies
    data = api_call("GET", "/strategies")
    if "error" in data:
        print(f"  List FAIL: {data['error']}")
        return False
    
    print(f"  Listed {len(data)} strategies")
    
    # Create strategy
    new_strategy = api_call("POST", "/strategies", {
        "name": "Automated Test Strategy",
        "pine_code": "//@version=5\nstrategy(\"Test\")\nplot(close)",
        "description": "Created by system test",
        "author": "System Test",
        "category": "strategy"
    })
    
    if "error" in new_strategy:
        print(f"  Create FAIL: {new_strategy['error']}")
        return False
    
    strategy_id = new_strategy.get("id")
    print(f"  Created strategy: {new_strategy.get('name')} ({strategy_id})")
    
    # Get specific strategy
    data = api_call("GET", f"/strategies/{strategy_id}")
    if "error" in data:
        print(f"  Get FAIL: {data['error']}")
        return False
    
    print(f"  Retrieved strategy: {data.get('name')}")
    return True

def test_watchlists():
    """Test watchlist endpoints"""
    print("\n[TEST] Watchlist Management")
    
    # List watchlists
    data = api_call("GET", "/watchlists")
    if "error" in data:
        print(f"  List FAIL: {data['error']}")
        return False
    
    print(f"  Listed {len(data)} watchlists")
    
    # Create watchlist
    new_wl = api_call("POST", "/watchlists", {
        "name": "Test Watchlist",
        "category": "test",
        "description": "Created by system test"
    })
    
    if "error" in new_wl:
        print(f"  Create FAIL: {new_wl['error']}")
        return False
    
    wl_id = new_wl.get("id")
    print(f"  Created watchlist: {new_wl.get('name')} ({wl_id})")
    
    # Add symbol
    data = api_call("POST", f"/watchlists/{wl_id}/symbols/BTCUSDT", {"venue": "LIGHTER"})
    if "error" in data:
        print(f"  Add Symbol FAIL: {data['error']}")
    else:
        print(f"  Added BTCUSDT to watchlist")
    
    return True

def test_scripts():
    """Test community script endpoints"""
    print("\n[TEST] Community Scripts")
    
    data = api_call("GET", "/scripts")
    if "error" in data:
        print(f"  List FAIL: {data['error']}")
        return False
    
    print(f"  Listed {len(data)} scripts")
    return True

def test_sapphire():
    """Test sapphire integration"""
    print("\n[TEST] Sapphire Integration")
    
    data = api_call("GET", "/sapphire/status")
    print(f"  Status: {data.get('status', 'unknown')}")
    
    data = api_call("POST", "/sapphire/heartbeat")
    print(f"  Heartbeat: {data.get('success', False)}")
    
    return True

def test_tv_control():
    """Test TradingView control (without actual connection)"""
    print("\n[TEST] TradingView Control (No Connection)")
    
    # Try to connect (will fail without TV running, but tests endpoint)
    data = api_call("POST", "/tv/connect")
    if "error" in data:
        print(f"  Connect (expected failure): {data.get('detail', 'No detail')}")
    else:
        print(f"  Connected: {data.get('status')}")
    
    # Try to get state
    data = api_call("GET", "/tv/state")
    if "error" in data:
        print(f"  Get State (expected failure): {data.get('detail', 'No detail')[:50]}")
    else:
        print(f"  State: {data.get('symbol')}")
    
    return True

def main():
    print("="*60)
    print("TRADINGVIEW AUTONOMOUS MANAGER - SYSTEM TEST")
    print("="*60)
    print(f"\nBase URL: {BASE_URL}")
    
    results = []
    
    results.append(("Health", test_health()))
    results.append(("Strategies", test_strategies()))
    results.append(("Watchlists", test_watchlists()))
    results.append(("Scripts", test_scripts()))
    results.append(("Sapphire", test_sapphire()))
    results.append(("TV Control", test_tv_control()))
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  [{status}] {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[OK] All tests passed!")
        return 0
    else:
        print(f"\n[WARN] {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
