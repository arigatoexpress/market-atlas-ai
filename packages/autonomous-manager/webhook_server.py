#!/usr/bin/env python3
"""
TradingView Webhook Server
Receives alerts from TradingView and forwards to Sapphire
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import json
import logging
from datetime import datetime
from typing import Dict, Any

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="TradingView Webhook Receiver")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
SAPPHIRE_WEBHOOK = "http://100.87.225.89:8080/tradingview/webhook"
WEBHOOK_SECRET = ""  # Set your secret here

# Venue mapping (same as before)
VENUE_MAPPING = {
    'SOL': 'ASTER',
    'JUP': 'ASTER',
    'PYTH': 'ASTER',
    'BONK': 'ASTER',
    'WIF': 'ASTER',
    'BTC': 'LIGHTER',
    'ETH': 'LIGHTER',
    'HYPE': 'LIGHTER',
    'DOGE': 'LIGHTER',
    'AVAX': 'LIGHTER'
}


def get_venue(symbol: str) -> str:
    """Determine venue from symbol"""
    base = symbol.replace('USDT', '').replace('USD', '').replace('PERP', '')
    return VENUE_MAPPING.get(base, 'LIGHTER')


@app.post("/tradingview-webhook")
async def receive_tradingview_alert(request: Request):
    """
    Receive TradingView alert webhook
    
    TradingView sends:
    {
        "symbol": "BTCUSDT",
        "action": "buy",
        "price": 45000,
        "strategy": "My Strategy"
    }
    """
    try:
        # Parse the alert data
        data = await request.json()
        logger.info(f"Received alert: {json.dumps(data, indent=2)}")
        
        # Extract fields (TradingView can send various formats)
        symbol = data.get('symbol', data.get('ticker', ''))
        action = data.get('action', data.get('side', 'buy')).lower()
        price = float(data.get('price', 0))
        strategy = data.get('strategy', 'TV Alert')
        
        # Convert action
        if action in ['buy', 'long', 'entry']:
            action = 'buy'
        elif action in ['sell', 'short', 'exit']:
            action = 'sell'
        
        # Build Sapphire signal
        sapphire_signal = {
            "action": action,
            "symbol": symbol,
            "venue": get_venue(symbol),
            "price": price,
            "strategy": strategy,
            "source": "tradingview_webhook",
            "timestamp": datetime.now().isoformat(),
            "secret": WEBHOOK_SECRET
        }
        
        # Forward to Sapphire
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                SAPPHIRE_WEBHOOK,
                json=sapphire_signal
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Signal forwarded to Sapphire: {symbol} {action}")
                return {
                    "status": "success",
                    "message": "Signal forwarded to Sapphire",
                    "sapphire_response": response.json() if response.text else {}
                }
            else:
                logger.error(f"❌ Sapphire error: {response.status_code}")
                raise HTTPException(
                    status_code=502,
                    detail=f"Sapphire returned {response.status_code}"
                )
    
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tradingview-webhook/alert")
async def receive_simple_alert(request: Request):
    """
    Simpler endpoint for basic TradingView alerts
    Just forwards message to Sapphire
    """
    try:
        body = await request.body()
        message = body.decode('utf-8')
        
        logger.info(f"Received simple alert: {message}")
        
        # Try to parse as JSON
        try:
            data = json.loads(message)
        except:
            # If not JSON, treat as text alert
            data = {"message": message}
        
        # Forward to Sapphire
        sapphire_signal = {
            "action": data.get('action', 'status'),
            "symbol": data.get('symbol', ''),
            "message": message,
            "source": "tradingview_alert",
            "timestamp": datetime.now().isoformat(),
            "secret": WEBHOOK_SECRET
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                SAPPHIRE_WEBHOOK,
                json=sapphire_signal
            )
            
            return {
                "status": "forwarded",
                "sapphire_status": response.status_code
            }
    
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "sapphire_webhook": SAPPHIRE_WEBHOOK,
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    print("="*60)
    print("TradingView Webhook Server")
    print("="*60)
    print(f"Sapphire Webhook: {SAPPHIRE_WEBHOOK}")
    print(f"Listening on: http://0.0.0.0:8082")
    print("="*60)
    uvicorn.run(app, host="0.0.0.0", port=8082)
