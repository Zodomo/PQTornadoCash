#!/bin/sh
set -eu
cd "$(dirname "$0")"
forge test --match-test testMeasureQueueUserDepositPath -vv
python3 ../ingest-foundry.py
