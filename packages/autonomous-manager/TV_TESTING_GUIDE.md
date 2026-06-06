# TradingView Desktop Autonomous Testing Guide

## Current Status
- ✅ Server running on http://localhost:8081
- ✅ Windows Firewall: Port 8081 open
- ✅ 1 watchlist loaded (Forex Majors)
- ⚠️ TradingView Desktop: Not connected
- ⚠️ Sapphire (rari2): Not connected

---

## Phase 1: TradingView Desktop Connection

### Step 1: Launch TradingView Desktop with Debug Port

**Option A: Command Line (Recommended)**
```powershell
# Close TradingView Desktop if running
# Then launch with CDP port:
& "C:\Users\$env:USERNAME\AppData\Local\Programs\TradingView\TradingView.exe" --remote-debugging-port=9222
```

**Option B: Check if already running with CDP**
```powershell
# Check if TradingView is listening on port 9222
netstat -ano | findstr 9222
```

### Step 2: Connect via API

**Test from your Mac:**
```bash
# Connect to TradingView Desktop
curl -X POST http://100.71.10.48:8081/tv/connect

# Expected response:
# {"status": "connected", "message": "TradingView Desktop connected"}
```

**Or from Windows PowerShell:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8081/tv/connect" -Method POST
```

### Step 3: Verify Connection

```bash
# Check TV state
curl http://100.71.10.48:8081/tv/state

# Expected response:
# {
#   "symbol": "BTCUSDT",
#   "timeframe": "1h",
#   "active_indicators": [...],
#   "is_chart_loaded": true,
#   ...
# }
```

---

## Phase 2: TradingView Control Tests

### Test 2.1: Change Symbol

```bash
# Change to BTC
curl -X POST http://100.71.10.48:8081/tv/symbol/BTCUSDT

# Change to ETH
curl -X POST http://100.71.10.48:8081/tv/symbol/ETHUSDT

# Change to SOL
curl -X POST http://100.71.10.48:8081/tv/symbol/SOLUSDT
```

### Test 2.2: Change Timeframe

```bash
# Switch to 1 hour
curl -X POST http://100.71.10.48:8081/tv/timeframe/1h

# Switch to 4 hour
curl -X POST http://100.71.10.48:8081/tv/timeframe/4h

# Switch to 1 day
curl -X POST http://100.71.10.48:8081/tv/timeframe/1d

# Switch to 15 minute
curl -X POST http://100.71.10.48:8081/tv/timeframe/15m
```

### Test 2.3: Add/Remove Indicators

```bash
# Add EMA
curl -X POST http://100.71.10.48:8081/tv/indicator/EMA

# Add RSI
curl -X POST http://100.71.10.48:8081/tv/indicator/RSI

# Add MACD
curl -X POST http://100.71.10.48:8081/tv/indicator/MACD

# Remove an indicator
curl -X DELETE http://100.71.10.48:8081/tv/indicator/RSI
```

### Test 2.4: Capture Screenshot

```bash
# Take chart screenshot
curl -X POST http://100.71.10.48:8081/tv/screenshot

# Response will contain base64 encoded image
```

---

## Phase 3: Strategy Management Tests

### Test 3.1: Create Strategy

```bash
curl -X POST http://100.71.10.48:8081/strategies \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sapphire Momentum",
    "pine_code": "//@version=5\nstrategy(\"Sapphire Momentum\", overlay=true)\n\n// RSI Momentum\nrsi = ta.rsi(close, 14)\n\n// Signals\nlong = ta.crossover(rsi, 50)\nshort = ta.crossunder(rsi, 50)\n\nif (long)\n    strategy.entry(\"Long\", strategy.long)\nif (short)\n    strategy.entry(\"Short\", strategy.short)",
    "description": "RSI-based momentum strategy",
    "author": "Test",
    "category": "strategy",
    "preferred_symbols": ["BTCUSDT", "ETHUSDT"],
    "preferred_timeframes": ["1h", "4h"]
  }'
