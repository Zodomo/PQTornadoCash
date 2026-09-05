# R2-01 Security model review

**Scope:** F04/F09/F11 and work package R2-01. Source review and executable arithmetic/reduced-round research, **not human cryptographic acceptance**. All runtime experiment results belong under `outputs/`; this document does not claim those commands were executed during concurrent implementation. Old calculators, prior outputs, original findings and frozen protocol code remain untouched.

| Axis | Disposition |
|---|---|
| Specification | Explicit three-path formulas, exact-role attack matrix, PCS inventory and threat games |
| Correctness | Runnable arithmetic/source-accounting regressions; result file records actual execution only |
| Privacy | Hiding configuration is not a composed zero-knowledge proof |
| Security | `SECURITY_NOT_QUALIFIED`; conditional analysis, unresolved exact-instance costs and QROM |
| Performance | Analytical bounds/sensitivities; reduced-round algebra is not measured full attack cost |
| Stage | Calculator plus reduced-round experiment; no verifier deployment |
| Promotion | Not promoted, no custody/public-chain authorization, no human acceptance fabricated |

## 1. Three paths, preserved rather than reconciled by editing

1. `rust/` calls **unmodified** Plonky3 `3152b14a89067c83775a8076cc262ffc48a1fd7c`: direct `proven_security_report`, `best_ldr_m`, all allowed-m FRI terms, and `ProvenSecurity`/`ConjecturedSecurity` integer APIs. Input profiles are explicit JSON, not fixed to the horizontal AIR. The binary emits both ordinary grinding and quantum-grinding-only rows. Exact upstream report objects are retained.
2. `run.py` imports the **unchanged** project `research/security-model/calculator/security_calculator.py`; saves its complete output and compares applicable per-m terms. That version chooses m using quantum-adjusted FRI-only terms even when presenting its classical aggregate. The direct native classical selector is allowed to differ; it is not silently forced to match.
3. `r2-full-objective-v1` independently evaluates every allowed m, both grinding models, both epsilon variants, and three objectives: FRI-only minimum, full minimum and arithmetic error-sum. It never changes paths 1 or 2. The independent reviewer script is also imported unchanged and its asserted reference output retained.

The complete run compares native quantum-adjusted UDR/LDR decimals and selected m to the project's independent path. All-m independent/project comparisons tolerate only rounding at 1e-7; q32/q48/q64 reference cases use 1e-8. Failed checks abort, never manufacture a successful results file. Re-running should use a fresh output directory so a prior successful result cannot be confused with a failing later run.

### Formulas and composition boundaries

Let k=2^proof_degree_bits, n=k*2^b, rho=2^-b, s=m+1/2,
alpha=(1+1/(2m))*sqrt(rho), gamma=1-alpha, L=s/sqrt(rho).
The copied upstream search is m=3 through min(ceil(1/[2(sqrt((k+2)/k)-1)]),1000).
Keep the strict condition k+max_combo < alpha*n, gamma in (0,1), and whether m is in that search range. The cap1000 is an analysis implementation cap, not a universal theorem restriction.

- AIR: f-log2(L*constraints).
- DEEP: f-log2(L*(degree*(k+max_combo-1)+k-1)).
- FRI query: -q*log2(alpha)+query grinding credit.
- epsilon_dominant = 2*s^5*n/(3*rho^(3/2)).
- epsilon_full = epsilon_dominant + s*gamma*n/sqrt(rho) + s/sqrt(rho).
- FRI commit linear: f-log2(max(epsilon_full*(2^fold_log-1),1)).
- FRI commit alternative: f-fold_log-log2(n+1)-log2(2m+1)+(1/2)log2(rho).
- FRI commit is their minimum plus commit grinding credit.
- Batched proximity: f-log2(epsilon_variant)-log2(num_functions-1), omitted only when num_functions<2.
- Explicit caps: the supplied challenge budget and MMCS binding assumption. These are not derived primitive security.

The recorded aggregate is min component bits. Separately retain -log2(sum_i 2^-b_i), using stable scaled summation. The latter includes caps as an arithmetic diagnostic: it is **not** an assertion that field/MMCS caps are independent additive events or that the round-by-round soundness theorem can be replaced by a union sum. Grinding credit is g classically and g/2 in the heuristic quantum-work adjustment; other bits are not globally halved. There is no QROM theorem hiding inside this operation.

### Required reference sensitivity (expected, not claimed newly executed here)

