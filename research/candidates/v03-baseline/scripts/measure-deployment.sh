#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../../../.." && pwd)
if [ -e "$ROOT/.env" ]; then
  echo "refusing Foundry invocation while repository .env exists" >&2
  exit 2
fi
OUT="$ROOT/research/candidates/v03-baseline/gas/deployment-profile.log"
mkdir -p "$(dirname "$OUT")"
forge test --root "$ROOT/research/candidates/v03-baseline/evm" \
  --match-test testDeploymentInitcodeRuntimeAndCodeDepositGas -vv >"$OUT" 2>&1
cat "$OUT"
