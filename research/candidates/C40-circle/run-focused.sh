#!/bin/sh
set -eu
umask 077

PACKAGE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
OUTPUT=${1:-"$PACKAGE_DIR/outputs/latest.json"}
case "$OUTPUT" in
  /*) ;;
  *) OUTPUT="$PWD/$OUTPUT" ;;
esac
WORK=$(mktemp -d "${TMPDIR:-/tmp}/pqtc-c40.XXXXXX")
trap 'rm -rf "$WORK"' EXIT HUP INT TERM

mkdir -p "$(dirname -- "$OUTPUT")"
python3 "$PACKAGE_DIR/source-watch.py" --work "$WORK" >"$WORK/result.json"
python3 "$PACKAGE_DIR/validate-result.py" "$WORK/result.json"
mv "$WORK/result.json" "$OUTPUT"
printf '%s\n' "$OUTPUT"
