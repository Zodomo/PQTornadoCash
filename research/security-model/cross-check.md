# Cross-check against pinned Plonky3

## Source review

The translation was made from local checkout commit `3152b14a89067c83775a8076cc262ffc48a1fd7c`, principally:

- `security/src/air.rs`, `deep.rs`, `proximity.rs`, `assumption.rs`, `fri.rs`, `grinding.rs`, and `stark.rs`;
- `uni-stark/src/security.rs` wrapper behavior;
- the source-linked ePrint references 2020/654, 2024/1553, 2025/2010, and 2025/2055.

An independent human has **not** accepted this methodology. Internal reviewer `SecurityModelReview` returned `REJECT_METHOD` with five findings, returned `REJECT_METHOD` with one remaining boundary finding on corrective round one, and returned `ACCEPT_METHOD_WITH_LIMITATIONS` with no code findings on corrective round two. All six historical findings are corrected and regression-tested. This internal methodology review is not external human cryptographic acceptance.

## v0.3 q32 reproduction

Input is `manifests/v03-q32.json`: width 190, 1,186 constraints, maximum degree 7, 210 functions (`190+16+4`), logical degree bits 8, hiding padding 1 bit, proof degree bits 9, blowup 4, binary folding, 32 queries, and 16 configured classical bits at each FRI grinding site. The project wrapper passes half the grinding value to p3-security; therefore the quantum column uses 8 bits at each site.

| Result | Independent exact bits | Floored | Pinned project output |
|---|---:|---:|---:|
| Random words | 107.997888224 | 107 | 107 |
| UDR | 37.190582247 | 37 | 37 |
| LDR / best proven | 56.201226486 | 56 | 56 |

The random-words bottleneck is DEEP-ALI, not the raw random-words FRI query expression. UDR binds at FRI query. LDR uses pinned FRI-only `m=185` selection and then binds at the 210-function batched-opening proximity term.

There is no numerical disagreement after applying the wrapper's post-hiding degree and quantum grinding convention. The independent output is more explicit in three respects:

1. it retains full floating-point values before flooring;
2. it reports classical and quantum grinding treatments side by side;
3. it prints the random-words batching omission rather than allowing `num_batched_functions=210` to appear consumed.

The third point matters because the v0.3 Rust wrapper sets `num_batched_functions=210` and then invokes `ConjecturedSecurity::compute_from_params`, but pinned `uni-stark/src/security.rs:253-275` explicitly does not consume that field. The 107-bit value therefore does not include the 210-function proximity gap.

## q48 comparisons

`manifests/v02-style-q48-width190.json` changes only queries from 32 to 48 on the fully specified width-190/210-function relation. It is a counterfactual “v0.2-style query count”, not a v0.2 relation reproduction.

| Width / batch | Queries | Random words | UDR | LDR / best proven | Status |
|---:|---:|---:|---:|---:|---|
| 190 / 210 | 32 | 107.997888224 | 37.190582247 | 56.201226486 | exact specified v0.3 inputs |
| 190 / 210 | 48 | 107.997888224 | 51.785873370 | 81.580445275 | exact counterfactual on v0.3 relation |

Random words remains at 107.997888224 because DEEP-ALI already binds; more queries cannot raise that non-query term. Both proven regimes improve monotonically, with LDR still limited by batching after the pinned FRI-only `m` selection.

The historical report documents v0.2 width 230, logical height 256, and q48, but the frozen tree intentionally removed v0.2 source and manifests. Exact v0.2 constraint count, maximum degree, quotient chunks, batching count, proof degree after hiding, and security manifest are unavailable. `manifests/legacy-v02-q48-width230-assumptions.json` therefore carries conspicuous non-equivalence omissions and substitutes v0.3-style values, including assumed 16 quotient and 4 hiding functions (batch 250). Its output is a sensitivity example only and must not be cited as reproduced v0.2 security.

## Negative and invariant checks

Focused tests establish the requested calculator properties:

- changing 210 batched functions to 1 removes the applicable proven batch term and increases LDR security;
- doubling target count subtracts one bit under the declared union-bound model;
- lowering the challenge budget lowers the cap and aggregate result where it binds;
- query sweeps from 1 through 128 are monotonic for random-words, UDR, and LDR outputs;
- impossible LDE fold domains, nonzero final polynomial logs at/above proof degree, excessive maximum arities, and ZK degree/blowup profiles are rejected; zero and `proof_degree_bits-1` final logs plus an arity valid only because of blowup are accepted;
- logical degree 8, hiding padding 1, and proof degree 9 are separately emitted and consistency-checked;
- batch derivation is a closed enum; derived counts cannot silently disagree with width + quotient + hiding functions, and explicit counts require a rationale;
- exact inner/outer composition uses the probability sum, not a minimum;
- UDR remains available when the pinned LDR `m` search has no candidate;
- LDR terms/aggregate carry the Johnson mutual-correlated-agreement condition in machine-readable status;
- target search excludes random words from recommendations and retains the actual batched-function omission;
- repeated serialization is byte-for-byte deterministic.

## Qualification outcome

The calculator reproduces the pinned integer results and its internal methodology review is `ACCEPT_METHOD_WITH_LIMITATIONS`, but external human cryptographic review remains open. All outputs remain `UNREVIEWED_RESEARCH_RESULT` for cryptographic acceptance; none receives `SECURITY_QUALIFIED_CANDIDATE`. Random words is excluded from target recommendations because its batch term is unmodeled and its status is conjectural. LDR remains conditional on mutual correlated agreement up to the Johnson bound.
