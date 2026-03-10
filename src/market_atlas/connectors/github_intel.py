from __future__ import annotations

from datetime import datetime, timezone
import json

import pandas as pd
import requests

GITHUB_SEARCH = "https://api.github.com/search/repositories"


def fetch_open_source_intel(token: str = "", per_page: int = 50) -> pd.DataFrame:
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    query = "(crypto OR trading OR quant OR market) stars:>50 pushed:>2024-01-01"
    params = {"q": query, "sort": "stars", "order": "desc", "per_page": per_page}
    resp = requests.get(GITHUB_SEARCH, headers=headers, params=params, timeout=20)
    resp.raise_for_status()
    payload = resp.json()

    rows = []
    for item in payload.get("items", []):
        rows.append(
            {
                "ts": datetime.now(timezone.utc),
                "source": "github",
                "topic": item.get("full_name", ""),
                "score": float(item.get("stargazers_count", 0)),
                "payload": json.dumps(
                    {
                        "url": item.get("html_url"),
                        "description": item.get("description"),
                        "stars": item.get("stargazers_count"),
                        "forks": item.get("forks_count"),
                        "updated_at": item.get("updated_at"),
                    }
                ),
            }
        )

    return pd.DataFrame(rows)
