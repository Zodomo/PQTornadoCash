# PQTornadoCash — Independent Research Review

**Reviewed repository:** `Zodomo/PQTornadoCash`  
**Reviewed public commit:** `e51a5c5ccc4f50e0beb07cdf04d7f8dd258c7997`  
**Review date:** 2026-09-04  
**Disposition:** agree with `OUTCOME_D / RECOMMEND_ADDITIONAL_TARGETED_RESEARCH`; revise the interpretation of negative results and the execution gates for the next round.  
**Scope:** source-and-evidence review plus independent arithmetic sensitivity experiments. Not an audit, external human cryptographic acceptance, implementation authorization, or deployment authorization.

## 1. Bottom line

The repository provides strong evidence that the frozen v0.3 implementation is not a robust deployable design. It does **not** provide strong evidence that an efficient one-transaction PQ-oriented Classic mixer is impossible, or that the principal alternatives have been exhausted.

This distinction is the most important conclusion of this review. The research produced useful baseline measurements, a much more candid security model, preserved negative results, and a substantial reproducibility framework. However, the most consequential new relation experiments—especially a vertical AIR and a complete fixed-compression withdrawal relation—were not executed. Many branches stopped because another component had not passed security or completeness gates. A missing eligibility prerequisite is not a falsified performance hypothesis.

The immediate decision not to commission a new full product build is correct. The next program should be a **controlled experimental integration round**, with security analysis running alongside performance measurement. It should produce complete local proofs and verifier calls without pretending that those prototypes are approved for custody. It should not produce another large collection of predominantly status-only candidate records.

The most promising work remains:

1. Compare equivalent implementations before rejecting fixed-length compression on gas.
2. Build a narrow AIR against the existing H0 relation, so AIR geometry can be tested without waiting for a new hash to be accepted.
3. Complete one exact candidate hash relation and run the corresponding horizontal/vertical comparison.
4. Finish typed transcript batching and verifier cost attribution.
5. Test one alternative hiding proof backend on the same relation, rather than a synthetic upstream smoke alone.
6. Improve security accounting without confusing better bounds, changed assumptions, and actual stronger protocols.

The attached `FOLLOW_UP_RESEARCH_PLAN.md` makes these bounded work packages, with evidence requirements, stop conditions, and explicit permission to run non-custodial experiments before external cryptographic approval.

## 2. Review boundary and reproducibility

### 2.1 What was examined

The review began with the final report, executive matrix, unresolved questions, report-freeze decision, external security request, cryptanalysis packet, and reproduction instructions. It then followed important claims into the independent security calculator, FRI screening code, hash measurements and Solidity kernels, baseline verifier source, advisory results, field benchmarks, and selected candidate artifacts.

The most important reviewed sources are enumerated in `SOURCES.md`. All repository links there are pinned to the reviewed commit. This was not a line-by-line audit of every file or every candidate implementation.

### 2.2 What was and was not executed

**Executed here:** a standalone Python transcription of the visible LDR formulas, with baseline regression checks and alternative optimization objectives. The program and JSON output are included under `evidence/`.

**Not executed here:** the five repository handoff commands, the Rust suite, Foundry suite, fresh STARK generation, Solidity compilation, full evidence-manifest verification, or any network deployment. Repository reads worked through the GitHub connector, but the executable environment could not resolve GitHub for a clone and had no Rust/Foundry toolchain. Therefore all repository performance numbers below are **retained project evidence**, not numbers independently reproduced in this review.

This limitation is significant but does not prevent checking source-level inference, arithmetic, status propagation, and whether a conclusion follows from the reported experimental coverage.

### 2.3 Commit and evidence epochs

The public review target is `e51a5c5…`. The final report and internal review records refer to earlier report-freeze and measurement commits. This is not automatically a defect: evidence can legitimately be frozen before a later cleanup commit. The reviewed latest commit deletes only `old_plans/pq-tornado-classic-engineering-plan.md` and `old_reports/ENGINEERING_REPORT.md`. The governing next-generation research plan is still present at the root, and the reproduction manifest excludes the old directories. I found no basis to claim that this cleanup itself broke reproduction. [S01, S07, S08]

The next release should nevertheless publish one explicit relationship:

`public review commit → report snapshot → experiment source commit → artifact hash → command/environment`

That removes ambiguity without rewriting history or treating every file as if it were generated from the latest commit.

### 2.4 Evidence labels used in this review

- **Repository evidence:** directly supported by pinned files or retained measurements.
- **Independent calculation:** arithmetic performed here using explicitly stated formulas.
- **Inference:** a reasoned conclusion not itself measured.
- **Research recommendation:** a proposed experiment, not an assertion that it will succeed.
- **External source:** a primary publication or official specification used to check a claim.

## 3. What the baseline now establishes

