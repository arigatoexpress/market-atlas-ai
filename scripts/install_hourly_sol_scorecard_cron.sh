#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${ROOT_DIR}/reports/scorecards"
LOG_FILE="${LOG_DIR}/sol_hourly_cron.log"
TAG="# market-atlas-sol-hourly-scorecard"
MINUTE="${CRON_MINUTE:-5}"

mkdir -p "${LOG_DIR}"

ROOT_ESCAPED="${ROOT_DIR// /\\ }"
CMD="cd ${ROOT_ESCAPED} && /bin/bash ${ROOT_ESCAPED}/scripts/run_hourly_sol_scorecard.sh >> ${ROOT_ESCAPED}/reports/scorecards/sol_hourly_cron.log 2>&1"
LINE="${MINUTE} * * * * ${CMD} ${TAG}"

CURRENT="$(crontab -l 2>/dev/null || true)"
if echo "${CURRENT}" | grep -Fq "${TAG}"; then
  echo "Cron entry already exists (${TAG})."
  exit 0
fi

if [[ -n "${CURRENT}" ]]; then
  printf "%s\n%s\n" "${CURRENT}" "${LINE}" | crontab -
else
  printf "%s\n" "${LINE}" | crontab -
fi

echo "Installed hourly scorecard cron:"
echo "  ${LINE}"
echo "Log file:"
echo "  ${LOG_FILE}"
