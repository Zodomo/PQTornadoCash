# Security calculator decision record

## Status

Internal reviewer `SecurityModelReview` returned `ACCEPT_METHOD_WITH_LIMITATIONS` after confirming all six historical findings were resolved. External human cryptographic review remains open. This internal methodology verdict is not cryptographic acceptance, protocol qualification, or candidate qualification.

## Context

The initial methodology review confirmed q32/q48 arithmetic but rejected grading use because five edge-case and machine-label defects could hide assumptions or reject valid manifests. The first corrective review confirmed those five fixes and found one remaining pinned-prover final-polynomial buildability defect. All six corrections below are fail-closed and preserve negative outcomes.

The final corrective review found no remaining code findings and accepted the implementation methodology with limitations. Its limits preserve every conjectural/conditional label and require external cryptographic applicability review before qualification.

## Decisions

### Batch-count provenance is a closed enum

`batch_count_derivation` accepts only:

- `relation_plus_quotient_plus_hiding`, which enforces `num_batched_functions = relation_width + quotient_chunks + hiding_random_functions`; or
- `explicit`, which requires a non-empty `batch_count_rationale`.

Missing, misspelled, or unknown modes are rejected. Explicit mode exists for genuinely standalone/unbatched analyses, not as a silent escape hatch.

### FRI maximum arity is checked at the LDE height

Available fold depth is `proof_degree_bits + fri_log_blowup - fri_log_final_poly_len`. Final length may not exceed that LDE domain, and maximum log arity may not exceed the available depth. Divisibility by maximum arity is not required because pinned FRI can reduce an actual round's arity. This accepts, for example, proof degree 2 + blowup 1 + final log 0 + maximum arity 3.

### Final-polynomial degree matches the pinned prover

Pinned `fri/src/prover.rs:88-92` treats zero specially and otherwise asserts that the smallest committed polynomial height is strictly greater than `log_final_poly_len + log_blowup`. In this manifest model, nonzero `fri_log_final_poly_len` must therefore be strictly below `proof_degree_bits`. The highest positive valid boundary is `proof_degree_bits-1`; equality and larger values are rejected even when they remain below the LDE height.

### UDR survives absent LDR

Pinned `best_ldr_m` may return no `m` for a small trace. The calculator emits LDR as unavailable with zero bits and an explicit omission, while preserving the independently valid UDR report and allowing best-proven selection to choose UDR. Absence of one theorem regime is not a malformed manifest.

### Johnson-bound conditions are machine-readable

LDR AIR, DEEP, FRI query, FRI commit, and batching terms use `conditional-theorem-johnson-correlated-agreement`. Their omissions and the regime `assumptions` state that mutual correlated agreement up to the Johnson bound is required. If an aggregate selects LDR, its selected proof status and conditional assumptions carry through. “Best proven” remains the upstream-compatible name for `max(UDR,LDR)`, not a claim that the Johnson application is unconditional.

### Random words is excluded from target recommendations

Target search may show random-words arithmetic for comparison, but each result is labeled `conjectural-random-words`, repeats the actual `num_batched_functions`, says batching is unmodeled, and sets target recommendation to `excluded-conjectural-and-batched-opening-unmodeled`. The artifact also sets `random_words_eligible_for_target_recommendation=false`.

## Consequences

Adversarial regression tests lock down all six decisions, including zero/highest-valid/equal/above final-polynomial boundaries. Checked-in JSON, CSV, text, and target artifacts are deterministic. Both prior rejections remain visible in `status.json`; the final internal verdict is `ACCEPT_METHOD_WITH_LIMITATIONS`. Outputs remain `UNREVIEWED_RESEARCH_RESULT` with respect to external cryptographic acceptance, and no candidate is security-qualified.
