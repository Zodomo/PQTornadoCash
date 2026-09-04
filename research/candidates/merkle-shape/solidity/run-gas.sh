#!/bin/sh
set -eu
cd "$(dirname "$0")"
forge test --match-test testCanonicalH0SweepAndBoundaries -vv
python3 ../ingest-foundry.py
