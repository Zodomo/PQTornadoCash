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
WORK=$(mktemp -d "${TMPDIR:-/tmp}/pqtc-c30.XXXXXX")
trap 'rm -rf "$WORK"' EXIT HUP INT TERM

mkdir -p "$(dirname -- "$OUTPUT")"
git clone --quiet --filter=blob:none https://github.com/Plonky3/Plonky3.git "$WORK/source"
git -C "$WORK/source" checkout --quiet --detach "$PIN"
test "$(git -C "$WORK/source" rev-parse HEAD)" = "$PIN"
(
  cd "$WORK/source"
  printf '%s  %s\n' \
    1ab67427b3b55f11ca63772236cf1625b928369410723dfa28db41268884866a stir/src/pcs.rs \
    1e331cf86eaca8510cf68e16c745f7518341eebe6aaaecb8e0b4ba3d12c4b3e2 Cargo.toml \
    | shasum -a 256 -c - >/dev/null
)
cp -R "$PACKAGE_DIR/adapter" "$WORK/source/pqtc-c30-adapter"
CARGO_TARGET_DIR="$WORK/build" PQTC_SOURCE_HASHES_VERIFIED=1 \
  cargo run --locked --quiet --release --manifest-path "$WORK/source/pqtc-c30-adapter/Cargo.toml" \
  >"$WORK/result.json"
python3 "$PACKAGE_DIR/validate-result.py" "$WORK/result.json"
mv "$WORK/result.json" "$OUTPUT"
printf '%s\n' "$OUTPUT"
