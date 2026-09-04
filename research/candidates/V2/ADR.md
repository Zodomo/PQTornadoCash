# V2: Checked inverse witnesses

## Status

PENDING: remain BENCHMARK_ONLY until a canonical full-path replay establishes a gate.

## Context

SP-31 requires this optimization in isolation and in a non-additive combined package against the frozen v0.3 baseline. The canonical generated proof fixture is not checked in, so kernel measurements cannot be relabeled as transaction measurements.

## Decision

Use the shared Rust/Solidity kernels and fail-closed driver. Preserve canonical encodings and protocol ordering. Witnesses are accepted only for denominators whose nonzero obligation is independently enforced. Zero-legal batch and selector legs retain native handling.

## Gate

Keep only with at least 2% measured complete-verifier savings, removal of a known security risk, or material measured worst-case proof-byte reduction. Small V3+V4 work may be grouped only as a simplifying combination. No custody code is changed.
