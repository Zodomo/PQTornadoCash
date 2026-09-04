# V4: Calldata-native bounded-memory evaluation

## Status

PENDING: remain BENCHMARK_ONLY until a canonical full-path replay establishes a gate.

## Context

SP-31 requires this optimization in isolation and in a non-additive combined package against the frozen v0.3 baseline. Projections are anchored to the source-bound canonical v03-fixed-01 run; the historic report fixture is retained only as a named comparator. The kernels are not integrated into a full verifier, so their measurements cannot be relabeled as transaction measurements.

## Decision

Use the shared Rust/Solidity kernels and fail-closed driver. Preserve canonical encodings and protocol ordering. Loops are length-bounded before entry and consume calldata directly; V3+V4 is the simplifying combination.

## Gate

Keep only with at least 2% measured complete-verifier savings, removal of a known security risk, or material measured worst-case proof-byte reduction. Small V3+V4 work may be grouped only as a simplifying combination. No custody code is changed.