### 3.1 The old single-fixture gas result was not robust

The retained 60-run baseline reports the following. These are local measurements and modeled complete-transaction totals, not public-chain receipts. [S02]

| Quantity | Retained result |
|---|---:|
| Raw A+B proof bytes, median | 208,940 |
| A+B ABI bytes, median | 209,608 |
| Part A total gas, minimum | 16,179,681 |
| Part A total gas, median | 16,664,641.5 |
| Part A total gas, maximum | 16,953,270 |
| Part A above 16,777,216 | 9 of 60 |
| Part B total gas, median | 13,959,759.5 |
| Part B total gas, maximum | 14,264,492 |
| Part B above 16,777,216 | 0 of 60 |
| Deposit execution gas | 13,991,021 |
| Internal pool CREATE gas measurement | 18,873,630 |
| Warm proving time, median | 604.969 ms |
| Warm proving time, p95 | 834.257 ms |
| Warm proving time, p99 | 1,086.470 ms |
| Median process peak RSS | 29,483,008 bytes |

Nine cap exceedances are enough to reject the claim that the present fixed split reliably fits. The empirical exceedance frequency is 15% in this particular sample. It is not a universal failure probability: sample construction, workload strata, masks, query patterns, and environment matter.

A median near the cap also matters. Even proofs that fit have inadequate margin for a product. This is a stronger result than merely observing that one previous fixture had a small margin.

### 3.2 Deployment is an independent problem

The internal CREATE measurement exceeds the protocol cap by 2,096,414 gas. It is not a top-level deployment receipt and must not be relabeled as one. Nevertheless, this is strong evidence that the current constructor path cannot be assumed deployable under the same transaction limit. The next round must measure the actual initcode transaction separately and decompose constructor hashing, storage, initcode metering, and runtime-code deposit. [S02, S27]

The project was right to investigate this. A contract whose functions can sometimes fit but whose deployment does not fit is not an operational candidate.

### 3.3 Native proving is not the dominant problem on the measured machine

The retained high-end ARM warm measurements are around 0.6 seconds, with roughly 28 MiB median peak RSS. They do not establish commodity-laptop, browser, cold-start, or portable performance. But they do establish something useful: on the measured machine, the current problem is predominantly EVM verification and proof transport, not an already-unacceptable native prover.

This creates room to trade additional off-chain work for fewer on-chain openings or cheaper verification. It also means that Flock's headline proving throughput, by itself, is not the most relevant selection metric for the current project.

### 3.4 Ethereum limits and project preferences must stay separate

EIP-7825's 16,777,216 cap is a protocol constraint. The research plan's 14M one-call limit, 12M per half, 20M combined two-call limit, 80 KiB one-call allowance, and 128 KiB two-call allowance are deliberate product/research targets. They are reasonable targets, but violating one is not proof that Ethereum execution is impossible. [S08, S27]

The 64- and 96-gas-per-byte tests should remain separately labeled scenarios unless activated on the target chain. EIP-8311 is a draft proposal. A design can fail a future-resilience preference while remaining technically possible under current rules. No candidate here currently earns a full build recommendation under either interpretation, but the distinction is necessary for honest tradeoff decisions. [S28]

## 4. What the research did especially well

The repository has improved substantially in evidence discipline.

**First, negative results are retained.** `NOT_EVALUATED`, failed builds, stopped integrations, and deferred cases are visible. The handoff does not claim an alternative exists merely because a primitive benchmark is fast.

**Second, security labels are more accurate.** The q32 Johnson result is now described as conditional rather than as an unconditional end-to-end guarantee. The random-words batching omission is explicit. Human external acceptance is not inferred from internal agent review.

**Third, the baseline was challenged with fresh data.** That exposed cap failures and constructor cost that a single canonical proof did not reveal.

**Fourth, hash and transcript roles are being analyzed separately.** The cryptanalysis packet identifies exact fields, matrices, rounds, truncation, domains, and missing role coverage. It does not simply declare Poseidon2 or Keccak “safe.”

**Fifth, proof-only aggregation preserves the correct trust boundary.** An untrusted aggregator should receive proofs, not raw note secrets. The repository does not conceal witness disclosure behind the word “batching.”

**Sixth, reproducibility tooling is defensive.** The controller uses explicit argv, an environment allowlist, isolated work directories, hashes, and no arbitrary network or signing option. These are good engineering decisions. [S07, S09]

These strengths should be preserved. The next round should improve execution coverage without weakening this honesty.

## 5. The central process problem: a qualification gate became an experimentation gate

The repository records zero implemented A1–A4 AIR alternatives and no completed structured-R1CS relation. These stopped because no compressor had cleared the required gate. The compressor gate itself depended on full parity, complete application layouts, misuse tests, and external security review. [S02, S10, S11]

The resulting dependency chain was effectively:

