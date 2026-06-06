# TradingView Autonomous Manager - Quick Start

## 🎉 Status: Both Servers Running!

| Server | Port | Status | URL |
|--------|------|--------|-----|
| Main API | 8081 | ✅ Running | http://100.71.10.48:8081 |
| Webhook | 8082 | ✅ Running | http://100.71.10.48:8082 |

---

## 🚀 Option 1: TradingView Webhooks (EASIEST - Production Ready)

This is the BEST approach for automated trading with Sapphire.

### Step 1: Verify Webhook Server
```bash
# From your Mac:
curl http://100.71.10.48:8082/health

# Expected: {"status": "healthy", "sapphire_webhook": "..."}
```

### Step 2: Add Pine Script to TradingView
1. Open TradingView Desktop or Web
2. Open Pine Editor (bottom of screen)
3. Copy the code from: `pine_scripts/webhook_strategy_template.pine`
4. Click "Add to Chart"

### Step 3: Create Alert with Webhook
1. Click "Alerts" (right panel)
2. Click "Create Alert"
3. Configure:
   - **Condition:** Your strategy (Sapphire Webhook Strategy)
   - **Webhook URL:** `http://100.71.10.48:8082/tradingview-webhook`
   - **Message:** 
     ```json
     {"symbol":"{{ticker}}","action":"{{strategy.order.action}}","price":{{close}}}
     ```
4. Click "Create"

### Step 4: Test
```bash
# Send test webhook manually:
curl -X POST http://100.71.10.48:8082/tradingview-webhook \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BTCUSDT","action":"buy","price":45000}'
```

---

## 🎮 Option 2: Full TradingView Control (Playwright)

For research, screenshots, and manual chart control.

### Step 1: Launch TradingView Desktop with Debug Port
```powershell
# On your Windows PC (PowerShell):
& "C:\Users\$env:USERNAME\AppData\Local\Programs\TradingView\TradingView.exe" --remote-debugging-port=9222
```

### Step 2: Connect via API
```bash
# From your Mac:
curl -X POST http://100.71.10.48:8081/tv/connect
```

### Step 3: Control TradingView
```bash
# Change symbol
curl -X POST http://100.71.10.48:8081/tv/symbol/BTCUSDT

# Change timeframe
curl -X POST http://100.71.10.48:8081/tv/timeframe/1h

# Take screenshot
curl -X POST http://100.71.10.48:8081/tv/screenshot

# Get state
curl http://100.71.10.48:8081/tv/state
```

---

## 📊 API Reference

### Main API (Port 8081) - Chart Control
```
POST /tv/connect              - Connect to TV Desktop
GET  /tv/state                - Get current chart state
POST /tv/symbol/{symbol}      - Change symbol
POST /tv/timeframe/{tf}       - Change timeframe (1m, 5m, 15m, 1h, 4h, 1d)
POST /tv/indicator/{name}     - Add indicator (RSI, MACD, EMA, etc.)
POST /tv/screenshot           - Capture chart screenshot

GET  /strategies              - List strategies
POST /strategies              - Create new strategy
POST /strategies/{id}/apply   - Apply to chart

GET  /watchlists              - List watchlists
POST /watchlists              - Create watchlist
POST /watchlists/{id}/sync    - Sync to TradingView
```

### Webhook Server (Port 8082) - Signal Reception
```
POST /tradingview-webhook     - Receive TradingView alerts
GET  /health                  - Server health check
```

### Sapphire Integration
```
POST /signals/send            - Send signal to Sapphire
GET  /sapphire/status         - Check Sapphire connection
POST /sapphire/heartbeat      - Test connection
```

---

## 🧪 Testing Commands

Run from your Mac:

```bash
# Health check
curl http://100.71.10.48:8081/health

# List strategies
curl http://100.71.10.48:8081/strategies

# List watchlists  
curl http://100.71.10.48:8081/watchlists

# Send test signal to Sapphire
curl -X POST http://100.71.10.48:8081/signals/send \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTCUSDT",
    "direction": "LONG",
    "entry_price": 45000,
    "stop_loss": 44000,
    "take_profit": 47000,
    "confidence": 0.85,
    "venue": "LIGHTER"
  }'
```

---

## 📁 Project Files

| File | Purpose |
|------|---------|
| `backend/main.py` | Main FastAPI server |
| `webhook_server.py` | TradingView webhook receiver |
| `pine_scripts/webhook_strategy_template.pine` | Pine Script with webhook alerts |
| `interactive_test.py` | Interactive testing menu |
| `connect_tv.py` | Helper to connect TV Desktop |
| `test_api.py` | Automated test suite |
| `show_state.py` | Display current state |

---

## 🔧 Troubleshooting

### Webhook server not responding?
```powershell
# Check if running
netstat -ano | findstr 8082

# Restart it
cd C:\Users\aribs\TradingViewAutonomousManager
.\backend\venv\Scripts\activate
python webhook_server.py
```

### TradingView not connecting?
```powershell
# Check if TV is running with CDP
netstat -ano | findstr 9222

# If not, restart TV:
taskkill /F /IM TradingView.exe
& "C:\Users\$env:USERNAME\AppData\Local\Programs\TradingView\TradingView.exe" --remote-debugging-port=9222
```

### Firewall blocking?
```powershell
# Check rules
netsh advfirewall firewall show rule name="TradingView*"

# Add if needed
netsh advfirewall firewall add rule name="TV Manager" dir=in action=allow protocol=tcp localport=8081
netsh advfirewall firewall add rule name="TV Webhook" dir=in action=allow protocol=tcp localport=8082
```

---

## 🎯 Recommended Setup

For **production automated trading**:
1. ✅ Use **Webhooks (Port 8082)** as primary signal flow
2. ✅ Keep **Main API (Port 8081)** for research/monitoring
3. ✅ Deploy webhook server to rari2 for 24/7 operation

For **testing/development**:
1. ✅ Use **Main API** for full chart control
2. ✅ Take screenshots to verify signals
3. ✅ Test strategies manually

---

## 📚 Documentation

- `APPROACH_COMPARISON.md` - Compare webhooks vs automation vs lightweight charts
- `TV_TESTING_GUIDE.md` - Comprehensive testing guide
- `README.md` - Full project documentation

---

**You're all set! Start with webhooks for the easiest path to automated trading! 🚀**
