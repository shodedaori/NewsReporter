#!/usr/bin/env bash
set -euo pipefail

python -m src.app.main --date "$(date +%F)" --publish