`no externally accepted compressor → no new AIR → no exact relation for backend → no integration → no full gas result → no candidate`

That is safe as a deployment policy. It is counterproductive as a research execution policy when the objective is to discover which construction is worth deeper review.

My previous plan contributed to this problem by not distinguishing these gates sharply enough. It appropriately prohibited premature custody integration but made some performance work contingent on qualification that the performance work was intended to help prioritize. The new plan must correct that, not simply ask the engineers to repeat the same process with more documentation.

### Correct separation

| Gate | What it authorizes | What it does not authorize |
|---|---|---|
| Specification completeness | implement an exact relation | call it secure |
| Reference correctness and bounded execution | run local performance experiments | public custody |
| Experimental integration | produce complete local hiding proofs and verifier calls | production or testnet deployment |
| Security assessment | state a scoped conditional/accepted claim | bypass operational gates |
| Build selection | write a new full engineering specification | deployment |
| Deployment approval | deploy the reviewed build under explicit conditions | future unreviewed upgrades |

A missing external cryptographic sign-off should not prevent measuring a narrow AIR for the existing H0 relation. H0 is already available and can remain clearly unqualified. Similarly, a candidate compressor can be tested locally after its exact semantics and reference correctness are established, while its structural review remains open.

The goal is not to “fail open” on safety. It is to permit **measurement without promotion**.

## 6. Security accounting: what is now correct, and what remains open

### 6.1 The q32 figures must be interpreted at their actual layer

The repository reports:

- 37 bits from the unique-decoding route without the additional Johnson correlated-agreement condition;
- 56 bits from the conditional Johnson/list-decoding route;
- 107 bits from the random-words calculation, which omits the batched-opening proximity term.

These are modeled proof-system quantities, not demonstrated attack costs. A 37-bit theorem-derived result does not exhibit a practical 2^37 attack. Nor does the word “unconditional” make the whole mixer unconditionally secure: hash assumptions, Fiat–Shamir, zero knowledge, quantum composition, code correctness, and deployment remain separate. [S12, S13, S14]

The pinned Plonky3 assumption selector explicitly labels unique decoding as not requiring conjectures and the Johnson route as requiring mutual correlated agreement up to the Johnson bound. This supports the research's more careful distinction. [S15]

### 6.2 Reproducing an upstream integer is not enough

The independent calculator is a useful translation. Its internal review corrected six issues and now records limitations. Agreement with pinned Plonky3 values establishes consistency with that implementation; it does not by itself establish theorem applicability or optimal parameter analysis. [S12]

The next review should separate:

1. arithmetic transcription;
2. mapping the actual committed matrices/openings to theorem parameters;
3. optimizing free analytical parameters;
4. composing round-by-round, random-oracle, and quantum claims;
5. interpreting lifetime exposure.

### 6.3 New finding: the LDR optimization objective leaves useful analysis on the table

The calculator chooses the proximity parameter `m` by maximizing only the minimum of the FRI query and commit terms. It then uses that selected `m` in the complete expression, including the batched-opening penalty. Its own external-review request calls attention to this choice. [S12, S14]

This is faithful to the pinned routine, but it need not maximize the complete lower bound. The batch penalty grows approximately as `(m + 1/2)^5`. A large `m` slightly improves the query-distance term but can greatly worsen the batching term.

I independently transcribed the visible formulas and evaluated the same permitted `m` range. I did not change the proof, queries, field, hash, or runtime. The resulting sensitivity is:

| Profile | FRI-only selected m | Whole-expression minimum | Full-expression selected m | Whole-expression minimum |
|---|---:|---:|---:|---:|
| q32, b4 | 185 | 56.201226486 | 23 | 71.007139340 |
| q48, b4 | 5 | 81.580445275 | 3 | 84.840828758 |
| q64, b4 | 3 | 84.840828758 | 3 | 84.840828758 |

For q32 at m=23, the query term is about 71.007 bits and the modeled batching term is about 71.105 bits, rather than choosing m=185 and letting batching fall to 56.201 bits.

This is **not** a new security theorem. It retains the conditional Johnson assumptions, the calculator's supplied hash/field caps, and all missing composition analysis. The unchanged unique-decoding result is still about 37 bits. It does not qualify q32 at 100 bits.

It is nevertheless a valuable research direction: when an analysis parameter is not part of proof generation or verification, a better justified analysis can improve the bound at zero runtime cost. A cryptographer should check that the same `m` is valid throughout all component theorems and whether a probability sum, rather than the recorded minimum, is required at a particular composition boundary.

The included script also reports an arithmetic probability-sum sensitivity. For the q32 m=23 row, summing all listed error terms gives about 70.055 bits. This is not substituted for Plonky3's round-by-round theorem; it simply makes the effect of an alternative aggregation visible. Including the subdominant epsilon terms in the batch sensitivity does not materially change that q32 result. See `evidence/ldr_objective_sensitivity.py` and its generated JSON.

