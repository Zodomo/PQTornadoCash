# ADR: H1 measurement decision

## Context

SP-10 requires a deterministic benchmark candidate without modifying frozen custody code. The only published Poseidon2 compressor reviewed here is first-lane `Trunc_d(P(x)+x)`; H7 is preserved as its published sponge.

## Decision

Measure as a negative control; it cannot pass the mixer gate. Stopped: two children require 14 lanes and four separate controls require 18 > 16.

## Rejected alternatives

No `TruncatedPermutation`, output-lane substitution, control packing, chained permutation, concatenated truncation, matrix change, constant reuse across widths, or invented RPO compressor is permitted.

## Consequences

Status remains `BENCHMARK_ONLY` and grants no security-qualified label. Promotion requires independent review of the exact field, permutation, constants, mode, constrained layouts, multi-target model, and quantum assumptions.

## Measurement profile

Solidity gas and size evidence is comparable under the canonical profile only: solc 0.8.30, Prague EVM, optimizer enabled with 200 runs, and via-IR enabled. Measurements from any other profile do not satisfy this ADR.

## AIR gate comparison

All five gates are conjunctive; AIR work remains stopped unless every gate passes.

- 5× node-permutation reduction: NOT PASSED — H1 has no application node permutation count.
- Complete direct deposit below 4,000,000 gas: NOT EVALUATED — no complete non-H0 direct-deposit implementation was benchmarked.
- Generic security of at least 100 bits: FAIL — ideal quantum collision ceiling 72.116 bits and hidden-part Grover ceiling 139.081 bits; limiting generic ceiling 72.116 bits. This is a necessary width heuristic only, not qualification.
- No structural attack: FAIL — the exact 2026 width-16 compression round-skip result applies.
- External review: NOT PASSED — the exact construction has not been externally reviewed.

Overall: **FAIL**. This candidate remains stopped from AIR work. Numeric evidence is `research/candidates/hash-compression-common/gas/results.json`. The separately retained synthetic depth-20 root-update gas is not a direct-deposit measurement.

## Negative evidence and unmeasured scope

No application-role implementation is evaluated; scope, empty-leaf, and statement roles are NOT_EVALUATED. Solidity parity covers 8 suite-wide anchor vectors, not the 18,146-vector bundle; full three-language parity and the required misuse suite are NOT_EVALUATED. The constant-comparison run is NOT_RETAINED.
