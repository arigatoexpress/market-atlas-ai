#!/usr/bin/env python3
"""
Interactive TradingView Autonomous Testing
"""
import urllib.request
import json
import time

BASE_URL = "http://localhost:8081"

def api_call(method, endpoint, data=None):
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

def test_symbol_change():
    """Test changing symbols"""
    print("\n[TEST] Changing Symbols")
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    
    for symbol in symbols:
        print(f"  Setting symbol to {symbol}...", end=" ")
        result = api_call("POST", f"/tv/symbol/{symbol}")
        if "error" in result:
            print(f"FAILED: {result['error']}")
        else:
            print("OK")
        time.sleep(1)

def test_timeframe_change():
    """Test changing timeframes"""
    print("\n[TEST] Changing Timeframes")
    timeframes = ["15m", "1h", "4h", "1d"]
    
    for tf in timeframes:
        print(f"  Setting timeframe to {tf}...", end=" ")
        result = api_call("POST", f"/tv/timeframe/{tf}")
        if "error" in result:
            print(f"FAILED: {result['error']}")
        else:
            print("OK")
        time.sleep(1)

def test_indicators():
    """Test adding indicators"""
    print("\n[TEST] Adding Indicators")
    indicators = ["RSI", "MACD", "EMA"]
    
    for ind in indicators:
        print(f"  Adding {ind}...", end=" ")
        result = api_call("POST", f"/tv/indicator/{ind}")
        if "error" in result:
            print(f"FAILED: {result['error']}")
        else:
            print("OK")
        time.sleep(1)

def test_screenshot():
    """Test screenshot capture"""
    print("\n[TEST] Screenshot Capture")
    print("  Capturing chart screenshot...", end=" ")
    result = api_call("POST", "/tv/screenshot")
    if "error" in result:
        print(f"FAILED: {result['error']}")
    else:
        screenshot = result.get('screenshot', '')
        size = len(screenshot)
        print(f"OK (size: {size} chars)")

def test_signal():
    """Test sending a signal"""
    print("\n[TEST] Send Trading Signal")
    signal = {
        "symbol": "BTCUSDT",
        "direction": "LONG",
        "entry_price": 45000,
        "stop_loss": 44000,
        "take_profit": 47000,
        "confidence": 0.85,
        "timeframe": "1h",
        "strategy": "Test Strategy",
        "venue": "LIGHTER",
        "quantity": 0.1
    }
    
    print(f"  Sending LONG signal for BTCUSDT...", end=" ")
    result = api_call("POST", "/signals/send", signal)
    if "error" in result:
        print(f"FAILED: {result['error']}")
    else:
        print("OK")

def menu():
    """Show interactive menu"""
    print("\n" + "="*60)
    print("  TRADINGVIEW AUTONOMOUS - INTERACTIVE TESTING")
    print("="*60)
    print("\nAvailable Tests:")
    print("  1. Connect to TradingView Desktop")
    print("  2. Change Symbols (BTC, ETH, SOL)")
    print("  3. Change Timeframes (15m, 1h, 4h, 1d)")
    print("  4. Add Indicators (RSI, MACD, EMA)")
    print("  5. Capture Screenshot")
    print("  6. Send Test Signal")
    print("  7. Run All Tests")
    print("  8. Show Current State")
    print("  0. Exit")

def main():
    while True:
        menu()
        choice = input("\nEnter choice: ").strip()
        
        if choice == "1":
            print("\n[Connecting to TradingView Desktop...]")
            result = api_call("POST", "/tv/connect")
            if "error" in result:
                print(f"  FAILED: {result['error']}")
                print("  Make sure TradingView Desktop is running with --remote-debugging-port=9222")
            else:
                print(f"  SUCCESS: {result.get('message')}")
        
        elif choice == "2":
            test_symbol_change()
        
        elif choice == "3":
            test_timeframe_change()
        
        elif choice == "4":
            test_indicators()
        
        elif choice == "5":
            test_screenshot()
        
        elif choice == "6":
            test_signal()
        
        elif choice == "7":
            print("\n" + "="*60)
            print("  RUNNING ALL TESTS")
            print("="*60)
            test_symbol_change()
            test_timeframe_change()
            test_indicators()
            test_screenshot()
            test_signal()
            print("\n" + "="*60)
            print("  ALL TESTS COMPLETE")
            print("="*60)
        
        elif choice == "8":
            result = api_call("GET", "/tv/state")
            if "error" in result:
                print(f"\n  Cannot get state: {result['error']}")
            else:
                print("\n  Current State:")
                print(f"    Symbol: {result.get('symbol')}")
                print(f"    Timeframe: {result.get('timeframe')}")
                print(f"    Indicators: {result.get('active_indicators')}")
                print(f"    Price: {result.get('current_price')}")
        
        elif choice == "0":
            print("\nExiting...")
            break
        
        else:
            print("\nInvalid choice!")

if __name__ == "__main__":
    main()
