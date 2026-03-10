from __future__ import annotations

from datetime import datetime, timedelta
import json
from typing import List

import pandas as pd
import requests

GDELT_API = "https://api.gdeltproject.org/api/v2/doc/doc"


def fetch_news(query: str, lookback_hours: int = 48, max_records: int = 250) -> pd.DataFrame:
    end = datetime.utcnow()
    start = end - timedelta(hours=lookback_hours)

    params = {
        "query": query,
        "mode": "ArtList",
        "format": "json",
        "maxrecords": max_records,
        "sort": "DateDesc",
        "startdatetime": start.strftime("%Y%m%d%H%M%S"),
        "enddatetime": end.strftime("%Y%m%d%H%M%S"),
    }
    resp = requests.get(GDELT_API, params=params, timeout=25)
    resp.raise_for_status()
    payload = resp.json()
    articles: List[dict] = payload.get("articles", []) if isinstance(payload, dict) else []

    rows = []
    for article in articles:
        ts = pd.to_datetime(article.get("seendate"), errors="coerce")
        rows.append(
            {
                "ts": ts,
                "source": article.get("domain", "gdelt"),
                "title": article.get("title", ""),
                "url": article.get("url", ""),
                "sentiment_hint": "",
                "payload": json.dumps(article),
            }
        )

    return pd.DataFrame(rows)