### 6.4 Verify the actual batching count rather than hard-coding its explanation

The calculator uses 210 functions, derived as 190 trace columns +16 quotient chunks +4 hiding functions. The EVM query verifier separately processes arrays of 8 random openings, 194 trace openings at two points, 128 quotient-related openings, and 524 reduction terms. These are not necessarily inconsistent: coefficients, rotations, quotient chunks, and distinct polynomials are different objects. However, the correspondence needs a theorem-level derivation. [S13, S16]

Do **not** mechanically replace 210 with 524. Instead, generate a manifest from the actual committed matrices and opening requests and identify which objects the batching theorem counts. Include masks, extension-to-base decomposition, repeated evaluation points, and degree correction. This is an open verification question, not a confirmed undercount.

### 6.5 Quantum adjustments need a threat game, not a label on a column

The calculator halves the work credit for grinding at its actual site. That is clearer than granting quantum security because the protocol is hash-based. But it is not a complete QROM analysis, nor does it account for every possible quantum interaction merely by changing `g` to `g/2`.

Require separate statements for:

- algebraic/IOP soundness under classical public-coin interaction;
- hash commitment binding;
- Fiat–Shamir soundness and extraction in the selected model;
- quantum work assumptions for hash attacks and grinding;
- zero knowledge against the selected adversary;
- the final system claim.

A combined number should appear only when the composition and its losses are stated.

### 6.6 Multi-target sensitivity is useful, but not a universal formula

The project retains both proof-forgery union-bound scenarios and digest-width sensitivity models. This is useful provided the output remains explicitly a model. A list of honest historical deposits, the number of adaptive proof attempts, the number of hash invocations, and the number of independent secret-recovery targets are not interchangeable. [S10, S13]

The next security packet should define distinct games: recover any funded note, find a useful commitment collision before deposit, forge tree membership, splice A/B continuations, forge a proof, and distinguish two witness distributions. For each game, name the target count and whether the bound already accounts for oracle queries. Avoid applying a lifetime subtraction twice or treating arbitrary collision search as identical to target-preimage search.

## 7. The hash experiment is informative but not yet an architectural comparison

### 7.1 The implementation-tier mismatch is substantial

The common Solidity harness reports these retained values. [S17]

| Implementation/path | Gas |
|---|---:|
| Frozen optimized H0 complete deposit | 13,991,021 |
| Generic H0 compute-only depth-20 insertion | 127,632,688 |
| Generic H0 node | 6,376,977 |
| H3 generic width-24 node | 1,222,559 |
| H5 generic width-32 node | 2,159,231 |
| H5 generic compute-only depth-20 insertion | 43,258,198 |
| H7 generic RPO-M31 compute-only insertion | 509,474,048 |

The generic H0 computation is about 9.12 times the optimized complete deposit. This does not mean either measurement is fabricated. They measure different implementations and, in part, different workload envelopes. It does mean they cannot establish that fixed compression inherently requires 24–43M gas for a practical deposit.

The generic Poseidon kernel uses dynamic arrays, checked indexing, runtime loop bounds, virtual constant accessors, and generic modular arithmetic. The width-32 constants are selected through a large assembly switch. The production H0 implementation uses a much more specialized style. [S18, S19]

An opcode trace is needed to quantify constant dispatch, indexing, memory, arithmetic, and call/ABI costs. The large switch is a plausible contributor, not a measured attribution in this review.

The matched generic comparison still contains useful evidence: H5's twenty-node computation is about 2.95 times cheaper than generic H0's, even though H5's individual wider permutation is costlier. This supports a structural saving, not the original expectation of an elevenfold end-to-end gain. The correct next experiment is a matched-tier implementation comparison.

### 7.2 A correct mathematical mode is not a completed application relation

The compression mode is `Trunc_d(P_t(x)+x)`. That describes a primitive. The research application harness generally demands `2d` payload lanes for every role, including note and nullifier. The review packet admits that non-H0 note/nullifier cases omit the frozen scope and use replacement secret widths; empty-leaf and statement roles are incomplete. [S10, S18]

Consequently, the projected 22 permutations are not a measured complete Classic relation. The next round must finish role schemas before making a product claim.

One exact research layout worth testing is H5 with width 32 and 12-field output:

- Merkle node: 12 left +12 right +4 control lanes +4 fixed lanes.
- Note: 12 scope +8 secret +8 trapdoor +4 control lanes.
- Nullifier: 12 scope +8 secret +4 control lanes +8 fixed lanes.

This is a layout hypothesis, not approved cryptography. Scope derivation, empty leaves, parameter separation, padding/fixed lanes, feed-forward positions, and the implication of shared permutation domains must all be specified and tested. It is nevertheless sufficiently concrete to implement a non-custodial experiment; it should not remain an unresolved generic placeholder.

