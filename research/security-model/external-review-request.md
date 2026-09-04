# External cryptographic review request

Status: **internal methodology accepted with limitations; external human cryptographic review remains open; no independent cryptographic acceptance recorded**.

Internal reviewer `SecurityModelReview` first returned `REJECT_METHOD` with five findings, returned `REJECT_METHOD` on the first corrective review with one final-polynomial finding, and returned `ACCEPT_METHOD_WITH_LIMITATIONS` with no remaining code findings after all six were corrected. This internal result is not external human review, theorem-applicability acceptance, protocol qualification, or candidate qualification.

Please review the SP-01 calculator in this directory against Plonky3 commit `3152b14a89067c83775a8076cc262ffc48a1fd7c` and the cited papers. A review should not be inferred from repository inclusion, automated tests, source-location checks, or agreement with upstream integers.

## Internal methodology review record

| Reviewer | Round | Verdict | Findings | Disposition |
|---|---|---|---:|---|
| `SecurityModelReview` (internal agent) | Initial | `REJECT_METHOD` | 5 | Corrected and regression-tested |
| `SecurityModelReview` (internal agent) | Corrective 1 | `REJECT_METHOD` | 1 | Corrected with final-polynomial boundary regressions |
| `SecurityModelReview` (internal agent) | Corrective 2 | `ACCEPT_METHOD_WITH_LIMITATIONS` | 0 | Method accepted; external cryptographic review still open |

The accepted scope was calculator code/methodology and generated-artifact consistency. Limitations include the conjectural random-words path and its batching omission, the Johnson correlated-agreement condition, supplied MMCS/challenge assumptions, and lack of complete Fiat–Shamir/QROM and protocol-composition acceptance.

## Requested scope

1. Confirm the translations of AIR RLC, DEEP-ALI, UDR, explicit-`m` LDR, random-words, FRI commit/query phases, and batched-opening proximity terms.
2. Confirm that pinned `best_ldr_m` optimizes the FRI-only quantum-adjusted commit/query minimum before full STARK composition, and that using the selected `m` for the batching term is appropriate.
3. Assess the pinned LDR theorem/assumption labels, particularly mutual correlated agreement at the Johnson bound and the dominant-term-only batch expression.
4. Confirm that random words has no accepted batched-opening analogue and that output correctly treats `num_batched_functions` as omitted on that path rather than assigning a guessed bound.
5. Review post-ZK proof-degree accounting and the one-tighter ZK degree/blowup buildability rule.
6. Review the site-specific classical and Grover-style quantum grinding treatment. State separately whether any complete Fiat–Shamir/QROM theorem applies to the actual transcript.
7. Review the challenge-field and MMCS caps as supplied assumptions, including whether multi-target use changes them differently from the calculator's conservative uniform union bound.
8. Review the exact probability-sum implementation for recursive/aggregated inner and outer components and identify any missing extraction or composition terms.
9. Confirm the v0.3 q32 and width-190 q48 counterfactual cross-checks. Do not treat the width-230 assumptions profile as an equivalent v0.2 reproduction.
10. Re-run the negative tests and propose adversarial manifests around degree, domain, fold arity, batch count, hiding padding, query monotonicity, target counts, and floating-point boundaries.

## Expected review record

A useful response should identify reviewer, date, reviewed commit/hash, source and paper versions, commands run, disagreements with severity, required corrections, residual assumptions, and an explicit outcome: accepted methodology, accepted with conditions, or rejected. Acceptance of arithmetic must remain distinct from acceptance of protocol applicability or a deployment security target.

Until such a review is recorded and its findings are resolved, outputs remain `UNREVIEWED_RESEARCH_RESULT`; `security_qualified_candidate` remains false. The calculator does not self-award `SECURITY_QUALIFIED_CANDIDATE` under any profile.