```

### Test 3.2: List Strategies

```bash
curl http://100.71.10.48:8081/strategies
```

### Test 3.3: Apply Strategy to Chart

```bash
# Get strategy ID from list, then:
curl -X POST http://100.71.10.48:8081/strategies/{strategy_id}/apply
```

### Test 3.4: Activate Strategy

```bash
curl -X POST http://100.71.10.48:8081/strategies/{strategy_id}/activate
```

---

## Phase 4: Watchlist Management Tests

### Test 4.1: Create Watchlist

```bash
curl -X POST http://100.71.10.48:8081/watchlists \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Crypto Perps",
    "category": "crypto",
    "description": "Top crypto perpetuals"
  }'
```

### Test 4.2: Add Symbols

```bash
# Add BTC
curl -X POST http://100.71.10.48:8081/watchlists/{watchlist_id}/symbols/BTCUSDT

# Add ETH
curl -X POST http://100.71.10.48:8081/watchlists/{watchlist_id}/symbols/ETHUSDT

# Add SOL
curl -X POST http://100.71.10.48:8081/watchlists/{watchlist_id}/symbols/SOLUSDT
```

### Test 4.3: Sync to TradingView

```bash
curl -X POST http://100.71.10.48:8081/watchlists/{watchlist_id}/sync
```

---

## Phase 5: Signal Tests

### Test 5.1: Send Manual Signal

```bash
curl -X POST http://100.71.10.48:8081/signals/send \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTCUSDT",
    "direction": "LONG",
    "entry_price": 45000,
    "stop_loss": 44000,
    "take_profit": 47000,
    "confidence": 0.85,
    "timeframe": "1h",
    "strategy": "Sapphire Momentum",
    "venue": "LIGHTER",
    "quantity": 0.1
  }'
```

### Test 5.2: Auto-Scan for Signals

```bash
curl -X POST http://100.71.10.48:8081/signals/scan
```

---

## Phase 6: Community Script Tests

### Test 6.1: Import Script

```bash
curl -X POST http://100.71.10.48:8081/scripts \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Community EMA Cloud",
    "pine_code": "//@version=5\nindicator(\"EMA Cloud\", overlay=true)\n\nema50 = ta.ema(close, 50)\nema200 = ta.ema(close, 200)\n\nfill(plot(ema50), plot(ema200), color=ema50 > ema200 ? color.green : color.red)",
    "author": "Community",
    "source": "TradingView Public",
    "script_type": "indicator"
  }'
```

### Test 6.2: Test Script

```bash
curl -X POST http://100.71.10.48:8081/scripts/{script_id}/test
```

### Test 6.3: Approve Script

```bash
curl -X POST http://100.71.10.48:8081/scripts/{script_id}/approve \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["BTCUSDT", "ETHUSDT"],
    "timeframes": ["1h", "4h"]
  }'
```

---

## Phase 7: Sapphire Integration Tests

### Test 7.1: Check Sapphire Status

```bash
curl http://100.71.10.48:8081/sapphire/status
```

### Test 7.2: Send Heartbeat

```bash
curl -X POST http://100.71.10.48:8081/sapphire/heartbeat
```

---

## Automated Test Runner

Run all tests at once:

```bash
cd ~/TradingViewAutonomousManager
python test_api.py
```

---

## Troubleshooting

### TradingView Not Connecting
1. Ensure TradingView Desktop is running
2. Check it's launched with: `--remote-debugging-port=9222`
3. Verify no firewall blocking port 9222
4. Try restarting TradingView Desktop

### Signals Not Reaching Sapphire
1. Check rari2 is online: `ping 100.87.225.89`
2. Verify webhook URL is correct
3. Check Sapphire service is running on rari2

### Playwright Issues
```powershell
# Reinstall Playwright browsers
cd C:\Users\aribs\TradingViewAutonomousManager\backend
.\venv\Scripts\activate
playwright install chromium
```

---

## WebSocket Real-time Updates

Connect to WebSocket for live updates:

```javascript
// JavaScript example
const ws = new WebSocket('ws://100.71.10.48:8081/ws');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('TV Update:', data);
};

ws.onopen = () => {
    // Request current state
    ws.send(JSON.stringify({type: 'get_state'}));
};
```

---

## Next Steps After Testing

1. ✅ Verify all API endpoints work
2. ✅ Test TradingView Desktop automation
3. ✅ Create and test strategies
4. ✅ Set up watchlists
5. 🔄 Deploy to Pi mesh (rari1/rari2)
6. 🔄 Integrate with Sapphire production

---

**Ready to test? Start with Phase 1 - connect TradingView Desktop!**
