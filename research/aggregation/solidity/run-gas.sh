#!/bin/sh
set -eu
cd "$(dirname "$0")"
forge test --match-test testMeasureSettlementComponentsOnly -vv
python3 ../ingest-foundry.py
