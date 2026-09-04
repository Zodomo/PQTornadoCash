# SP-31 combined verifier optimization package

## Status

BENCHMARK_ONLY. No custody integration is authorized.

## Decision

Run V1-V9 from one fail-closed command. Keep measured isolated Solidity gas and diagnostic Rust aggregate timings in separate JSON fields. The Rust `bench()` loop has no warmup or sample distribution and is not common-protocol-comparable. Do not add overlapping microbenchmarks. V3+V4 is the only predeclared simplifying combination. A complete-transaction gate remains pending because no isolated optimized full-verifier variant exists; the source-bound canonical baseline is observed and used for projections.
