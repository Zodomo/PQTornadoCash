#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../../../.." && pwd)
EVMROOT="$ROOT/research/candidates/v03-baseline/evm"
OUT="$ROOT/research/candidates/v03-baseline/gas/deployment-profile.log"
mkdir -p "$(dirname "$OUT")"
(CDPATH= cd -- "$EVMROOT" && forge test --root . \
  --match-test testDeploymentInitcodeRuntimeAndCodeDepositGas -vv) >"$OUT" 2>&1
if [ -f "$ROOT/research/candidates/v03-baseline/gas/deposit-profile.log" ] && [ -f "$ROOT/research/runs/v03-fixed-01.json" ]; then
  python3 "$ROOT/research/candidates/v03-baseline/scripts/synthesize-measurements.py"
fi
cat "$OUT"
