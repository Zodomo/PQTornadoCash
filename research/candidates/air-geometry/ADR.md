# ADR: Stop alternate AIR work at the SP-10 dependency gate

## Status

`STOPPED_BY_DEPENDENCY`. A0 is retained as source-verified frozen evidence. A1 through A4 were not implemented, measured, or admitted to PCS integration.

## Context

SP-20 requires the winning SP-10 application primitive. Every H0–H7 status records `gateComparison.airDisposition = STOPPED` and `allPass = false`. No candidate passed the full-storage deposit, structural-security, and external-review gates together. SP-02 is also `ARCHIVED_FAILED` with `gateResult = FAIL` because the required native malformed-proof panic containment was not established.

The frozen v0.3 sources remain useful as a correctness anchor. They specify a 256-row, 190-column withdrawal AIR, including a maintained 157-column Poseidon2 sub-AIR, 240 active application permutations, four public-payout binding rows, twelve padding rows, 1,186 constraints, maximum degree seven, sixteen quotient chunks, and 210 batched functions. The frozen hiding profile fixes the PCS inputs recorded in `results.json`. These facts describe A0 only.

## Decision

1. Preserve A0 as `SOURCE_VERIFIED_BASELINE` and pin every source used to recover it.
2. Retain A1, A2 lane-parallelism `1/2/4/8/16/full`, A3 table decomposition, and A4 backend-neutral forms only as symbolic worksheets. Every such row is `NOT_ATTEMPTED_BY_GATE`, has `measured = false`, and contains no numeric geometry, proof, gas, timing, or memory result.
3. Do not construct an SP-10 finalist, substitute H0, or infer geometry from isolated field or verifier microbenchmarks.
4. Prohibit PCS integration until one SP-10 status satisfies the explicit eligibility predicate and SP-02's failed prerequisite is resolved.
5. Treat symbolic bounds as algebraic planning expressions only. They are neither measured geometry nor finalist projections.

## Consequences

There is no SP-20 winner and no downstream geometry selection. A1–A4 have no proof bytes, native proving measurements, or EVM AIR/DEEP gas. `check.py` validates the honest stopped package and all eight upstream dispositions. Its `--require-eligible` mode exits with code 3 while no eligible SP-10 status exists, so automation cannot silently consume these worksheets as a finalist.
