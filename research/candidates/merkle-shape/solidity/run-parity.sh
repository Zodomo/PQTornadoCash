#!/bin/sh
set -eu
cd "$(dirname "$0")"
forge test --match-test testFrozenV03AllThousandRoots -vv
