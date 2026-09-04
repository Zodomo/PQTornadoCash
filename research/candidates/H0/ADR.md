# ADR: H0 measurement decision

## Context

SP-10 requires a deterministic benchmark candidate without modifying frozen custody code. The only published Poseidon2 compressor reviewed here is first-lane `Trunc_d(P(x)+x)`; H7 is preserved as its published sponge.

## Decision

Retain only as compatibility and measurement control. All current sponge roles remain measurable with explicit version/tag/byte-length/element-count/aux framing.

## Rejected alternatives

No `TruncatedPermutation`, output-lane substitution, control packing, chained permutation, concatenated truncation, matrix change, constant reuse across widths, or invented RPO compressor is permitted.

## Consequences

Status remains `BENCHMARK_ONLY` and grants no security-qualified label. Promotion requires independent review of the exact field, permutation, constants, mode, constrained layouts, multi-target model, and quantum assumptions.

## Measurement profile

Solidity gas and size evidence is comparable under the canonical profile only: solc 0.8.30, Prague EVM, optimizer enabled with 200 runs, and via-IR enabled. Measurements from any other profile do not satisfy this ADR.

## AIR gate comparison

All five gates are conjunctive; AIR work remains stopped unless every gate passes.

- 5× node-permutation reduction: FAIL — H0 uses 11 node permutations; H0 uses 11; 1.000× reduction.
- Complete direct deposit below 4,000,000 gas: FAIL — frozen H0 direct deposit is 13,991,021 gas against the exclusive 4,000,000 gas limit.
- Generic security of at least 100 bits: NOT PASSED — no applicable compression-mode generic quantum ceiling is available.
- No structural attack: NOT PASSED — H0 is the baseline and makes no replacement claim.
- External review: NOT PASSED — the exact construction has not been externally reviewed.

Overall: **FAIL**. This candidate remains stopped from AIR work. Numeric evidence is `research/candidates/hash-compression-common/gas/results.json`. The separately retained synthetic depth-20 root-update gas is not a direct-deposit measurement.

## Negative evidence and unmeasured scope

H0 retains only baseline framing evidence. Empty-leaf and statement roles are NOT_EVALUATED. Solidity parity covers 8 suite-wide anchor vectors, not the 18,146-vector bundle; full three-language parity and the required misuse suite are NOT_EVALUATED. The constant-comparison run is NOT_RETAINED.
