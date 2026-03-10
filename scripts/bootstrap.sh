#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

echo "Bootstrap complete."
echo "Run: source .venv/bin/activate && market-atlas full-run --start-date 2024-01-01"