| b4 profile | FRI-only m | Full minimum at FRI m | Full-min m | Full minimum |
|---|---:|---:|---:|---:|
| q32 | 185 | 56.201226486 | 23 | 71.007139340 |
| q48 | 5 | 81.580445275 | 3 | 84.840828758 |
| q64 | 3 | 84.840828758 | 3 | 84.840828758 |

At q32/m23 the reference's arithmetic error sum is about70.055 bits. q32 UDR remains about37.190582247 bits; better Johnson accounting neither improves that route nor certifies100-bit system security. Full epsilon produces separately labeled results, not overwritten dominant-only artifacts. All allowed m, not just winners, remain in CSV/JSON. A mathematical lower bound on modeled soundness is not an exhibited attack at that exponent.

### m has no runtime role

`p3/security/src/fri.rs:254-279` chooses m exclusively for error accounting. Runtime `crates/pqtc-stark/src/lib.rs:92-109` constructs `FriParameters` from blowup, final length, arity, q, commit/query work, MMCS and random codewords; there is no m member. Native `query.rs:302-376` and Solidity opening/FRI paths consume no m. The R2 sensitivity changes only calculator selection and serializes no new proof parameter. The runner pins these unchanged runtime source files. This establishes **no protocol/runtime change**, not a newly measured gas saving: a better justified analytical bound would have zero runtime overhead, while still requiring theorem applicability review.

### Candidate and normalized support

`--shapes FILE` accepts an array, `{ "shapes": [...] }`, or one AIR-exported `shape.json` object; repeat the flag for C1/C3 files. Each shape requires candidate_id, logical_trace_height, proof_degree_bits, relation_width, num_constraints, max_constraint_degree, max_combo, quotient_chunks, hiding_random_functions, num_batched_functions. Extra commitment matrices/preprocessed columns are rejected rather than ignored. Current base AIR inventory handles one or two rotation points, extension degree4, one hiding padding bit, no committed preprocessing. C1/C3 periodic public schedules are not committed polynomials; symbolic constraints must nevertheless include their degree effects.

Optional `observed_input_matrices` are native proof-derived rows `{commitment,matrix,base_width,lde_height,opening_points}` in random/trace/quotient order and are checked against the source inventory. Source-derived versus runtime-observed inventories remain labeled differently. `normalized-profiles.json` independently searches q1..256 for b3/b4/b5, target100, in UDR and full-objective conditional Johnson models. First target-reaching q or best unattained plateau is emitted. `TARGET_UNREACHABLE_IN_DECLARED_SWEEP` is not an architecture failure. No q32 weak-control row is labeled security normalized.

## 2. Actual PCS objects: 210 is not 330 is not 524

Source: pinned `fri/src/hiding_pcs.rs:110-135,190-258,337-362,443-462`; `uni-stark/src/prover.rs:186-215,298-332,367-409`; repository `query.rs:302-376`; Solidity `PQTCQueryVerifier.sol:217-237`.

The baseline logical trace has256 rows. Hiding trace interleaving gives degree<512 and b4 LDE height8192. There are **three input commitments, eighteen matrices**, in FRI opening order random, trace, quotient:

| Commitment | Matrices | Original/data coefficient width | Appended random width | Committed width | Points | Alpha reductions |
|---|---:|---:|---:|---:|---:|---:|
| Random batch polynomial |1|4 base coefficients|4|8|zeta|8|
| Trace |1|190|4|194|zeta and zeta*g256|388|
| Quotient chunks |16|4 each|4 each|8 each|zeta|128|
| Total |18|258|72|330|not one global point count|524|

Random commitment generation directly invokes the inner PCS on512 rows of width `Challenge::DIMENSION + num_random_codewords`; it does not append padding a second time. A quotient chunk has four base-field coefficient columns for one extension-valued polynomial. Its four additional random codewords are genuinely additional committed base columns. Quotient masks are vanishing-polynomial additions with the final chunk's mask correlated to earlier masks by Lagrange normalization constants; those are **not** additional separately committed columns. Trace row interleaving supplies randomness within each original polynomial as well as four appended polynomials.

