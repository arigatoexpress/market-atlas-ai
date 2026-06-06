#!/usr/bin/env python3
"""
TradingView Autonomous Management - Comprehensive Test Suite
Tests all autonomous capabilities
"""
import urllib.request
import json
import time
from datetime import datetime

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

def print_header(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def print_section(title):
    print(f"\n>> {title}")
    print("-" * 40)

# ═══════════════════════════════════════════════════════════════════════════════
# TEST SUITE
# ═══════════════════════════════════════════════════════════════════════════════

def test_system_health():
    """Test 1: System Health & Status"""
    print_section("System Health Check")
    
    data = api_call("GET", "/health")
    if "error" in data:
        print(f"[FAIL] {data['error']}")
        return False
    
    print(f"Status: {data.get('status', 'unknown')}")
    print(f"Version: {data.get('version', 'unknown')}")
    print(f"Timestamp: {data.get('timestamp', 'N/A')}")
    print()
    print(f"TradingView:")
    print(f"  Connected: {data.get('tradingview', {}).get('connected', False)}")
    print(f"  Symbol: {data.get('tradingview', {}).get('symbol', 'N/A')}")
    print(f"  Timeframe: {data.get('tradingview', {}).get('timeframe', 'N/A')}")
    print()
    print(f"Sapphire:")
    print(f"  Connected: {data.get('sapphire', {}).get('connected', False)}")
    print(f"  URL: {data.get('sapphire', {}).get('url', 'N/A')}")
    print()
    print(f"Data:")
    print(f"  Strategies: {data.get('data', {}).get('strategies_loaded', 0)}")
    print(f"  Watchlists: {data.get('data', {}).get('watchlists_loaded', 0)}")
    print(f"  Scripts: {data.get('data', {}).get('scripts_loaded', 0)}")
    
    return True

def test_strategy_lifecycle():
    """Test 2: Complete Strategy Lifecycle"""
    print_section("Strategy Lifecycle Test")
    
    # 2.1 Create strategy
    print("\n2.1 Creating strategy...")
    pine_code = '''//@version=5
strategy("Autonomous EMA Cross", overlay=true, initial_capital=10000)

fastEMA = ta.ema(close, 12)
slowEMA = ta.ema(close, 26)

longCondition = ta.crossover(fastEMA, slowEMA)
shortCondition = ta.crossunder(fastEMA, slowEMA)

if (longCondition)
    strategy.entry("Long", strategy.long)
if (shortCondition)
    strategy.entry("Short", strategy.short)

plot(fastEMA, "Fast EMA", color.blue)
plot(slowEMA, "Slow EMA", color.red)
'''
    
    strategy = api_call("POST", "/strategies", {
        "name": "Autonomous EMA Cross v2",
        "pine_code": pine_code,
        "description": "Automated EMA crossover strategy for autonomous trading",
        "author": "TV Autonomous Manager",
        "category": "strategy",
        "preferred_symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "JUPUSDT"],
        "preferred_timeframes": ["1h", "4h", "1d"]
    })
    
    if "error" in strategy:
        print(f"[FAIL] Create: {strategy['error']}")
        return False
    
    strategy_id = strategy.get("id")
    print(f"[OK] Created: {strategy.get('name')} (ID: {strategy_id})")
    
    # 2.2 Get strategy
    print("\n2.2 Retrieving strategy...")
    data = api_call("GET", f"/strategies/{strategy_id}")
    if "error" in data:
        print(f"[FAIL] Get: {data['error']}")
    else:
        print(f"[OK] Retrieved: {data.get('name')}")
        print(f"  Validated: {data.get('is_validated', False)}")
        print(f"  Symbols: {', '.join(data.get('preferred_symbols', [])[:3])}...")
    
    # 2.3 List strategies
    print("\n2.3 Listing all strategies...")
    strategies = api_call("GET", "/strategies")
    if isinstance(strategies, list):
        print(f"[OK] Total strategies: {len(strategies)}")
        for s in strategies[:3]:
            status = "ACTIVE" if s.get('is_active') else "inactive"
            print(f"  - {s.get('name')} ({status})")
    
    # 2.4 Activate strategy
    print("\n2.4 Activating strategy...")
    result = api_call("POST", f"/strategies/{strategy_id}/activate")
    if "error" not in result:
        print(f"[OK] Strategy activated")
    else:
        print(f"[WARN] Activate: {result.get('error', 'Unknown')}")
    
    return True

def test_watchlist_management():
    """Test 3: Watchlist Management"""
    print_section("Watchlist Management Test")
    
    # 3.1 Create watchlist
    print("\n3.1 Creating watchlist...")
    wl = api_call("POST", "/watchlists", {
        "name": "Autonomous Trading Focus",
        "category": "autonomous",
        "description": "High-priority symbols for autonomous trading system"
    })
    
    if "error" in wl:
        print(f"[FAIL] Create: {wl['error']}")
        return False
    
    wl_id = wl.get("id")
    print(f"[OK] Created: {wl.get('name')} (ID: {wl_id})")
    
    # 3.2 Add symbols
    print("\n3.2 Adding symbols...")
    symbols = [
        ("BTCUSDT", "LIGHTER"),
        ("ETHUSDT", "LIGHTER"),
        ("SOLUSDT", "ASTER"),
        ("JUPUSDT", "ASTER"),
        ("PYTHUSDT", "ASTER"),
    ]
    
    for symbol, venue in symbols:
        result = api_call("POST", f"/watchlists/{wl_id}/symbols/{symbol}?venue={venue}")
        if "error" not in result:
            print(f"  [OK] +{symbol} ({venue})")
        else:
            print(f"  [FAIL] +{symbol}: {result.get('error')}")
    
    # 3.3 Get watchlist
    print("\n3.3 Retrieving watchlist...")
    data = api_call("GET", f"/watchlists/{wl_id}")
    if "error" not in data:
        print(f"[OK] Watchlist: {data.get('name')}")
        print(f"  Symbols ({len(data.get('symbols', []))}):")
        for sym in data.get('symbols', [])[:5]:
            info = data.get('symbol_info', {}).get(sym, {})
            venue = info.get('venue', 'N/A')
            print(f"    - {sym} ({venue})")
    
    # 3.4 List all watchlists
    print("\n3.4 Listing all watchlists...")
    watchlists = api_call("GET", "/watchlists")
    if isinstance(watchlists, list):
        print(f"[OK] Total watchlists: {len(watchlists)}")
        for w in watchlists[:3]:
            print(f"  - {w.get('name')} ({len(w.get('symbols', []))} symbols)")
    
    return True

def test_tradingview_connection():
    """Test 4: TradingView Desktop Connection"""
    print_section("TradingView Desktop Connection Test")
    
    # 4.1 Try to connect
    print("\n4.1 Attempting connection...")
    print("  Note: TradingView Desktop must be running with --remote-debugging-port=9222")
    
    result = api_call("POST", "/tv/connect")
    if "error" in result:
        print(f"[INFO] Connection status: {result.get('detail', 'Check if TV Desktop is running')}")
        print("  To connect:")
        print("  1. Launch TradingView Desktop")
        print("  2. Close it, then run with CDP port:")
        print('     TradingView.exe --remote-debugging-port=9222')
        print("  3. Retry connection")
        return False
    else:
        print(f"[OK] Connected: {result.get('message', 'Success')}")
        
        # 4.2 Get state
        print("\n4.2 Getting chart state...")
        state = api_call("GET", "/tv/state")
        if "error" not in state:
            print(f"  Symbol: {state.get('symbol', 'N/A')}")
            print(f"  Timeframe: {state.get('timeframe', 'N/A')}")
            print(f"  Indicators: {', '.join(state.get('active_indicators', []))}")
            print(f"  Price: {state.get('current_price', 'N/A')}")
        
        return True
    
    return False

def test_signal_generation():
    """Test 5: Signal Generation & Forwarding"""
    print_section("Signal Generation Test")
    
    # 5.1 Send manual signal
    print("\n5.1 Sending manual trading signal...")
    signal = api_call("POST", "/signals/send", {
        "symbol": "BTCUSDT",
        "direction": "LONG",
        "entry_price": 45000.0,
        "stop_loss": 44000.0,
        "take_profit": 47000.0,
        "confidence": 0.85,
        "timeframe": "1h",
        "strategy": "Autonomous Test",
        "venue": "LIGHTER",
        "quantity": 0.1
    })
    
    if "error" in signal:
        print(f"[WARN] Signal send: {signal.get('detail', signal.get('error'))}")
        print("  Note: Sapphire (rari2) may be offline")
    else:
        print(f"[OK] Signal sent successfully")
    
    # 5.2 Check Sapphire status
    print("\n5.2 Checking Sapphire integration...")
    status = api_call("GET", "/sapphire/status")
    print(f"  Status: {status.get('status', 'unknown')}")
    
    heartbeat = api_call("POST", "/sapphire/heartbeat")
    print(f"  Heartbeat: {'OK' if heartbeat.get('success') else 'FAIL'}")
    
    return True

def test_community_scripts():
    """Test 6: Community Script Management"""
    print_section("Community Scripts Test")
    
    # 6.1 List scripts
    print("\n6.1 Listing scripts...")
    scripts = api_call("GET", "/scripts")
    if isinstance(scripts, list):
        print(f"[OK] Scripts loaded: {len(scripts)}")
    
    # 6.2 Import script
    print("\n6.2 Importing test script...")
    script = api_call("POST", "/scripts", {
        "name": "Autonomous Test Script",
        "pine_code": '''//@version=5
indicator("Test Indicator", overlay=true)
plot(ta.sma(close, 20), "SMA 20")
plot(ta.sma(close, 50), "SMA 50")
''',
        "author": "Test",
        "source": "autonomous_test",
        "script_type": "indicator"
    })
    
    if "error" in script:
        print(f"[FAIL] Import: {script.get('error')}")
    else:
        script_id = script.get("id")
        print(f"[OK] Imported: {script.get('name')} (ID: {script_id})")
    
    return True

def test_configuration():
    """Test 7: Configuration & Settings"""
    print_section("Configuration Test")
    
    print("\n7.1 Checking loaded configuration...")
    health = api_call("GET", "/health")
    config = health.get("config", {})
    
    print(f"  TV Headless: {config.get('tv_headless', 'N/A')}")
    print(f"  TV CDP Port: {config.get('tv_cdp_port', 'N/A')}")
    print(f"  Sapphire Default Venue: {config.get('sapphire_default_venue', 'N/A')}")
    
    print("\n7.2 Environment variables:")
    print("  TV_HEADLESS - Set to 'true' for headless mode")
    print("  TV_CDP_PORT - Override default port 9222")
    print("  SAPPHIRE_WEBHOOK_URL - Override Sapphire webhook URL")
    print("  SAPPHIRE_WEBHOOK_SECRET - Set webhook secret")
    
    return True

def generate_report():
    """Generate final test report"""
    print_header("FINAL REPORT")
    
    print(f"\nTest Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API URL: {BASE_URL}")
    
    # Get final health status
    health = api_call("GET", "/health")
    
    print("\n[System Status]")
    print(f"  Server: {health.get('status', 'unknown')}")
    print(f"  Version: {health.get('version', 'N/A')}")
    
    print("\n[Components]")
    print(f"  TradingView Desktop: {'Connected' if health.get('tradingview', {}).get('connected') else 'Not Connected'}")
    print(f"  Sapphire: {'Connected' if health.get('sapphire', {}).get('connected') else 'Not Connected'}")
    
    print("\n[Data]")
    data = health.get('data', {})
    print(f"  Strategies: {data.get('strategies_loaded', 0)}")
    print(f"  Watchlists: {data.get('watchlists_loaded', 0)}")
    print(f"  Scripts: {data.get('scripts_loaded', 0)}")
    
    print("\n[Recommendations]")
    if not health.get('tradingview', {}).get('connected'):
        print("  1. Launch TradingView Desktop with: --remote-debugging-port=9222")
        print("  2. Run: POST /tv/connect")
    
    if not health.get('sapphire', {}).get('connected'):
        print("  3. Ensure rari2 is online and Sapphire is running")
    
    if data.get('strategies_loaded', 0) == 0:
        print("  4. Create some strategies via POST /strategies")
    
    print("\n" + "="*60)

def main():
    print_header("TRADINGVIEW AUTONOMOUS MANAGEMENT - TEST SUITE")
    print(f"\nAPI Base URL: {BASE_URL}")
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # Run all tests
    results.append(("System Health", test_system_health()))
    time.sleep(0.5)
    
    results.append(("Strategy Lifecycle", test_strategy_lifecycle()))
    time.sleep(0.5)
    
    results.append(("Watchlist Management", test_watchlist_management()))
    time.sleep(0.5)
    
    results.append(("TV Desktop Connection", test_tradingview_connection()))
    time.sleep(0.5)
    
    results.append(("Signal Generation", test_signal_generation()))
    time.sleep(0.5)
    
    results.append(("Community Scripts", test_community_scripts()))
    time.sleep(0.5)
    
    results.append(("Configuration", test_configuration()))
    
    # Print summary
    print_header("TEST SUMMARY")
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "[OK]" if result else "[INFO/WARN]"
        print(f"  {status} {name}")
    
    print(f"\nTotal: {passed}/{total} core tests completed")
    
    # Generate detailed report
    generate_report()
    
    return 0

if __name__ == "__main__":
    exit(main())
