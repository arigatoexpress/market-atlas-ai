from market_atlas.pipelines.regimes import _classify_row


def test_goldilocks_classification():
    regime, confidence, rationale = _classify_row(growth=0.2, inflation=-0.1, liquidity=0.3)
    assert regime == "Goldilocks"
    assert 0.0 <= confidence <= 1.0
    assert "growth" in rationale


def test_stagflation_classification():
    regime, _, _ = _classify_row(growth=-0.2, inflation=0.15, liquidity=-0.1)
    assert regime == "Stagflation"
