# Formula translation

All source paths below refer to Plonky3 commit `3152b14a89067c83775a8076cc262ffc48a1fd7c`. The calculator retains floating-point values and floors only the displayed integer compatibility result, matching the wrapper's final `as usize` behavior. Python's IEEE-754 binary64 `log2`, `sqrt`, and exponentiation are deterministic on the supported workstation; serialized values are rounded to nine decimal places.

## Symbols

- `d = 2^proof_degree_bits`: committed trace-domain size after hiding padding.
- `rho = 2^-log_blowup`: Reed–Solomon rate.
- `n = d/rho = 2^(proof_degree_bits + log_blowup)`: LDE size.
- `q`: number of FRI queries.
- `Q = |F|`: challenge field; manifests use the conservative `log2(Q)=120` budget rather than silently deriving it.
- `c`: number of AIR constraints; `D`: maximum constraint degree; `r`: maximum OOD points per column (`max_combo`).
- `k`: number of codewords combined in the batched opening.
- `g_c`, `g_q`: configured commit/query grinding bits.
- `L+`: decoding list size.

## AIR random linear combination

Pinned source: `security/src/air.rs:1-16`.

`epsilon_ALI = L+ * c / Q`, hence

`b_ALI = log2(Q) - log2(L+) - log2(c)`.

UDR and random-words use `L+=1`. LDR uses the explicit-`m` value below. The status is conjectural only when embedded in the random-words composite; the formula itself is a direct finite-field challenge bound.

## DEEP-ALI

Pinned source: `security/src/deep.rs:1-28`.

`epsilon_DEEP = L+ * (D*(d+r-1) + (d-1)) / Q`, hence

`b_DEEP = log2(Q) - log2(L+) - log2(D*(d+r-1)+(d-1))`.

The pinned comments note that Ethereum `soundcalc` divides by `Q-d-D` and that ePrint 2024/1553 Theorem 2 uses an `L^2`-style multiplier; those differences do not bind the reproduced profile but remain source caveats.

## UDR

Pinned source: `security/src/proximity.rs:20-27,47-50` and `security/src/fri.rs:121-223`.

`rho+ = (d+r)/n`, `alpha_UDR = (1+rho+)/2`, and `L+=1`.

The query term is `b = -q*log2(alpha_UDR) + grinding`. The commit term, when folds occur, is

`b = log2(Q) - log2((folding_factor-1)*(n+1)) + grinding`.

The proximity precondition `d+r < alpha_UDR*n` is checked. The UDR composite is the minimum of AIR, DEEP, FRI query, FRI commit, batched opening, challenge ceiling, and MMCS binding terms. UDR uses no decoding conjecture.

## LDR / Johnson bound

Pinned source: `security/src/proximity.rs:29-44,65-80`, `security/src/fri.rs:145-279`, and ePrint 2025/2055 Theorem 4.2.

For each integer `m` from 3 through `min(compute_upper_m(d),1000)`:

- `alpha_m = (1+1/(2m))*sqrt(rho)`;
- `gamma_m = 1-alpha_m`;
- `L+ = (m+1/2)/sqrt(rho)`;
- the query term is `-q*log2(alpha_m)+grinding`;
- the BCHKS25 commit expression is `((2(m+1/2)^5+3(m+1/2)gamma_m rho)n/(3 rho^(3/2)) + (m+1/2)/sqrt(rho))*(folding_factor-1)/Q`;
- the alternative 2024/1553 commit bits are `log2(Q)-log2(folding_factor)-log2(n+1)-log2(2m+1)+0.5log2(rho)+grinding`.

The commit term takes the smaller bit value. Exactly like pinned `best_ldr_m`, the calculator chooses `m` maximizing `min(FRI commit, FRI query)` in the quantum-adjusted accounting, then composes the full AIR/DEEP/batch/cap report. It does not optimize the final composite instead, because doing so would not be an exact translation.

Johnson-bound status requires mutual correlated agreement up to the Johnson bound; it is not labeled “no conjectures” by pinned `SecurityAssumption` (`security/src/assumption.rs:41-56`). Every machine-readable LDR AIR, DEEP, FRI, and batching row therefore uses `conditional-theorem-johnson-correlated-agreement` and repeats the condition in its omissions. An aggregate selecting LDR carries the same status. This remains distinct from external cryptographic acceptance.

## Random words

Pinned source: `security/src/fri.rs:80-99`, ePrint 2025/2010 section 1.5.

