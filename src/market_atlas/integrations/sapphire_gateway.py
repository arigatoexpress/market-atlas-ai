from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import requests


def to_gateway_signal_payload(
    signal: dict,
    target_platforms: list[str],
    source: str = "market-atlas",
) -> dict | None:
    action = str(signal.get("action", "")).upper()
    if action not in {"BUY", "SELL"}:
        return None

    metadata = dict(signal.get("metadata") or {})
    metadata["signal_id"] = signal.get("signal_id")
    metadata["edge"] = signal.get("edge")
    metadata["strategy"] = signal.get("strategy")
    metadata["timeframe"] = signal.get("timeframe")
    entry_price = signal.get("entry_price")
    if entry_price is None:
        entry_price = metadata.get("close")

    return {
        "symbol": signal.get("symbol"),
        "side": action,
        "signal_type": "entry",
        "confidence": float(signal.get("confidence") or 0.0),
        "target_platforms": target_platforms,
        "entry_price": entry_price,
        "stop_loss": signal.get("stop_loss"),
        "take_profit": signal.get("take_profit"),
        "quantity": None,
        "source": source,
        "strategy": signal.get("strategy"),
        "timeframe": signal.get("timeframe"),
        "metadata": metadata,
    }


def publish_signals(
    signals: Iterable[dict],
    gateway_url: str,
    gateway_token: str,
    target_platforms: list[str],
    output_path: str,
) -> dict:
    endpoint = gateway_url.rstrip("/") + "/api/signals/create"
    headers = {"Content-Type": "application/json"}
    if gateway_token:
        headers["X-Gateway-Token"] = gateway_token

    sent = 0
    skipped = 0
    failed = 0
    results: list[dict] = []

    for signal in signals:
        payload = to_gateway_signal_payload(signal, target_platforms=target_platforms)
        if payload is None:
            skipped += 1
            results.append(
                {
                    "signal_id": signal.get("signal_id"),
                    "symbol": signal.get("symbol"),
                    "status": "skipped",
                    "reason": f"action={signal.get('action')}",
                }
            )
            continue

        try:
            resp = requests.post(endpoint, headers=headers, json=payload, timeout=20)
            ok = resp.status_code < 300
            if ok:
                sent += 1
                body = resp.json() if "application/json" in resp.headers.get("Content-Type", "") else {}
                results.append(
                    {
                        "signal_id": signal.get("signal_id"),
                        "symbol": signal.get("symbol"),
                        "status": "sent",
                        "gateway_response": body,
                    }
                )
            else:
                failed += 1
                results.append(
                    {
                        "signal_id": signal.get("signal_id"),
                        "symbol": signal.get("symbol"),
                        "status": "failed",
                        "http_status": resp.status_code,
                        "body": resp.text[:400],
                    }
                )
        except Exception as exc:
            failed += 1
            results.append(
                {
                    "signal_id": signal.get("signal_id"),
                    "symbol": signal.get("symbol"),
                    "status": "failed",
                    "error": str(exc),
                }
            )

    output = {
        "endpoint": endpoint,
        "sent": sent,
        "skipped": skipped,
        "failed": failed,
        "results": results,
    }

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    return output
