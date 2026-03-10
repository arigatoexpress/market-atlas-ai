#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

source .venv/bin/activate

START_DATE="${START_DATE:-2024-01-01}"
SYMBOL="${SCORECARD_SYMBOL:-SOLUSDT}"
BOT_STATUS_URL="${SCORECARD_BOT_STATUS_URL:-http://127.0.0.1:18082/status}"
GATEWAY_URL="${SAPPHIRE_GATEWAY_URL:-http://127.0.0.1:18080}"
PUBLISH_SIGNALS="${PUBLISH_SIGNALS:-true}"
PUBLISH_FORCE="${PUBLISH_FORCE:-true}"
MIN_FILL_RATE_PCT="${SCORECARD_MIN_FILL_RATE_PCT:-70}"
MAX_REJECT_TAX_PCT="${SCORECARD_MAX_REJECT_TAX_PCT:-25}"
MAX_EV_ERROR_PCT="${SCORECARD_MAX_EV_ERROR_PCT:-5}"
MAX_DRAWDOWN_PCT="${SCORECARD_MAX_DRAWDOWN_PCT:--35}"

echo "[1/4] full-run (ingest -> features -> regimes -> backtest -> brief)"
market-atlas full-run --start-date "${START_DATE}"

echo "[2/4] promotion gate"
market-atlas promotion-gate --output reports/latest/promotion_gate.json

if [[ "${PUBLISH_SIGNALS,,}" == "true" ]]; then
  echo "[3/4] publish ${SYMBOL} to Sapphire gateway"
  publish_args=(
    market-atlas publish-sapphire
    --symbols "${SYMBOL}"
    --gateway-url "${GATEWAY_URL}"
    --output reports/latest/publish_results.json
  )
  if [[ "${PUBLISH_FORCE,,}" == "true" ]]; then
    publish_args+=(--force)
  fi
  "${publish_args[@]}"
else
  echo "[3/4] publish skipped (PUBLISH_SIGNALS=${PUBLISH_SIGNALS})"
fi

echo "[4/4] build SOL scorecard + append hourly history"
market-atlas scorecard \
  --symbol "${SYMBOL}" \
  --bot-status-url "${BOT_STATUS_URL}" \
  --min-fill-rate-pct "${MIN_FILL_RATE_PCT}" \
  --max-reject-tax-pct "${MAX_REJECT_TAX_PCT}" \
  --max-ev-error-pct "${MAX_EV_ERROR_PCT}" \
  --max-drawdown-pct "${MAX_DRAWDOWN_PCT}" \
  --output reports/latest/sol_scorecard.json \
  --history-path reports/scorecards/sol_hourly_history.jsonl

echo
echo "Hourly scorecard run complete."
echo "Artifacts:"
echo "  reports/latest/sol_scorecard.json"
echo "  reports/latest/sol_scorecard.md"
echo "  reports/scorecards/sol_hourly_history.jsonl"