### 7.3 The parity and misuse gap is finite engineering work

The package contains 18,146 Rust/TypeScript matches, only eight Solidity anchors, no retained independent constant-comparison result, and no completed required misuse suite. [S11, S20]

The honest labels are good. The incomplete work should not be treated as a permanent external dependency. Engineers can retain the constant regeneration, stream the vector corpus through Solidity in chunks, and execute the role/domain/length/canonicality misuse suite. A large vector file is not a substitute for coverage across all implementations.

### 7.4 Structural attack applicability is not a break result

Some hash scorecards label a candidate as failing because exact round-skipping methods apply. The cryptanalysis packet is more careful: it says speedups are not achieved security-bit estimates and no candidate is cleared. [S10, S17]

The primary *Skipping Class* paper explicitly says an improved algebraic attack can leave a primitive above its claimed security level because of its original margin. Therefore distinguish:

1. attack family inapplicable to the exact instance;
2. applicable but cost not evaluated;
3. evaluated and below the required threshold;
4. evaluated and above threshold under named assumptions;
5. incomplete structural assessment.

This is not a recommendation to ignore the attacks. It is a recommendation not to equate category 2 with category 3. [S29]

H1 remains a useful negative control because its output width already fails the chosen generic target. H3 has little generic collision margin and deserves low priority. H5/H6 are still structurally unreviewed, not demonstrated broken.

### 7.5 H4 and H2 were stopped, not disproved

H4's `2×11+4=26` lanes do not fit width 24. That falsifies that exact four-control-lane layout. It does not prove that all width-24/11-output modes are impossible. A packed injective control encoding or another reviewed tweak layout would be a different candidate. It should not be silently substituted, but it can be evaluated later if width-24 performance warrants it.

H2 has no implemented/reviewed wide-output mode. That is a design gap, not negative performance or cryptanalysis evidence.

Neither branch should consume the next round's critical path. Their current disposition should simply be labeled accurately.

## 8. AIR geometry remains the largest untested hypothesis

The research's central AIR experiment did not happen. This is the most important gap to close. [S02]

It is not necessary to wait for H5 to be approved in order to answer whether 190-column horizontal evaluation is a poor EVM tradeoff. The existing H0 permutation and sponge relation are available. Build a vertical implementation of **the same H0 semantics**, retain the same statement and witness, and compare the proofs.

The comparison should vary only geometry first:

- horizontal whole-permutation rows;
- full-round or partial-round rows;
- a small set of lane-parallelism choices;
- explicit degree-two/three intermediates versus degree-seven constraints.

Measure width, height, number of distinct openings, constraint count and degree, quotient chunks, masks, exact proof bytes, and EVM arithmetic. Do not optimize trace height alone, and do not assume that a lower-degree AIR will automatically be cheaper: extra columns and rounds can offset the savings.

After that, run a small factorial experiment:

| | Horizontal | Vertical |
|---|---|---|
| H0 sponge | existing reference | new geometry control |
| Complete H5 compression relation | hash-change control | combined candidate |

This separates the benefit of compression from the benefit of geometry. It provides more decision value than another large parameter sweep over H0's unchanged 190-column trace.

### 8.1 The field bakeoff is useful infrastructure, not a selected field

The field harness explicitly classifies its native measurements as diagnostic: no warmup, deterministic local inputs, and some timer-scale samples. The Solidity measurements include input construction and external-call/return overhead. It does not instantiate a full PCS, because no complete alternative field/hash/MMCS tuple was frozen. That is honest and useful, but these numbers cannot yet select a proof field. [S26]

Use the operation and byte inventory of a real narrow AIR to choose one alternate field or extension experiment. Small scalar timings dominated by call overhead are less informative than representative extension dot products, FRI folds, and complete proof openings.

Distinguish changing the **challenge extension** from changing the **base field**. The former can sometimes preserve the application permutation while changing verifier arithmetic and soundness terms. The latter changes a field-native Poseidon instance; retaining the original hash then requires non-native arithmetic, while replacing the hash requires a new exact-instance security review. It is not a free substitution. Any claimed field improvement must include that cost and semantic difference.

Do not port six complete backends before answering the H0 geometry question. The next field candidate should be chosen by a measured bottleneck—for example, a challenge-field batching ceiling—not by the fastest isolated multiplication.

## 9. The FRI sweep needs methodological correction before it can rule things out

### 9.1 504,000 configurations are not 504,000 protocol experiments

The sweep is predominantly an analytical Cartesian screening of a frozen relation. Only a few anchors were generated as real proofs, including b4/q32, b4/q48, and b3/q111. Complete alternative verifier transactions were not executed. This is useful screening work but not broad implementation coverage. [S02, S21, S22]