All committed input LDEs reach8192 rows. Quotient chunk input evaluations have256 rows; masking raises degree to<512. The reduction `(f(z)-f(X))/(z-X)` lowers degree by one. The second trace rotation is another reduction of the same194 polynomials, not another194 committed polynomials. Native/Solidity powers are consecutive alpha^0..alpha^523: random0..7; trace-local8..201; trace-next202..395; quotient396..523. Eight MMCS salt fields per authenticated input row are not polynomial columns and never consume these alpha powers. FRI round commitments are commitments to folded reduction codewords, not additional functions in this initial batch count.

The manifest's210 =190 trace +16 extension quotient chunks +4 hiding functions is the **pinned nominal convention**, not a derivation accounting for all base masks.330 =190 trace +4 random coefficients +64 quotient coefficients +72 appended codewords.524 =330+194 repeated trace evaluations. They count different things. The theorem API says committed codewords random-linearly combined; the actual implementation draws powers across polynomial/point pairs, and quotient coefficients/masks and degree correction complicate the exact mapping. The inventory therefore retains all three as **sensitivity interpretations**, not a confirmed bug or silent correction. A reviewer must decide whether the proximity theorem counts base polynomials, extension-combined polynomials, point-specific reduced functions, or a proven regrouping, and show the coefficients have the required distribution despite correlated masks and common alpha.

## 3. Eight games, not one lifetime subtraction

`threat-games.json` contains one explicit sheet per required game: funded-note secret recovery, useful commitment collision/double spending, false accumulator membership, nullifier aliasing, proof forgery, continuation substitution, witness indistinguishability, and inner/outer composition. Each names adversary, public inputs, oracle access, budgets, targets, advantage expression, work-factor interpretation, assumptions, lifetime and decisive task. Generated CSV preserves the same fields.

Eight independent uniform canonical BabyBear limbs give h=8*log2(2013265921), about247.255 bits, not256. A secret and trapdoor jointly have16*log2(p) bits when independent. This does not automatically make note recovery a secret-only Grover predicate: an unspent commitment does not expose the unknown trapdoor. A useful collision must admit valid witnesses with distinct spendable nullifiers; arbitrary digest equality is insufficient. Adaptive forgery attempts, live note targets, hash calls and historical deposits must never be substituted for one another. Witness indistinguishability is a distinguishing advantage, not preimage hardness. A weak inner proof can be honestly wrapped; soundness bits are never added across layers.

## 4. Exact H0/H5/H6 attack applicability

`packet.py` reads the frozen constants artifact and new H5 spec; emits full lane layouts, matrices, constants, rounds, domains, feed-forward and extraction with every attack row. H0 is the **exact** frozen P2BB512 framing including scope/payout/statement, not the old generic abbreviated role benchmark. H5 is R2-H5-complete-v1 (domains1..7/version2001). H6 is explicitly **only the historical node-shaped comparator**, not an invented complete relation. H3/H4 are not reopened.

Application permutation field p=2013265921, S-box7, no application extension. H0 width16 uses RF8/RP13, rate4/capacity12, four sequential4-lane squeezes. H5/H6 width32 use RF8/RP30 and retain the first12/14 feed-forward lanes. H5 note scope/secret/trapdoor placement differs from node/empty/nullifier/control placement. Scope/payout/statement use a length/chunk/domain-framed chain, requiring a composed-mode review beyond one compression call. Node scope is transitive through scoped leaves. Encoding injectivity is not finite-digest or chaining injectivity.

### Primary-source applicability corrections

