# ADR: H6 measurement decision

## Context

SP-10 requires a deterministic benchmark candidate without modifying frozen custody code. The only published Poseidon2 compressor reviewed here is first-lane `Trunc_d(P(x)+x)`; H7 is preserved as its published sponge.

## Decision

Use d=14 as the conservative-output comparator; d=15 is rejected because controls do not fit. The layout exercise uses 28 generic payload lanes followed by four controls, but note/nullifier payloads omit scope and frozen semantic secret/trapdoor widths and are not application-complete.

## Rejected alternatives

No `TruncatedPermutation`, output-lane substitution, control packing, chained permutation, concatenated truncation, matrix change, constant reuse across widths, or invented RPO compressor is permitted.

## Consequences

Status remains `BENCHMARK_ONLY` and grants no security-qualified label. Promotion requires independent review of the exact field, permutation, constants, mode, constrained layouts, multi-target model, and quantum assumptions.

## Measurement profile

Solidity gas and size evidence is comparable under the canonical profile only: solc 0.8.30, Prague EVM, optimizer enabled with 200 runs, and via-IR enabled. Measurements from any other profile do not satisfy this ADR.

## AIR gate comparison

All five gates are conjunctive; AIR work remains stopped unless every gate passes.

- 5× node-permutation reduction: PASS — H0 uses 11 node permutations; H6 uses 1; 11.000× reduction.
- Complete direct deposit below 4,000,000 gas: NOT EVALUATED — no complete non-H0 direct-deposit implementation was benchmarked.
- Generic security of at least 100 bits: PASS — ideal quantum collision ceiling 144.232 bits and hidden-part Grover ceiling 278.162 bits; limiting generic ceiling 144.232 bits. This is a necessary width heuristic only, not qualification.
- No structural attack: NOT PASSED — exact width-32 structural analysis is missing.
- External review: NOT PASSED — the exact construction has not been externally reviewed.

Overall: **FAIL**. This candidate remains stopped from AIR work. Numeric evidence is `research/candidates/hash-compression-common/gas/results.json`. The separately retained synthetic depth-20 root-update gas is not a direct-deposit measurement.

## Negative evidence and unmeasured scope

The note/nullifier cases are primitive/layout exercises only: they omit protocol scope and use candidate-output-width payloads instead of the frozen semantic secret/trapdoor widths. Complete application-role parity is not claimed; scope, empty-leaf, and statement roles are NOT_EVALUATED. Solidity parity covers 8 suite-wide anchor vectors, not the required 10,000 vectors; full 18,146-vector three-language parity and the required misuse suite are NOT_EVALUATED. The constant-comparison run is NOT_RETAINED. The 1,000-sample native timings are `DIAGNOSTIC_NOT_COMMON_PROTOCOL` because warmup, p90, p99, standard deviation, and at least 10 seconds of measured work are absent.