`eta = ((log2(e)+log_blowup)*rho)/log2(Q)` and

`b_RW = q*(-log2(rho+eta)) + query_grinding`.

Pinned `security/src/fri.rs:101-143` also includes the same UDR exceptional-folding commit term. AIR and DEEP use `L+=1`. The paper/pinned comments recommend proven bounds for deployment.

Pinned `security/src/stark.rs:308-314` and `uni-stark/src/security.rs:174-183,253-275` explicitly omit the batched-opening RLC proximity term: random words models distance distribution, not the batching proximity gap. `num_batched_functions` is not read by the conjectural wrapper. Accordingly the calculator emits an `omitted-unmodeled` row with the actual function count and does not invent a bound. This makes the conjectural result optimistic for `k>1`.

## Batched-opening proximity

Pinned source: `security/src/assumption.rs:126-245` and `security/src/stark.rs:104-145`.

For UDR and `k>=2`:

`b_batch_UDR = log2(Q) - (log2(d)+log_blowup+log2(k-1))`.

For LDR at the exact `m` selected by FRI:

`b_batch_LDR = log2(Q) - log2(2(m+1/2)^5*n/(3 rho^(3/2))) - log2(k-1)`.

The second expression translates the pinned implementation's dominant BCHKS25 term. It intentionally omits the documented additive `(m+1/2)/sqrt(rho)` and subdominant `3(m+1/2)gamma rho` terms, following pinned `prox_gaps_error_jb_at_m` exactly. Removing batching (`k=1`) removes this term; tests require the applicable UDR/LDR result to change visibly.

## FRI final phase and geometry rejection

The pinned FRI soundness module has commit and query probability terms but no separate random final-polynomial term. The final degree/length condition is deterministic, so output records it as `deterministic-check` with null bit fields rather than assigning fictitious security.

Pinned `fri/src/prover.rs:88-92` additionally requires every nonzero `log_final_poly_len` to be strictly below the smallest committed polynomial degree after removing blowup; for this manifest model that is `proof_degree_bits`. Zero remains the explicit special case. The calculator also rejects a final length outside the LDE fold domain and a maximum fold arity larger than `proof_degree_bits + log_blowup - final_log`, the available LDE fold depth used by pinned FRI. It does not require divisibility by maximum arity because the field is a maximum and an actual round may fold by less. Wrapper buildability limits (`uni-stark/src/security.rs:46-72`) remain degree at most `2^log_blowup+1` without ZK and the one-tighter `2^log_blowup` with ZK. When pinned `best_ldr_m` has no valid `m`, LDR is unavailable at zero bits and UDR remains reportable.

## Hiding padding

Pinned `uni-stark/src/security.rs:244-251,326-330` says proof degree is the committed-polynomial degree after ZK padding. Manifests therefore supply all three of logical height, hiding padding bits, and proof degree, and validation enforces

`proof_degree_bits = log2(logical_trace_height) + hiding_degree_padding_bits`.

Hiding is an accounting input, not a soundness bonus. The calculator does not claim a zero-knowledge theorem.

## Grinding: classical and quantum

Pinned `security/src/grinding.rs:1-54` adds proof-of-work only to the challenge round it precedes. Classical columns add the full configured `g_c` or `g_q`. Quantum columns add half, matching the project's Grover-style square-root cost and the v0.3 wrapper's division by two before calling p3-security. No grind is credited to AIR, DEEP, batching, challenge-field, or MMCS terms.

This is a cost-model treatment, not a QROM proof. In particular, the calculator makes no theorem claim for the custom transcript's Fiat–Shamir transform.

## Caps, targets, and composition

The challenge-field ceiling and supplied MMCS classical/quantum binding assumptions cap each regime. The calculator does not derive the MMCS cap from construction internals.

For `2^t` potential proof-forgery targets, the conservative union bound subtracts `t` from every applicable per-proof bit term. Scenarios `t=0,20,32,40` are always emitted. This explicitly states the target model rather than silently treating grinding as reusable or free.

For recursive/aggregated inner and outer components with counts `a_i` and component bit bounds `b_i`, exact union-bound arithmetic is

`b_composed = -log2(sum_i a_i * 2^-b_i)`.

The implementation evaluates this with a scaled log-sum expression to avoid underflow. It does not replace the sum by `min(b_i)`, assume independence, or turn an unreviewed component into a reviewed result.