- [2025/954](https://eprint.iacr.org/2025/954), especially sections5–7: finite partial-round subspace trails are structurally relevant. Corrected Groebner models can be nonregular; quotient dimension/solving costs remain assumptions. Use **APPLICABLE_COST_UNKNOWN** for that attack family, not a demonstrated below-target result.
- [2026/306](https://eprint.iacr.org/2026/306), Lemmas3.2/3.6/4.5 and sections4–6: enumerated widths stop at24. H5/H6 width32 and constrained controls are not an exact evaluated theorem instance. The paper's displayed4x4 matrix differs from the pinned Horizon matrix: it uses rows (5,7,1,3),(4,6,1,1),(1,3,5,7),(1,1,4,6), while this implementation uses (2,3,1,1),(1,2,3,1),(1,1,2,3),(3,1,1,2). Both have the outer tensor structure, but this is not license to copy skip tables blindly. Its sponge numerical attacks assume at least two absorptions and **one squeeze**; H0 uses four squeezes. Status: **APPLICABILITY_INCOMPLETE** for full exact modes. A reported2^106 improvement is not106-bit attack security and the paper explicitly does not claim its recommended instances broken.
- [2026/1692](https://eprint.iacr.org/2026/1692), sections5–7: the constructive operational demonstrations use **one** initial full round before the partial layer, not four initial full rounds as in these instances. Satisfying input constraints backward through additional nonlinear full rounds is a missing step. Do not subtract t-2k from every full-mode degree formula and claim a break. Status: **APPLICABILITY_INCOMPLETE**, not inapplicable by mere family name.

Exact extracted source text is hash-pinned under `sources/`. Direct PDF byte retrieval returned403; the retained pin is reader-extracted text, **not** a false PDF checksum or reviewer signature. OCR formulas require checking against the paper's rendered mathematics before external theorem acceptance.

All concrete attack costs/memory and structural margins remain null where uncomputed. Ideal BHT output and Grover output arithmetic are separate **oracle-model benchmarks**, not lower bounds. H5 output-only ideal collision exponent is about123.628 and H6 about144.232; H0's output width alone ignores capacity and multi-squeeze structure. No positive quantum qualification follows.

### Concrete reduced-instance experiment

`reduced_instance.py` constructs, over **the real BabyBear prime and exact width32 first-round constants**, a4-dimensional affine family in two unconstrained payload blocks for both H5 and H6 node layouts. With all controls fixed, solve

`3*M4*U + 2*M4*S_other + C_block0 + C_block1 = 0`.

Inputs `(U+X,-X,other-fixed-blocks)` then have opposite first-round pre-S-box blocks. The odd seventh power preserves cancellation; the tensor linear layer confines output differences to those two blocks.257 deterministic samples per layout retain full input/pre-S-box/output/feed-forward witnesses. A second-round counterexample is required to show the gadget is **not automatically a multi-round invariant**. This is a bounded concrete mechanism experiment, not a CICO solution, full-round preimage, collision or funded-note attack. It never guesses a full attack work factor. The relevant external task is extend or falsify this gadget under all rounds and exact useful-output constraints, with a solver/resource bound.

## 5. External acceptance and decisive gates

`EXTERNAL_REVIEW_REQUEST.md` gives finite deliverables, not an unbounded request to audit everything. It includes the unresolved reference mismatch: upstream comments call2024/1553 a STARK/FRI soundness paper while the independent source index identifies that ePrint as *STARK-based Signatures from the RPO Permutation*. Resolve title/version/theorem identity before treating comments as a proof citation. [2025/2055](https://eprint.iacr.org/2025/2055) establishes improved proximity gaps but does not by itself instantiate every mutual correlated-agreement/QROM/zero-knowledge claim of this protocol.

Research continuation does not require security qualification. Stop an exact candidate only for an evidenced useful below-target attack or irreparable relation flaw. Unknown attack cost, incomplete external review or a conditional-bound ceiling cannot alone prohibit isolated measurements.

## 6. Execution and artifacts

From repository root, with a sanitized environment/toolchain and a distinct target directory (Main runs after concurrent source edits settle):

```sh
env CARGO_TARGET_DIR=research/r2/security/target cargo build --release --manifest-path research/r2/security/rust/Cargo.toml
python3 research/r2/security/run.py --pinned-binary research/r2/security/target/release/pqtc-r2-security-pinned --output research/r2/security/outputs
```

Append `--shapes PATH_TO_C1_C3_SHAPES.json` for actual AIR exports. No environment secrets are printed; child process inherits only allowlisted toolchain/thread variables. No network/chain access is required by the calculator. `--arithmetic-only` is deliberately marked partial and cannot masquerade as a three-path result. `python3 research/r2/security/reduced_instance.py` runs only the bounded mechanism experiment. Arithmetic and source-accounting assertions live in the main runner; no separate broad test framework is needed.

Expected files after an actual successful run: `results.json`, `profiles.json`, `pinned-upstream.json`, raw pinned stdout/stderr logs, complete `translation.json`, reviewer `supplied-sensitivity.json`, `all-terms.csv/json`, `summary.csv/json`, `normalized-profiles.csv/json`, `pcs-inventory.json`, `pcs-matrices.csv`, `reduced-instance.json`, `attack-matrix.csv/json`, `threat-games.csv/json`, `exact-role-layouts.json`, `entropy.json`. No STARK proof is generated by security accounting, so no fake proof artifact is emitted; reduced-round full witnesses are the concrete experiment artifacts. Main owns actual run provenance, integration and final findings updates.
