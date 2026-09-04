#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../../../.." && pwd)
RUN_ID=${1:-v03-fixed-19}
OUT="$ROOT/research/candidates/v03-baseline/gas/t8n/$RUN_ID"
python3 "$ROOT/research/candidates/v03-baseline/scripts/export-t8n-prestate.py" --run-id "$RUN_ID" --out "$OUT"
if [ -n "${EVM_BIN:-}" ]; then
  "$EVM_BIN" --version >"$OUT/client-version.txt"
  "$EVM_BIN" t8n --state.fork Prague --trace --opcode.count opcode-count.json --input.alloc "$OUT/alloc.json" --input.env "$OUT/env.json" --input.txs "$OUT/txs.json" --output.alloc post-alloc.json --output.result result.json --output.body body.rlp --output.basedir "$OUT" >"$OUT/t8n.stdout.log" 2>"$OUT/t8n.stderr.log"
else
  IMAGE=ethereum/client-go:alltools-v1.17.5
  REL="research/candidates/v03-baseline/gas/t8n/$RUN_ID"
  docker image inspect "$IMAGE" >/dev/null 2>&1 || { echo "STOP: pinned $IMAGE is not installed; no network pull is attempted" >&2; exit 2; }
  docker run --rm -v "$ROOT:/workspace" -w /workspace "$IMAGE" evm --version >"$OUT/client-version.txt"
  docker run --rm -v "$ROOT:/workspace" -w /workspace "$IMAGE" evm t8n --state.fork Prague --trace --opcode.count opcode-count.json --input.alloc "/workspace/$REL/alloc.json" --input.env "/workspace/$REL/env.json" --input.txs "/workspace/$REL/txs.json" --output.alloc post-alloc.json --output.result result.json --output.body body.rlp --output.basedir "/workspace/$REL" >"$OUT/t8n.stdout.log" 2>"$OUT/t8n.stderr.log"
fi
python3 "$ROOT/research/candidates/v03-baseline/scripts/parse-t8n-result.py" "$OUT"
python3 "$ROOT/research/candidates/v03-baseline/scripts/synthesize-measurements.py"
