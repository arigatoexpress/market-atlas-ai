#!/usr/bin/env python3
"""
TradingView Desktop Connection Helper
"""
import subprocess
import os
import sys
import urllib.request
import json
import time

def check_tv_installed():
    """Check if TradingView Desktop is installed"""
    tv_path = os.path.expandvars(r"C:\Users\%USERNAME%\AppData\Local\Programs\TradingView\TradingView.exe")
    tv_path = tv_path.replace("%USERNAME%", os.getenv("USERNAME"))
    
    if os.path.exists(tv_path):
        return tv_path
    
    # Try alternative paths
    alt_paths = [
        r"C:\Program Files\TradingView\TradingView.exe",
        r"C:\Program Files (x86)\TradingView\TradingView.exe",
    ]
    
    for path in alt_paths:
        if os.path.exists(path):
            return path
    
    return None

def is_tv_running():
    """Check if TradingView is running"""
    try:
        result = subprocess.run(
            ['tasklist', '/FI', 'IMAGENAME eq TradingView.exe'],
            capture_output=True, text=True
        )
        return 'TradingView.exe' in result.stdout
    except:
        return False

def launch_tv_with_cdp(tv_path):
    """Launch TradingView with Chrome DevTools Protocol"""
    print(f"Launching TradingView with CDP port 9222...")
    print(f"Path: {tv_path}")
    
    try:
        # Launch in background
        subprocess.Popen(
            [tv_path, '--remote-debugging-port=9222'],
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        print("[OK] TradingView launched!")
        print("[INFO] Wait 5-10 seconds for it to fully load...")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to launch: {e}")
        return False

def test_connection():
    """Test API connection"""
    try:
        response = urllib.request.urlopen(
            'http://localhost:8081/tv/connect',
            timeout=30
        )
        data = json.loads(response.read())
        return data.get('status') == 'connected'
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return False

def main():
    print("="*60)
    print("  TRADINGVIEW DESKTOP CONNECTION HELPER")
    print("="*60)
    
    # Step 1: Check if TV is installed
    print("\n[Step 1] Checking TradingView Desktop installation...")
    tv_path = check_tv_installed()
    
    if tv_path:
        print(f"[OK] Found TradingView at: {tv_path}")
    else:
        print("[ERROR] TradingView Desktop not found!")
        print("[INFO] Please install TradingView Desktop from:")
        print("       https://www.tradingview.com/desktop/")
        return
    
    # Step 2: Check if running
    print("\n[Step 2] Checking if TradingView is running...")
    if is_tv_running():
        print("[OK] TradingView is currently running")
        print("[WARN] If not launched with --remote-debugging-port=9222,")
        print("       please close and restart it properly.")
        
        choice = input("\nRestart with CDP port? (y/n): ").lower()
        if choice == 'y':
            # Kill existing process
            subprocess.run(['taskkill', '/F', '/IM', 'TradingView.exe'], 
                         capture_output=True)
            time.sleep(2)
            launch_tv_with_cdp(tv_path)
    else:
        print("[INFO] TradingView not running")
        launch_tv_with_cdp(tv_path)
    
    # Step 3: Wait and connect
    print("\n[Step 3] Waiting for TradingView to initialize...")
    for i in range(10, 0, -1):
        print(f"  {i} seconds...", end='\r')
        time.sleep(1)
    print()
    
    # Step 4: Test connection
    print("\n[Step 4] Testing API connection...")
    print("  Sending connect request...")
    
    if test_connection():
        print("[OK] Successfully connected to TradingView Desktop!")
        
        # Get state
        print("\n[Step 5] Getting current state...")
        try:
            response = urllib.request.urlopen(
                'http://localhost:8081/tv/state', timeout=10
            )
            state = json.loads(response.read())
            print(f"  Symbol: {state.get('symbol', 'N/A')}")
            print(f"  Timeframe: {state.get('timeframe', 'N/A')}")
            print(f"  Chart Loaded: {state.get('is_chart_loaded', False)}")
        except Exception as e:
            print(f"  Could not get state: {e}")
        
        print("\n" + "="*60)
        print("  [SUCCESS] TradingView Desktop is now connected!")
        print("="*60)
        print("\nYou can now:")
        print("  - Change symbols: POST /tv/symbol/BTCUSDT")
        print("  - Change timeframes: POST /tv/timeframe/1h")
        print("  - Add indicators: POST /tv/indicator/RSI")
        print("  - Take screenshots: POST /tv/screenshot")
        
    else:
        print("\n[ERROR] Could not connect!")
        print("\nTroubleshooting:")
        print("  1. Ensure TradingView Desktop is fully loaded")
        print("  2. Check if port 9222 is accessible:")
        print("     netstat -ano | findstr 9222")
        print("  3. Try restarting TradingView Desktop")
        print("  4. Check Windows Defender/Firewall settings")

if __name__ == "__main__":
    main()