### 9.2 Unknown full-path gas is mapped to failure

The projection code sets `completeTransactionMeasured = False` and `completeTransactionGas = None`. Both one- and two-transaction pass flags are then conditioned on that false value. The resulting status becomes `TWO_TX_FAIL` even for a numerically promising projection. [S21]

Failing to approve an unmeasured candidate is correct. Recording it as a measured or mathematical transaction failure is not. Use separate fields:

- `measurement_status = NOT_EVALUATED`;
- `model_status = PROJECTED_PASS / PROJECTED_FAIL / OUT_OF_CALIBRATION`;
- `physical_feasibility = UNKNOWN / MEASURED_PASS / MEASURED_FAIL`;
- `qualification = NOT_QUALIFIED`.

Some rows also fail explicit projected byte limits, so this status issue does not magically create a winner. It does mean categorical summaries derived from `TWO_TX_FAIL` are not independent evidence of infeasibility.

### 9.3 The cost model confuses prover-domain growth with verifier growth

The model multiplies much of verifier gas by `2^(logBlowup−4)`. Increasing the LDE domain does increase prover FFT/hashing work substantially. For a fixed query count and relation, a Merkle-opening verifier usually sees additional authentication depth, not the entire domain. Other quantities can change, so the exact behavior must be measured, but an exponential whole-verifier factor is not justified by the code's structure alone. [S21]

This can distort the ranking of high-blowup candidates, exactly where one hopes to trade off-chain work for on-chain work.

### 9.4 Folding arity and Merkle caps need real codecs

The projection reduces the number of rounds as folding arity rises but retains a simplified per-round sibling-byte term. A larger-arity fold can require more sibling values per query. Merkle-cap savings also depend on query overlap and the actual pruned frontier; they cannot always be derived by subtracting `queries × capHeight × digestBytes` independently. [S21]

These models are acceptable as initial estimates if their error is measured. They must not be used as hard impossibility bounds.

### 9.5 “Projection” and “bound” are not synonyms

The source identifies values as projections but elsewhere calls them bounds. An estimate with hand-chosen coefficients, unmodeled arity growth, or uncalibrated extrapolation is not a proven upper or lower bound. A hard elimination is justified only by an exact byte/gas result, a conservative bound with a derivation, or a known security disqualification. Everything else should prioritize the next measurement.

## 10. Transcript and verifier work should now move into an exact path

T3's challenge-boundary framing is a good direction. It groups messages without crossing Fiat–Shamir dependency boundaries. However, the packet admits that the API does not enforce the phase state machine, that the misuse oracle uses out-of-band labels, and that Rust/Solidity cross-language misuse coverage is incomplete. Its full-width continuation redesign is also not fully implemented. [S10]

The next work should not invent another transcript family. It should:

1. implement typed phases or explicit runtime states;
2. reject early sampling and missing/duplicate/out-of-order items;
3. match exact bytes and challenges across Rust, TypeScript, and Solidity;
4. verify a complete hiding proof with the changed transcript;
5. measure its isolated and integrated EVM delta;
6. complete the full-width continuation comparison without truncating authoritative values.

V9's 12/20 split projection provides a useful next measurement but is not an implemented improved verifier. Its modeled minimum margin is about 1.274M, while its complete-transaction result remains null. This does not meet the stricter product targets and does not fix q32's security. A controlled local implementation can still establish whether the split model is valid. [S23]

Keep an attribution table for parse/transcript, AIR, opening reductions, inversions, MMCS, FRI, state, payout, and ABI floor. Do not sum independently measured kernel deltas and call the result an integrated transaction.

## 11. Alternative backend dispositions

### 11.1 Hiding WHIR: advance from synthetic smoke to the same relation

The retained HidingWhirPcs smoke is positive availability evidence: a hiding upstream PCS path can execute, with an anchor-scale proof around 36.8 KB. It is not a Classic withdrawal, not the 190-column relation, and not a Solidity verifier. The reported approximately 5.6 ms cannot be compared with the full baseline prover. [S02]

This is the highest-priority alternative backend experiment. Use the same H0 relation first, then the selected compression relation. An API-fit spike must establish whether the current AIR can be used directly or needs a structured multilinear/R1CS/CCS lowering. A hiding PCS alone is not a complete hiding argument. Do not label the adapter “drop-in” until the whole public statement and witness relation verify.

### 11.2 Spartan–WHIR: execution failures are not architecture failures

Upstream native tests and standalone Solidity controls are useful. A gas script failing before measurement, license review remaining open, or a missing application adapter does not establish poor gas. Preserve exact failure logs, make a bounded compatibility/license assessment, and avoid scheduling a whole product rebuild before one complete local relation exists.

