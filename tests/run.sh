#!/usr/bin/env bash
# Run this plugin's tests, then validate its manifest.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
python3 -m unittest discover -s tests
if command -v omarchy >/dev/null 2>&1; then
  omarchy plugin validate .
else
  echo "omarchy not found; skipped manifest validation"
fi
