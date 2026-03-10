#!/usr/bin/env bash
set -euo pipefail

TAG="# market-atlas-sol-hourly-scorecard"
CURRENT="$(crontab -l 2>/dev/null || true)"

if [[ -z "${CURRENT}" ]]; then
  echo "No crontab entries found."
  exit 0
fi

FILTERED="$(echo "${CURRENT}" | grep -Fv "${TAG}" || true)"
if [[ "${FILTERED}" == "${CURRENT}" ]]; then
  echo "No scorecard cron entry found."
  exit 0
fi

if [[ -n "${FILTERED}" ]]; then
  printf "%s\n" "${FILTERED}" | crontab -
else
  crontab -r
fi

echo "Removed hourly scorecard cron entry (${TAG})."