A structured relation remains preferable to introducing generic sparse-matrix authentication by default. Every matrix/lookup claim still needs sound closure.

### 11.3 STIR and Circle FRI: defer adoption, not necessarily all experiments

The lack of a reviewed hiding route is a legitimate blocker for replacing a private withdrawal proof. Non-hiding lower bounds can remain in the research corpus but must never be mistaken for usable anonymity proofs. The next round should not spend its critical path implementing a new hiding theorem unless FRI/WHIR measurements show the need.

### 11.4 Recursion: the right question is what the outer witness contains

The retained Fibonacci smoke is not evidence of a recursive hiding PQTC pipeline. The ignored `--zk` option and pin incompatibility should be treated as source-integration findings, not solved privacy.

A non-hiding outer proof may be useful if its witness is only an already-zero-knowledge inner proof and public verification data. That requires an explicit composition argument. It must not expose the original execution trace or note witness through an auxiliary path.

Most importantly, recursion does **not** repair a weak inner soundness bound. An attacker able to forge the inner proof may then generate an honest outer proof of its acceptance. A recursive candidate must have an adequately parameterized inner proof and account for both layers. It can move expensive verification off-chain, not erase its security obligations.

### 11.5 Flock: the stopped result is narrower than “Flock failed”

The retained batch-capacity record derives 48 capacity permutations for the requested 44, with four valid dummy computations. The exact attempt failed because the pinned implementation lacked `M21_FAST_SECURITY_CONFIG`. [S24]

This is a concrete upstream configuration failure. It is not a measurement showing that a 44-permutation statement is too expensive. A bounded revival would obtain an upstream-supported configuration or explicitly reviewed parameter set, retain the patch, and rerun. Guessing a security preset just to avoid the panic is prohibited.

Flock still has larger blockers for this product: exact Keccak/glue support, a complete hiding route, and EVM verification. Because native v0.3 proving is already fast on H1, Flock remains secondary to reducing on-chain work on the currently viable relation.

### 11.6 Aggregation: correct trust boundary, missing proof pipeline

The proof-only aggregation model is sound as a design boundary. But a model of duplicate nullifiers, payout ordering, censorship, or batch liveness is not a working aggregate proof. Start aggregation only once one complete individual hiding proof and a plausible outer verifier are measured. Do not collect unrelated users' note secrets to create the appearance of a cheap batch.

## 12. L2 conclusions must be kept narrow

The retained study tests source-pinned admission models and partial tooling for an ordinary signed transaction around the old combined 210 KiB shape. It does not establish that every smaller alternative, two approximately 100 KiB calls, or every target-chain configuration is inadmissible. [S02]

Separate five quantities:

1. raw proof bytes;
2. ABI calldata bytes;
3. signed transaction-envelope bytes;
4. RPC/txpool/sequencer admission limits;
5. execution and data-availability fees/limits.

A chain rejecting a 210 KiB envelope says little about a future 60 KiB proof. Two calls may also satisfy an envelope limit while failing a gas or economic target. A source-derived model is useful but not a live receipt.

The next L2 probe should be conditional on an exact candidate payload, not a synthetic distribution. It is not necessary to perform a broad live-chain bakeoff before there is a candidate worth transporting.

## 13. Reproduction and report presentation

### 13.1 `all-safe` is a consistency check, not an execution reproduction

The reproduction README explicitly says `all-safe` does not run subprocesses, builds, proofs, EVM calls, RPCs, or signing. This is good safety design. A successful result establishes inventory/metadata consistency, not cryptographic validity or gas reproduction. [S07]

Keep distinct records for:

- manifest and schema checks;
- deterministic table regeneration;
- clean builds;
- native verification of retained proofs;
- fresh proof generation;
- complete EVM execution;
- capped top-level transaction simulation;
- authorized public-chain receipts.

### 13.2 Missing component ledgers remain a material gap

The final report's proof-byte and gas-decomposition tables contain many `NOT_EVALUATED` cells even for the complete baseline. Since the parser, fixtures, and execution harness already exist, filling these is relatively bounded work. [S02]

This is necessary before deciding whether the next unit of effort should reduce columns, rounds, salts, headers, paths, array copying, transcript calls, or storage. A total proof size of 209 KB does not explain its dominant sections.

### 13.3 Candidate identifiers need a namespace

The report includes minimum-plan candidate IDs and separate backend-smoke IDs. For example, C30 can refer to the required aggregation row while a backend smoke uses C30 for STIR; C40 appears in both fallback and Circle contexts. This makes machine and human comparisons unnecessarily error-prone. [S02]

Use namespaced IDs such as `APP-H0-AIR-VERTICAL-FRI-P01`, `PCS-STIR-SMOKE-PIN1`, and `PRODUCT-AGG-N16`. A candidate identity must include relation, hash mode, proof backend, hiding configuration, parameters, implementation tier, and source revision.

