from market_atlas.integrations.sapphire_gateway import to_gateway_signal_payload


def test_gateway_payload_maps_signal_fields():
    signal = {
        "signal_id": "atlas-btc-1",
        "symbol": "BTCUSDT",
        "action": "BUY",
        "confidence": 0.83,
        "edge": 0.02,
        "timeframe": "1d",
        "strategy": "momentum_regime",
        "take_profit": 104.0,
        "stop_loss": 97.0,
        "metadata": {"regime": "Goldilocks"},
    }
    payload = to_gateway_signal_payload(signal, target_platforms=["lighter"])
    assert payload is not None
    assert payload["symbol"] == "BTCUSDT"
    assert payload["side"] == "BUY"
    assert payload["target_platforms"] == ["lighter"]
    assert payload["take_profit"] == 104.0
    assert payload["stop_loss"] == 97.0
    assert payload["metadata"]["strategy"] == "momentum_regime"
    assert payload["metadata"]["signal_id"] == "atlas-btc-1"


def test_gateway_payload_skips_non_actionable_signals():
    signal = {"signal_id": "atlas-sol-1", "symbol": "SOLUSDT", "action": "HOLD"}
    payload = to_gateway_signal_payload(signal, target_platforms=["lighter"])
    assert payload is None
