#!/bin/sh
set -eu
umask 077

PACKAGE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
OUTPUT=${1:-"$PACKAGE_DIR/outputs/latest.json"}
case "$OUTPUT" in
  /*) ;;
  *) OUTPUT="$PWD/$OUTPUT" ;;
esac
PIN=3152b14a89067c83775a8076cc262ffc48a1fd7c
WORK=$(mktemp -d "${TMPDIR:-/tmp}/pqtc-c20.XXXXXX")
trap 'rm -rf "$WORK"' EXIT HUP INT TERM

mkdir -p "$(dirname -- "$OUTPUT")"
git clone --quiet --filter=blob:none https://github.com/Plonky3/Plonky3.git "$WORK/source"
git -C "$WORK/source" checkout --quiet --detach "$PIN"
test "$(git -C "$WORK/source" rev-parse HEAD)" = "$PIN"
(
  cd "$WORK/source"
  printf '%s  %s\n' \
    b4d77a18897723ddd9d6b8c33c8cdd1bbfb97681001b6372314006d294e1aaf3 whir/src/pcs/zk/adapter.rs \
    156b1d59ae13968775eee35fd2b4e3c29730f5ffac2557f0a605d4c5bd91eeca whir/src/pcs/zk/config.rs \
    0e5ea33efa701fbfd29c2367da588e462a9241a636d0019f640e1e0aec886c9f whir/src/pcs/zk/security.rs \
    0bd7137da9590ee8068d377737f8b180dbc9a1729073bbb4955e967ff6cff402 whir/src/pcs/zk/proof.rs \
    | shasum -a 256 -c - >/dev/null
)
cp -R "$PACKAGE_DIR/adapter" "$WORK/source/pqtc-c20-adapter"
CARGO_TARGET_DIR="$WORK/build" PQTC_SOURCE_HASHES_VERIFIED=1 \
  cargo run --locked --quiet --release --manifest-path "$WORK/source/pqtc-c20-adapter/Cargo.toml" \
  >"$WORK/result.json"
python3 "$PACKAGE_DIR/validate-result.py" "$WORK/result.json"
mv "$WORK/result.json" "$OUTPUT"
printf '%s\n' "$OUTPUT"