### 13.4 Documentation volume is not experiment coverage

The final report is admirably explicit about missing work, but repeated templates can make dozens of entries look like dozens of tested end-to-end architectures. The executive comparison should show, for each hypothesis:

- exact implementation stage reached;
- raw measured result;
- what was not measured;
- whether the stop was scientific, engineering, administrative, or budgetary;
- the cheapest experiment that would resolve the uncertainty.

The current top-level executive CSV is primarily a field/value conclusion summary. Keep it, but add a genuine side-by-side candidate matrix and an opportunity matrix independent of deployment eligibility.

## 14. Advisory findings and operational hardening

The advisory artifact reports all executed behavioral checks passing but an overall failure due to a missing native panic boundary. The failed source check is specifically `native-catch-unwind-boundary`; the retained result does not demonstrate a false Solidity acceptance or a pool-draining proof. [S25]

This is an availability and API-hardening concern until an exact exploit shows more. Resolve it in an isolated research branch with malformed in-memory and serialized proofs, bounded decoding, checked verifier APIs, and a process containment policy.

`catch_unwind` is not a universal fix: it does not handle `panic=abort`, allocation aborts, or all resource exhaustion. Preserve structured errors at the public boundary and isolate untrusted verification when necessary. An upstream warning plus a grep failure is not an empirical proof of every claimed failure mode.

The abstract checkpoint-state model is useful but not an integrated solution. Complete full-width binding, per-nullifier/statement occupancy policy, expiry, replacement, consumer restriction, and rollback using real proofs. Measure storage costs and exceptional recovery separately from the normal two-call UX.

Part A is only a verified prefix, not a complete proof of ownership. A storage policy must not assume that every accepted prefix can complete, nor irrevocably reserve a nullifier on the strength of that prefix. Test adversarial occupation and replacement so that a storage-bounding change does not create a new withdrawal-censorship mechanism. This is a design-review requirement, not a demonstrated cheap prefix-forgery exploit.

## 15. What should be concluded about feasibility

### Supported conclusions

- v0.3 is not robustly below the transaction cap.
- Its current security analysis does not qualify it at the desired target.
- Its constructor path has a substantial deployment-cost problem.
- No alternative has a complete measured, security-qualified path.
- A new full production-style engineering build would be premature.

### Conclusions not established

- A one-transaction PQ Classic withdrawal is fundamentally impossible.
- Fixed-length Poseidon compression is intrinsically too expensive on the EVM.
- A vertical AIR cannot save enough verification work.
- Hiding WHIR cannot verify the application economically.
- Flock is infeasible because one pinned preset is missing.
- Every robust two-call or L2 route is impossible.
- Every conditional bound is unacceptable, or every primitive with an applicable attack is broken.

The correct language is **“not demonstrated on the retained evidence”**, not a general impossibility result.

## 16. Recommended next-round priorities

### Priority 0: repair the measurement and selection system

Separate unknown from failed, modeled from measured, and research-eligible from deployment-qualified. Retain all old results. Do not regenerate away the history.

### Priority 1: close bounded engineering gaps

Complete exact role schemas, constants regeneration, full cross-language parity, misuse tests, and a matched implementation-tier hash benchmark. Produce the baseline byte/gas ledgers. These do not need an external theorem to execute safely in a sandbox.

### Priority 2: test the untested causal hypothesis

Implement the H0 vertical AIR, then a complete H5 vertical relation. Produce actual hiding proofs. Measure them at fixed parameters and at separately reported security-normalized profiles.

### Priority 3: make one alternative backend comparison real

Use Hiding WHIR or a structured Spartan–HVZK-WHIR path for the same relation. Stop only at a documented concrete API/theorem/integration obstacle, not simply because the hash is not production-approved.

### Priority 4: produce at most two complete local verifier candidates

Combine measured improvements carefully and obtain exact ABI, gas, deployment, state, and prover results. A benchmark-only local candidate is an acceptable research output. It is not a v0.4 release.

### Parallel: external cryptographic review

Send focused questions with exact artifacts: the `m` objective, actual batching count, full error composition, QROM applicability, exact compressor modes, and lifetime games. Ask for scoped acceptance or rejection, not a vague blanket “is this PQ?” judgment.

## 17. Decision recommendation

Retain the existing decision token:

`RECOMMEND_ADDITIONAL_TARGETED_RESEARCH`

But change the next action from “wait for all hard gates to close before integration” to:

> Run a small set of exact, non-custodial, causally comparable integrations while security review proceeds independently. Require measured evidence before selecting a full build, and require accepted security before any deployment claim.

The project has useful infrastructure and a strong negative baseline. It has not yet measured the most promising structural alternatives. The next report should answer those questions directly, rather than return the same empty set of qualified candidates under the same dependency structure.
