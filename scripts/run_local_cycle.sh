#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

source .venv/bin/activate

START_DATE="${START_DATE:-2024-01-01}"
STRICT_LIVE_MODE="${STRICT_LIVE_MODE:-true}"
if [[ "${STRICT_LIVE_MODE,,}" == "true" ]]; then
  SYMBOLS="${SYMBOLS:-SOLUSDT}"
else
  SYMBOLS="${SYMBOLS:-BTCUSDT,ETHUSDT,SOLUSDT}"
fi

echo "[1/4] ingest + features + regimes + backtest"
market-atlas full-run --start-date "${START_DATE}"

echo "[2/4] promotion gate"
market-atlas promotion-gate --output reports/latest/promotion_gate.json

echo "[3/4] publish signals to local Sapphire gateway (blocked unless gate passes)"
echo "      symbols=${SYMBOLS} strict_live_mode=${STRICT_LIVE_MODE}"
market-atlas publish-sapphire \
  --symbols "${SYMBOLS}" \
  --gateway-url "${SAPPHIRE_GATEWAY_URL:-http://127.0.0.1:18080}" \
  --output reports/latest/publish_results.json

echo "[4/4] done"
echo "Artifacts:"
echo "  reports/latest/report.md"
echo "  reports/latest/operator_brief.md"
echo "  reports/latest/promotion_gate.md"
echo "  reports/latest/publish_results.json"
