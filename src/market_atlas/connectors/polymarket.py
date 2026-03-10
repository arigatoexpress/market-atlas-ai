from __future__ import annotations

from datetime import datetime, timezone
import json

import pandas as pd
import requests

POLYMARKET_GAMMA = "https://gamma-api.polymarket.com/markets"


def fetch_prediction_markets(limit: int = 200) -> pd.DataFrame:
    resp = requests.get(POLYMARKET_GAMMA, params={"limit": limit}, timeout=20)
    resp.raise_for_status()
    markets = resp.json()
    rows = []
    now = datetime.now(timezone.utc)

    for market in markets:
        # best effort parse; field names can vary over time
        market_id = str(market.get("id") or market.get("conditionId") or "")
        question = market.get("question") or market.get("title") or ""
        prob = market.get("probability")
        if prob is None:
            outcomes = market.get("outcomes") or []
            if outcomes and isinstance(outcomes, list) and isinstance(outcomes[0], dict):
                prob = outcomes[0].get("price")
        volume = market.get("volume") or market.get("liquidity") or 0

        rows.append(
            {
                "ts": now,
                "source": "polymarket",
                "market_id": market_id,
                "question": question,
                "probability": float(prob) if prob is not None else None,
                "volume": float(volume) if volume is not None else None,
                "payload": json.dumps(market),
            }
        )

    return pd.DataFrame(rows)
