# PQTornado next-generation research report

## 1. Executive conclusion

**Outcome:** `OUTCOME_D` — no new full build yet. **Recommendation:** `RECOMMEND_ADDITIONAL_TARGETED_RESEARCH`. The separately recorded SP-80 frontier is `CURRENT_RESEARCH_FRONTIER_NO_VIABLE_NEXT_BUILD`. There are zero security-qualified candidates, zero eligible finalists, and zero complete prototypes. [SP80]

- **One-transaction feasibility:** not demonstrated. The frozen baseline fails; every theorem-feasible hiding-FRI frontier row also fails the robust two-transaction filter, and no integrated alternative exists. [BASE] [CP3]
- **Best candidate and exact measured envelope:** no best eligible candidate exists. The only complete reference is C00, not a candidate for promotion: fresh raw proof median **208,940 B**, ABI median **209,608 B**, Part-A active-total median **16,664,641.5 gas** with **9 of 60** over the active cap, and Part-B active-total median **13,959,759.5 gas** with **0 of 60** over it. These are C00 measurements, not a new architecture envelope. [BASE]
- **Security status and lowest binding term:** not security-qualified and external cryptographic acceptance is open. For q32, the random-words estimate is **107 bits** and conjectural; the theorem-derived Johnson/list-decoding term is **56 bits** and conditional on correlated agreement; the unconditional unique-decoding regime is **37 bits**. The conservative binding result is therefore below the required security target. [CP1] [SEC]
- **Deposit cost:** the exact H0 direct deposit measured **13,991,021 execution gas**, above the research deposit UX gate; higher-arity alternatives were stopped. [GAS] [SP11]
- **Proof bytes:** C00 median raw proof and ABI sizes are the values above. They are distributions over fresh retained runs, not worst-case bounds; maximum proof length remains unresolved. [BASE]
- **Prover latency/RSS:** C00 H1 warm-only proof wall-time median is **604.969 ms**, p95 **834.257 ms**, and peak-RSS median **29,483,008 B**. Cold H1, H2, H3, portability, cancellation, and recovery were not evaluated. [BASE] [SP73]
- **Current/future gas floors:** the retained C00 records contain computed scenario distributions. Part A current/64/96 p50 is **16,664,641.5 / 16,664,641.5 / 16,664,641.5 gas** (each range **16,179,681–16,953,270**); Part B is **13,959,759.5 / 13,959,759.5 / 13,959,759.5 gas** (each range **13,333,063–14,264,492**). The future values are retained computed scenarios, not active-network receipts; all recorded floors were non-binding, and no new integrated candidate has an evaluated distribution. [RUN_INDEX] [PLAN]
- **Code/deployment status:** research components and state harnesses exist, but no integrated finalist/prototype exists and deployment is prohibited. C00 runtime/initcode size checks pass, while its pool internal CREATE measured **18,873,630 gas** and exact top-level deployment remains `NOT_EVALUATED`. [BASE] [SP80]
- **Full-plan decision:** a full new engineering plan is **not warranted**. Only blocker-closing, source-pinned targeted research is warranted.
- **Three largest unresolved risks:** (1) no externally accepted complete composed security/QROM/structural analysis; (2) no accepted fixed-compression relation feeding a hiding integrated proof; (3) no exact integrated transaction/deployment/prover envelope across required schedules and hardware. [CP4]

`PASS` means the named spike scope passed, never global qualification. `CONDITIONAL` means useful evidence with an unmet dependency. `FAIL` means a required gate failed. `DEFERRED` means work was intentionally not completed because a prerequisite or maturity gate was absent. `NOT_EVALUATED` is unknown and is never interpreted as zero. `BENCHMARK_ONLY` and projections are non-integrated diagnostics. Internal review is not external cryptographic acceptance.

## 2. Scope and evidence boundary

This report is standalone and frozen to committed evidence through the SP-91 clean detached snapshot at `e318928de5a5aff0bb0a4c0f92c03cb8eea13830`. [SP91] Its allowed basis is retained run records, generated summaries, candidate package status/results, SP-90 scorecards, checkpoints one through four, and the SP-91 record. It excludes private discussion, uncommitted observations, and any conversion of projections or isolated component diagnostics into integrated measurements.

The active hard-cap model is EIP-7825 at **16,777,216 transaction gas**; the current calldata-floor model is EIP-7623; EIP-7976 at **64 gas/byte** and EIP-8311 at **96 gas/byte** are future sensitivity scenarios. EIP-170 bounds runtime code and EIP-3860 bounds/meters initcode. The report's hard research gates are stricter: complete one-call withdrawal no more than **14.0M gas** under each schedule, exact ABI no more than **80 KiB**, runtime module no more than **22,000 B**, and each deployment no more than **14.0M gas**. Robust two-call requires each call no more than **12.0M gas**, combined no more than **20.0M gas**, combined ABI no more than **128 KiB**, bounded state, cleanup, and value movement only after complete verification. [PLAN]

Security qualification requires a conservative composed result meeting the plan target after quantum, composition, batching, and multi-target adjustments, plus hiding, transcript ordering, exact-instance structural analysis, statement binding, and explicit QROM status. A generic ceiling or conjectural estimate is necessary evidence, not acceptance. No component or bundle met this definition. [PLAN] [SP80]

## 3. Reproducibility manifest

| Field | Content |
|---|---|
| Spike ID | SP-91 |
| Hypothesis | A clean snapshot can reproduce the fail-closed decision. |
| Candidate IDs | C00 and minimum matrix C00–C40 |
| Source commits | e318928de5a5aff0bb0a4c0f92c03cb8eea13830 |
| Completed scope | Offline safe checks and evidence-chain reproduction. |
| Omitted scope | Fresh integrated finalist proof/verifier/transaction; none existed. |
| Gate result | PASS |
| Primary evidence | research/reproduction/independent-result.json |
| Security status | External cryptographic review remains open. |
| Operational status | Offline; no network or secret inputs. |
| Recommendation | Retain Outcome D; do not infer a finalist. |

### Methodology

Run registered offline checks from a clean detached worktree and compare deterministic products.

### Exact implementation

The reproducer validates the pinned inventory, run-record synthesis, scorecards, bundle gate, and stopped dependency states without network actions.

### Raw results

The snapshot inventory contained **1,886 files**, **60 authoritative baseline records**, **47 research records**, **54 ledger outputs**, **79 SP-90 outputs**, **62 scorecards**, **8 Pareto axes**, and **6 blocked bundles**. [SP91]

### Confidence intervals/distributions

This is an inventory/check result, not a statistical sample and has no confidence interval.

### Comparison with baseline

It reproduces C00 and the zero-finalist decision; it does not produce a new proof path.

### Confounders

Committed caches/toolchains can affect runnable commands; the safe checks explicitly avoid subprocess and network work where recorded.

### Failures

No eligible finalist existed to rebuild. That absence is a reproduced negative result, not a skipped success.

### Interpretation

The reproducibility manifest proves custody of committed evidence, not cryptographic correctness.

### Artifact paths

- `research/reproduction/independent-result.json`
- `research/reproduction/command-registry.json`
- `research/reproduction/evidence-manifest.json`

## 4. v0.1–v0.3 baseline chronology

v0.1 and v0.2 are historical context only; their report-era claims are not relabeled as current measurements. v0.3 is the frozen reproducible reference using P2BB512, a horizontal AIR, and hiding FRI q32. SP-00 regenerated fresh evidence, corrected the security interpretation, and failed the baseline gate. SP-01 separated conjectural random-words, conditional list-decoding, and unconditional unique-decoding claims. Checkpoint one approved the method freeze only, with integration forbidden. [CP1]

The chronology therefore ends at a failed reference, not a launch point: later components compare against C00 while retaining their own evidence classes.

## 5. Baseline reproduction results

| Field | Content |
|---|---|
| Spike ID | SP-00 |
| Hypothesis | Frozen v0.3 can be reproduced and clear current gates. |
| Candidate IDs | C00/v03-baseline |
| Source commits | d956ac0a7cd878b200be240fa8fd9a1a3da09d30 |
| Completed scope | Fresh native proofs, native verification, A/B Foundry calls, gas/byte/prover distributions, size checks. |
| Omitted scope | Complete second-client coverage, mined receipts, exact top-level deployment, worst-case proof bound. |
| Gate result | FAIL |
| Primary evidence | research/candidates/v03-baseline/gas/measured-summary.json |
| Security status | q32 below qualification under theorem-derived terms; external review open. |
| Operational status | Reference only; public network prohibited. |
| Recommendation | Keep as frozen negative baseline. |

### Methodology

Use the frozen corpus and fixed vectors to produce fresh proofs; report population standard deviation and interpolation percentiles over retained runs.

### Exact implementation

Pinned Rust prover/verifier plus complete local Foundry pool calls for Part A and Part B; every run retains proof, calldata, gas, and hardware records.

### Raw results

Across **60 runs**, raw proof p50 was **208,940 B** (min **198,052**, max **213,804**); ABI p50 **209,608 B**. Retained computed transaction-scenario p50s for current/64/96 were Part A **16,664,641.5/16,664,641.5/16,664,641.5 gas** and Part B **13,959,759.5/13,959,759.5/13,959,759.5 gas**; future schedules are computed scenarios, not new receipts. [BASE] [RUN_INDEX]

### Confidence intervals/distributions

Proof p95 **213,112.8 B**, p99 **213,766.24 B**, population σ **3,456.49 B**; Part-A total p95 **16,848,167.7 gas** and Part-B total p95 **14,124,328.2 gas**. These are empirical distributions, not worst-case bounds. [BASE]

### Comparison with baseline

The reproduced Part-B total median differs from the prior report by -1.036%; cause was not isolated. Deposit matched the report exactly. [BASE]

### Confounders

Compiler/harness versus proof-variation attribution remains unresolved; second-client coverage is partial and top-level deployment lacks calldata distribution/receipt evidence.

### Failures

Part A exceeded the active cap in **9 of 60** runs; pool internal CREATE exceeded it; future schedule and worst-case gates remain unpassed. [BASE]

### Interpretation

Correct native/EVM parity does not rescue a security, gas, deployment, or evidence-completeness failure.

### Artifact paths

- `research/candidates/v03-baseline/status.json`
- `research/candidates/v03-baseline/gas/measured-summary.json`
- `research/summaries/v03-distribution.csv`
- `research/runs/v03-*.json`

## 6. Security model and corrected v0.3 interpretation

| Field | Content |
|---|---|
| Spike ID | SP-01 |
| Hypothesis | Independent accounting can identify the conservative v0.3 security floor. |
| Candidate IDs | C00 q32; C01 q48 comparator |
| Source commits | d956ac0a7cd878b200be240fa8fd9a1a3da09d30 |
| Completed scope | Calculator, theorem regimes, composition omissions, internal method review. |
| Omitted scope | External human cryptographic acceptance, complete QROM/Fiat–Shamir composition, structural MMCS analysis. |
| Gate result | CONDITIONAL |
| Primary evidence | research/security-model/v03-q32.json |
| Security status | Method accepted internally with limitations; no candidate qualified. |
| Operational status | Research calculator only. |
| Recommendation | Seek external review before any integration. |

### Methodology

Calculate each applicable term separately; label conjectural, conditional-theorem, unconditional-theorem, heuristic, and omitted composition explicitly.

### Exact implementation

Pinned calculator consumes exact relation/FRI/MMCS/transcript parameters and emits per-term bottlenecks rather than one blended score.

### Raw results

q32 results are **107 conjectural**, **56 conditional Johnson/list-decoding**, and **37 unconditional unique-decoding bits**. [CP1] The exact lowest accepted operative term remains unsettled because external review is open.

### Confidence intervals/distributions

These are analytical bounds/estimates; statistical confidence intervals do not apply. Precision in JSON must not be mistaken for cryptographic confidence.

### Comparison with baseline

The old interpretation emphasized random-words. The corrected interpretation foregrounds theorem-derived lower terms and omissions.

### Confounders

The MMCS cap is assumed; random-words omits the batched-opening proximity term; zero knowledge is not graded; no full QROM composition proof exists.

### Failures

The target is missed under conservative theorem regimes, and self-awarding qualification from the conjectural estimate is forbidden.

### Interpretation

The only defensible status is unreviewed PQ-oriented research, not security-qualified.

### Artifact paths

- `research/security-model/v03-q32.json`
- `research/security-model/status.json`
- `research/security-model/external-review-request.md`
- `research/reviews/checkpoint-1-baseline.json`

## 7. Common benchmark corpus

| Field | Content |
|---|---|
| Spike ID | SP-00/SP-10 |
| Hypothesis | A common corpus can support comparable candidate evaluation. |
| Candidate IDs | C00; H0–H7 |
| Source commits | 708adad |
| Completed scope | Semantic corpus and retained fixed vectors were used where implementations existed. |
| Omitted scope | No integrated post-baseline candidate consumed the full common protocol. |
| Gate result | FAIL |
| Primary evidence | research/common-corpus/semantic-cases.json |
| Security status | Not security-qualified; external acceptance open. |
| Operational status | Research/benchmark-only; no custody or deployment authorization. |
| Recommendation | Close the named blocker only; do not promote. |

### Methodology

Apply the plan's common evidence classes and fail closed at missing dependencies.

### Exact implementation

The retained corpus is `research/common-corpus/semantic-cases.json` plus `invalid-mutations.json`, identified by `corpus-manifest.json`; candidate mappings and resulting run IDs are indexed in `research/summaries/run-index.csv`. No post-baseline integrated mapper exists.

### Raw results

Corpus mechanics are available, but cross-candidate comparison is blocked by zero eligible relations.

### Confidence intervals/distributions

Where retained distributions exist, the complete CSV is linked. Otherwise the result is deterministic/status evidence and a confidence interval is not applicable. Missing distributions remain `NOT_EVALUATED`.

### Comparison with baseline

C00 is the only complete reference path. Isolated kernels, toy relations, upstream smokes, and projections are not directly comparable to its complete pool calls.

### Confounders

Dependency stops, differing relations/hardware, incomplete full paths, and absent external review limit comparison.

### Failures

No integrated post-baseline candidate consumed the full common protocol.

### Interpretation

The gate result applies to this spike. A local pass or useful negative control cannot satisfy integration, security, transaction, or product gates.

### Artifact paths

- `research/common-corpus/semantic-cases.json`
- `research/summaries/run-index.csv`

## 8. Application hash/compression experiments

| Field | Content |
|---|---|
| Spike ID | SP-10 |
| Hypothesis | A fixed-length compressor can materially reduce the relation and remain acceptable. |
| Candidate IDs | H0–H7 |
| Source commits | 708adad |
| Completed scope | Rust/TypeScript vectors and Solidity anchors; primitive diagnostics. |
| Omitted scope | Full required Solidity parity, misuse suite, structural acceptance, eligible AIR relation. |
| Gate result | FAIL |
| Primary evidence | research/candidates/hash-compression-common/status.json |
| Security status | Not security-qualified; external acceptance open. |
| Operational status | Research/benchmark-only; no custody or deployment authorization. |
| Recommendation | Close the named blocker only; do not promote. |

### Methodology

Apply the plan's common evidence classes and fail closed at missing dependencies.

### Exact implementation

Entrypoint `python3 research/candidates/hash-compression-common/run.py` generates/checks the H0–H7 Rust/TypeScript bundle and Solidity anchor harness. The retained profile pins solc 0.8.30, Prague EVM, optimizer enabled with 200 runs, and via-IR; candidate modes and widths are in their manifests.

### Raw results

18,146 Rust/TypeScript vectors and 8 Solidity anchors did not establish an eligible compressor; verdict NO_AIR_CANDIDATE. [SP10]

### Confidence intervals/distributions

Where retained distributions exist, the complete CSV is linked. Otherwise the result is deterministic/status evidence and a confidence interval is not applicable. Missing distributions remain `NOT_EVALUATED`.

### Comparison with baseline

C00 is the only complete reference path. Isolated kernels, toy relations, upstream smokes, and projections are not directly comparable to its complete pool calls.

### Confounders

Dependency stops, differing relations/hardware, incomplete full paths, and absent external review limit comparison.

### Failures

Full required Solidity parity, misuse suite, structural acceptance, eligible AIR relation.

### Interpretation

The gate result applies to this spike. A local pass or useful negative control cannot satisfy integration, security, transaction, or product gates.

### Artifact paths

- `research/candidates/hash-compression-common/status.json`
- `research/candidates/hash-compression-common/vectors/cross-language.json.zst`

## 9. Merkle/deposit experiments

| Field | Content |
|---|---|
| Spike ID | SP-11/SP-12 |
| Hypothesis | Tree shape or batching can reduce deposit cost safely. |
| Candidate IDs | H0; higher-arity shapes; deposit batching |
| Source commits | 708adad |
| Completed scope | H0 root parity and isolated tree/batch diagnostics. |
| Omitted scope | Complete transactions for alternatives; accepted compressor; deployable batching path. |
| Gate result | FAIL |
| Primary evidence | research/candidates/merkle-shape/status.json |
| Security status | Not security-qualified; external acceptance open. |
| Operational status | Research/benchmark-only; no custody or deployment authorization. |
| Recommendation | Close the named blocker only; do not promote. |

### Methodology

Apply the plan's common evidence classes and fail closed at missing dependencies.

### Exact implementation

Entrypoints `python3 research/candidates/merkle-shape/run.py` and `python3 research/candidates/deposit-batching/run.py` execute deterministic models; each package's `ingest-foundry.py` imports isolated Solidity evidence. SP-11 retains binary depth-20 H0 and checks arity variants; SP-12 models bounded batched root transitions.

### Raw results

H0 parity passed for 1,000 roots, but higher arity stopped and complete alternative transaction gas was not evaluated. [SP11]

### Confidence intervals/distributions

Where retained distributions exist, the complete CSV is linked. Otherwise the result is deterministic/status evidence and a confidence interval is not applicable. Missing distributions remain `NOT_EVALUATED`.

### Comparison with baseline

C00 is the only complete reference path. Isolated kernels, toy relations, upstream smokes, and projections are not directly comparable to its complete pool calls.

### Confounders

Dependency stops, differing relations/hardware, incomplete full paths, and absent external review limit comparison.

### Failures

Complete transactions for alternatives; accepted compressor; deployable batching path.

### Interpretation

The gate result applies to this spike. A local pass or useful negative control cannot satisfy integration, security, transaction, or product gates.

### Artifact paths

- `research/candidates/merkle-shape/status.json`
- `research/candidates/deposit-batching/status.json`
- `research/candidates/merkle-shape/outputs/results.json`

## 10. AIR geometry experiments

| Field | Content |
|---|---|
| Spike ID | SP-20/SP-21 |
| Hypothesis | Vertical AIR or structured decomposition can shrink the complete relation. |
| Candidate IDs | A0–A4; structured AIR/R1CS/CCS |
| Source commits | 708adad |
| Completed scope | Dependency evaluation and source-verified reference mapping. |
| Omitted scope | Alternative relation implementation, proof integration, gas and prover measurement. |
| Gate result | DEFERRED |
| Primary evidence | research/candidates/air-geometry/status.json |
| Security status | Not security-qualified; external acceptance open. |
| Operational status | Research/benchmark-only; no custody or deployment authorization. |
| Recommendation | Close the named blocker only; do not promote. |

### Methodology

Apply the plan's common evidence classes and fail closed at missing dependencies.

### Exact implementation

Dependency checkers `python3 research/candidates/air-geometry/check.py` and `python3 research/candidates/structured-relation/check.py` read all H0–H7 dispositions and SP-02. They emit stopped-state results: A0 is source-reference only, A1–A4 are unattempted, and AIR/R1CS/CCS/Boolean conversions remain unattempted.

### Raw results

Both studies stopped by dependency because SP-10 produced no eligible compressor; null results are not zero. [SP20] [SP21]

### Confidence intervals/distributions

Where retained distributions exist, the complete CSV is linked. Otherwise the result is deterministic/status evidence and a confidence interval is not applicable. Missing distributions remain `NOT_EVALUATED`.

### Comparison with baseline

C00 is the only complete reference path. Isolated kernels, toy relations, upstream smokes, and projections are not directly comparable to its complete pool calls.

### Confounders

Dependency stops, differing relations/hardware, incomplete full paths, and absent external review limit comparison.

### Failures

Alternative relation implementation, proof integration, gas and prover measurement.

### Interpretation

The gate result applies to this spike. A local pass or useful negative control cannot satisfy integration, security, transaction, or product gates.

### Artifact paths

- `research/candidates/air-geometry/status.json`
- `research/candidates/structured-relation/status.json`

## 11. Transcript/verifier experiments

| Field | Content |
|---|---|
| Spike ID | SP-30/SP-31 |
| Hypothesis | Transcript and verifier changes can create robust complete-path margin. |
| Candidate IDs | T0–T3; V1–V9 |
| Source commits | 708adad |
| Completed scope | Isolated Solidity measurements, diagnostics, boundary review. |
| Omitted scope | Full verifier variants, complete claim-state machine, QROM review, integrated path. |
| Gate result | DEFERRED |
| Primary evidence | research/candidates/T3/status.json |
| Security status | Not security-qualified; external acceptance open. |
| Operational status | Research/benchmark-only; no custody or deployment authorization. |
| Recommendation | Close the named blocker only; do not promote. |

### Methodology

Apply the plan's common evidence classes and fail closed at missing dependencies.

### Exact implementation

Entrypoint `python3 research/cryptanalysis/transcript/run-focused.py` exercises T0–T3 claim/challenge grammars; `python3 research/candidates/verifier-optimization-common/run-focused.py` records V1–V9 isolated Rust/Solidity diagnostics. V9's retained benchmark JSON carries the projection and explicitly leaves `fullPath` not evaluated.

### Raw results

T3 is external-review-only. V9 projected minimum margin 1,274,248 gas, but full path is NOT_EVALUATED and the projection is not additive evidence. [SP31_RESULT]

### Confidence intervals/distributions

Where retained distributions exist, the complete CSV is linked. Otherwise the result is deterministic/status evidence and a confidence interval is not applicable. Missing distributions remain `NOT_EVALUATED`.

### Comparison with baseline

C00 is the only complete reference path. Isolated kernels, toy relations, upstream smokes, and projections are not directly comparable to its complete pool calls.

### Confounders

Dependency stops, differing relations/hardware, incomplete full paths, and absent external review limit comparison.

### Failures

Full verifier variants, complete claim-state machine, QROM review, integrated path.

### Interpretation

The gate result applies to this spike. A local pass or useful negative control cannot satisfy integration, security, transaction, or product gates.

### Artifact paths

- `research/candidates/T3/status.json`
- `research/candidates/verifier-optimization-common/status.json`
- `research/candidates/V9/status.json`
- `research/candidates/V9/outputs/benchmark.json`

## 12. Field/extension experiments

| Field | Content |
|---|---|
| Spike ID | SP-40 |
| Hypothesis | A different base/challenge field can improve the complete proof. |
| Candidate IDs | F0–F5 |
| Source commits | 708adad |
| Completed scope | Native and Solidity kernel diagnostics and deterministic vectors. |
| Omitted scope | Ported full relation/proof/verifier, complete soundness and accepted selection. |
| Gate result | DEFERRED |
| Primary evidence | research/candidates/field-bakeoff-common/status.json |
| Security status | Not security-qualified; external acceptance open. |
| Operational status | Research/benchmark-only; no custody or deployment authorization. |
| Recommendation | Close the named blocker only; do not promote. |

### Methodology

Apply the plan's common evidence classes and fail closed at missing dependencies.

### Exact implementation

`python3 research/candidates/field-bakeoff-common/generate_packages.py` materializes F0–F5 packages; native kernels are built from `native/Cargo.toml` and Solidity kernels run through `solidity/run_bench.py`. These are field-operation/opened-row diagnostics, not a ported relation.

### Raw results

All field candidates remain unranked benchmark-only diagnostics; none passed a complete protocol gate. [SP40]

### Confidence intervals/distributions

Where retained distributions exist, the complete CSV is linked. Otherwise the result is deterministic/status evidence and a confidence interval is not applicable. Missing distributions remain `NOT_EVALUATED`.

### Comparison with baseline

C00 is the only complete reference path. Isolated kernels, toy relations, upstream smokes, and projections are not directly comparable to its complete pool calls.

### Confounders

Dependency stops, differing relations/hardware, incomplete full paths, and absent external review limit comparison.

### Failures

Ported full relation/proof/verifier, complete soundness and accepted selection.

### Interpretation

The gate result applies to this spike. A local pass or useful negative control cannot satisfy integration, security, transaction, or product gates.

### Artifact paths

- `research/candidates/field-bakeoff-common/status.json`
- `research/candidates/field-bakeoff-common/outputs/native-latest.json`
- `research/candidates/field-bakeoff-common/outputs/solidity-latest.json`

## 13. Hiding FRI Pareto results

| Field | Content |
|---|---|
| Spike ID | SP-50 |
| Hypothesis | Hiding-FRI parameters can meet security and transaction frontiers. |
| Candidate IDs | C10-fri |
| Source commits | 6f40453 |
| Completed scope | Analytical Cartesian sweep and fresh native anchors. |
| Omitted scope | Exact complete transaction measurements and external security acceptance. |
| Gate result | FAIL |
| Primary evidence | research/fri-pareto/status.json |
| Security status | Not security-qualified; external acceptance open. |
| Operational status | Research/benchmark-only; no custody or deployment authorization. |
| Recommendation | Close the named blocker only; do not promote. |

### Methodology

Apply the plan's common evidence classes and fail closed at missing dependencies.

### Exact implementation

Entrypoint `python3 research/fri-pareto/run.py` applies `grid.json` to the frozen H0 relation, evaluates the full analytical Cartesian set, and generates two fresh native proofs for each b4-q32, b4-q48, and b3-q111 anchor. `--metadata-only` verifies retained metadata without fresh proofs.

### Raw results

504,000 analytical rows were evaluated; 120 retained nondominated q111 rows meeting the generated 100-bit threshold all failed the two-transaction filter; no winner. [SP50] [CP3]

### Confidence intervals/distributions

Where retained distributions exist, the complete CSV is linked. Otherwise the result is deterministic/status evidence and a confidence interval is not applicable. Missing distributions remain `NOT_EVALUATED`.

### Comparison with baseline

C00 is the only complete reference path. Isolated kernels, toy relations, upstream smokes, and projections are not directly comparable to its complete pool calls.

### Confounders

Dependency stops, differing relations/hardware, incomplete full paths, and absent external review limit comparison.

### Failures

Exact complete transaction measurements and external security acceptance.

### Interpretation

The gate result applies to this spike. A local pass or useful negative control cannot satisfy integration, security, transaction, or product gates.

### Artifact paths

- `research/fri-pareto/status.json`
- `research/fri-pareto/outputs/analytical-filter.json`
- `research/summaries/proof-ledger.csv`

## 14. HVZK-WHIR results

| Field | Content |
|---|---|
| Spike ID | SP-51 |
| Hypothesis | Hiding WHIR can provide a better private backend. |
| Candidate IDs | C20 |
| Source commits | 6f40453 |
| Completed scope | Pinned upstream HidingWhirPcs native smoke. |
| Omitted scope | Exact PQTC relation, matching EVM verifier, QROM reduction and review. |
| Gate result | DEFERRED |
| Primary evidence | research/candidates/C20-hvzk-whir/status.json |
| Security status | Not security-qualified; external acceptance open. |
| Operational status | Research/benchmark-only; no custody or deployment authorization. |
| Recommendation | Close the named blocker only; do not promote. |

### Methodology

Apply the plan's common evidence classes and fail closed at missing dependencies.

### Exact implementation

Entrypoint `research/candidates/C20-hvzk-whir/run-focused.sh` builds the lockfile-pinned Rust adapter and runs two fresh HidingWhirPcs upstream smokes at 4,096 logical/padded rows and trace width 12. It deliberately does not map the PQTC relation or call an EVM verifier.

### Raw results

The smoke is UPSTREAM_BASELINE_NOT_PQTC; it is neither an integrated proof nor a candidate measurement. [SP51]

### Confidence intervals/distributions

Where retained distributions exist, the complete CSV is linked. Otherwise the result is deterministic/status evidence and a confidence interval is not applicable. Missing distributions remain `NOT_EVALUATED`.

### Comparison with baseline

C00 is the only complete reference path. Isolated kernels, toy relations, upstream smokes, and projections are not directly comparable to its complete pool calls.

### Confounders

Dependency stops, differing relations/hardware, incomplete full paths, and absent external review limit comparison.

### Failures

Exact PQTC relation, matching EVM verifier, QROM reduction and review.

### Interpretation

The gate result applies to this spike. A local pass or useful negative control cannot satisfy integration, security, transaction, or product gates.

### Artifact paths

- `research/candidates/C20-hvzk-whir/status.json`
- `research/candidates/C20-hvzk-whir/manifest.json`

## 15. STIR/Circle readiness results

| Field | Content |
|---|---|
| Spike ID | SP-52/SP-53 |
| Hypothesis | STIR or Circle can establish a competitive hiding route. |
| Candidate IDs | C30; C40 |
| Source commits | 6f40453 |
| Completed scope | Pinned STIR non-hiding lower-bound smoke and Circle source watch. |
| Omitted scope | Hiding PCS, comparable relation, complete verifier and transaction. |
| Gate result | DEFERRED |
| Primary evidence | research/candidates/C30-stir/status.json |
| Security status | Not security-qualified; external acceptance open. |
| Operational status | Research/benchmark-only; no custody or deployment authorization. |
| Recommendation | Close the named blocker only; do not promote. |

### Methodology

Apply the plan's common evidence classes and fail closed at missing dependencies.

### Exact implementation

`research/candidates/C30-stir/run-focused.sh` builds/runs the lockfile-pinned TwoAdicStirPcs adapter with ZK=false; `research/candidates/C40-circle/run-focused.sh` and `source-watch.py` validate the pinned CirclePcs API without executing a native proof. Both validators enforce their result schemas.

### Raw results

STIR is non-hiding benchmark-only; Circle exposes no comparable hiding path at the pin. [SP52] [SP53]

### Confidence intervals/distributions

Where retained distributions exist, the complete CSV is linked. Otherwise the result is deterministic/status evidence and a confidence interval is not applicable. Missing distributions remain `NOT_EVALUATED`.

### Comparison with baseline

C00 is the only complete reference path. Isolated kernels, toy relations, upstream smokes, and projections are not directly comparable to its complete pool calls.

### Confounders

Dependency stops, differing relations/hardware, incomplete full paths, and absent external review limit comparison.

### Failures

Hiding PCS, comparable relation, complete verifier and transaction.

### Interpretation

The gate result applies to this spike. A local pass or useful negative control cannot satisfy integration, security, transaction, or product gates.

### Artifact paths

- `research/candidates/C30-stir/status.json`
- `research/candidates/C40-circle/status.json`

## 16. Spartan-WHIR results

| Field | Content |
|---|---|
| Spike ID | SP-60 |
| Hypothesis | Structured Spartan-WHIR can exploit repeated computation with full ZK. |
| Candidate IDs | C50 |
| Source commits | 6f40453 |
| Completed scope | Pinned native API and standalone Solidity-WHIR controls. |
| Omitted scope | Exact PQTC relation, full EVM Spartan path, executable gas harness and license clearance. |
| Gate result | DEFERRED |
| Primary evidence | research/candidates/C50-spartan-whir/status.json |
| Security status | Not security-qualified; external acceptance open. |
| Operational status | Research/benchmark-only; no custody or deployment authorization. |
| Recommendation | Close the named blocker only; do not promote. |

### Methodology

Apply the plan's common evidence classes and fail closed at missing dependencies.

### Exact implementation

Entrypoint `python3 research/candidates/C50-spartan-whir/run.py` checks pinned native DirectSparse/Spark controls and the standalone Solidity-WHIR build/tests. It preserves the upstream gas-script failure before measurement and does not synthesize an exact PQTC relation.

### Raw results

Upstream controls exist, but exact relation/end-to-end reproduction and gas are absent; no integration. [SP60]

### Confidence intervals/distributions

Where retained distributions exist, the complete CSV is linked. Otherwise the result is deterministic/status evidence and a confidence interval is not applicable. Missing distributions remain `NOT_EVALUATED`.

### Comparison with baseline

C00 is the only complete reference path. Isolated kernels, toy relations, upstream smokes, and projections are not directly comparable to its complete pool calls.

### Confounders

Dependency stops, differing relations/hardware, incomplete full paths, and absent external review limit comparison.

### Failures

Exact PQTC relation, full EVM Spartan path, executable gas harness and license clearance.

### Interpretation

The gate result applies to this spike. A local pass or useful negative control cannot satisfy integration, security, transaction, or product gates.

### Artifact paths

- `research/candidates/C50-spartan-whir/status.json`
- `research/candidates/C50-spartan-whir/manifest.json`

## 17. Recursive proof results

| Field | Content |
|---|---|
| Spike ID | SP-61 |
| Hypothesis | Transparent recursion can compress the strongest inner proof. |
| Candidate IDs | C60 |
| Source commits | 6f40453 |
| Completed scope | Upstream recursive architecture smoke. |
| Omitted scope | PQTC recursive Keccak ZK, hiding-WHIR in-circuit adapter, compatible pin, EVM verifier. |
| Gate result | DEFERRED |
| Primary evidence | research/candidates/C60-recursion/status.json |
| Security status | Not security-qualified; external acceptance open. |
| Operational status | Research/benchmark-only; no custody or deployment authorization. |
| Recommendation | Close the named blocker only; do not promote. |

### Methodology

Apply the plan's common evidence classes and fail closed at missing dependencies.

### Exact implementation

Entrypoint `python3 research/candidates/C60-recursion/run.py` executes the pinned recursive Fibonacci architecture control and inspects recursive Keccak, the `--zk` behavior, dependency version, in-circuit WHIR adapter, and EVM availability. The control is labeled upstream/toy, never PQTC.

### Raw results

Toy recursion is not PQTC; the ZK flag had no relevant effect and no EVM path exists. [SP61]

### Confidence intervals/distributions

Where retained distributions exist, the complete CSV is linked. Otherwise the result is deterministic/status evidence and a confidence interval is not applicable. Missing distributions remain `NOT_EVALUATED`.

### Comparison with baseline

C00 is the only complete reference path. Isolated kernels, toy relations, upstream smokes, and projections are not directly comparable to its complete pool calls.

### Confounders

Dependency stops, differing relations/hardware, incomplete full paths, and absent external review limit comparison.

### Failures

PQTC recursive Keccak ZK, hiding-WHIR in-circuit adapter, compatible pin, EVM verifier.

### Interpretation

The gate result applies to this spike. A local pass or useful negative control cannot satisfy integration, security, transaction, or product gates.

### Artifact paths

- `research/candidates/C60-recursion/status.json`
- `research/candidates/C60-recursion/manifest.json`

## 18. Flock/VEIL results

| Field | Content |
|---|---|
| Spike ID | SP-62 |
| Hypothesis | Flock/VEIL can combine conventional hashes with lightweight ZK. |
| Candidate IDs | C70 Flock; C70 VEIL |
| Source commits | 6f40453 |
| Completed scope | Source checks and experimental VEIL proof-of-concept controls. |
| Omitted scope | Executable historical benchmark, current Keccak relation, hiding Flock, EVM verifier, adapter. |
| Gate result | FAIL |
| Primary evidence | research/candidates/C70-flock-veil/status.json |
| Security status | Not security-qualified; external acceptance open. |
| Operational status | Research/benchmark-only; no custody or deployment authorization. |
| Recommendation | Close the named blocker only; do not promote. |

### Methodology

Apply the plan's common evidence classes and fail closed at missing dependencies.

### Exact implementation

Entrypoint `python3 research/candidates/C70-flock-veil/run.py` source-checks Flock, runs the exact historical batch-44 attempt without patching the missing Ligerito configuration, and records the VEIL root/MLE/zerocheck upstream PoCs. `batch-capacity.json` preserves source-derived capacity semantics separately from benchmark success.

### Raw results

Flock stopped; historical batch-44 panicked at the pin and is not a published measurement. VEIL remains deferred and non-integrated. [SP62]

### Confidence intervals/distributions

Where retained distributions exist, the complete CSV is linked. Otherwise the result is deterministic/status evidence and a confidence interval is not applicable. Missing distributions remain `NOT_EVALUATED`.

### Comparison with baseline

C00 is the only complete reference path. Isolated kernels, toy relations, upstream smokes, and projections are not directly comparable to its complete pool calls.

### Confounders

Dependency stops, differing relations/hardware, incomplete full paths, and absent external review limit comparison.

### Failures

Executable historical benchmark, current Keccak relation, hiding Flock, EVM verifier, adapter.

### Interpretation

The gate result applies to this spike. A local pass or useful negative control cannot satisfy integration, security, transaction, or product gates.

### Artifact paths

- `research/candidates/C70-flock-veil/status.json`
- `research/candidates/C70-flock-veil/manifest.json`

## 19. Aggregation results

| Field | Content |
|---|---|
| Spike ID | SP-70 |
| Hypothesis | Aggregation can amortize a qualified individual proof. |
| Candidate IDs | Product aggregation |
| Source commits | 6f40453 |
| Completed scope | Deterministic safety/liveness model and isolated settlement components. |
| Omitted scope | Accepted individual proof, outer proof, prover/RSS, complete settlement gas/calldata. |
| Gate result | DEFERRED |
| Primary evidence | research/aggregation/status.json |
| Security status | Not security-qualified; external acceptance open. |
| Operational status | Research/benchmark-only; no custody or deployment authorization. |
| Recommendation | Close the named blocker only; do not promote. |

### Methodology

Apply the plan's common evidence classes and fail closed at missing dependencies.

### Exact implementation

Entrypoint `python3 research/aggregation/run.py` evaluates `model.py` over N=1,2,4,8,16,32,64 and imports isolated settlement components through `ingest-foundry.py`. The API enforces proof-only aggregation privacy, while all proof/verifier/prover fields stay null without an accepted individual proof.

### Raw results

Stopped by dependency. Null aggregation metrics remain NOT_EVALUATED, not zero. [SP70]

### Confidence intervals/distributions

Where retained distributions exist, the complete CSV is linked. Otherwise the result is deterministic/status evidence and a confidence interval is not applicable. Missing distributions remain `NOT_EVALUATED`.

### Comparison with baseline

C00 is the only complete reference path. Isolated kernels, toy relations, upstream smokes, and projections are not directly comparable to its complete pool calls.

### Confounders

Dependency stops, differing relations/hardware, incomplete full paths, and absent external review limit comparison.

### Failures

Accepted individual proof, outer proof, prover/RSS, complete settlement gas/calldata.

### Interpretation

The gate result applies to this spike. A local pass or useful negative control cannot satisfy integration, security, transaction, or product gates.

### Artifact paths

- `research/aggregation/status.json`
- `research/aggregation/outputs/results.json`

## 20. Robust two-call state-machine results

| Field | Content |
|---|---|
| Spike ID | SP-72 |
| Hypothesis | A bounded A/B state machine can provide a robust fallback. |
| Candidate IDs | Product robust-two-call |
| Source commits | 6f40453 |
| Completed scope | Executable research state machine and attack model. |
| Omitted scope | Exact integrated proof binding, qualified security, live chain and required hardware. |
| Gate result | FAIL |
| Primary evidence | research/two-call-state/status.json |
| Security status | Not security-qualified; external acceptance open. |
| Operational status | Research/benchmark-only; no custody or deployment authorization. |
| Recommendation | Close the named blocker only; do not promote. |

### Methodology

Apply the plan's common evidence classes and fail closed at missing dependencies.

### Exact implementation

Entrypoint `python3 research/two-call-state/run.py` executes the transitions, invariants, attacks, and cleanup model from `transitions.json`, `invariants.json`, and `attacks.json`, then binds the Solidity research harness outputs. It records 10/10 modeled attacks while refusing full-path or security qualification.

### Raw results

State semantics passed their model, but retained projections fail the gas gate and no integrated proof path exists. [SP72]

### Confidence intervals/distributions

Where retained distributions exist, the complete CSV is linked. Otherwise the result is deterministic/status evidence and a confidence interval is not applicable. Missing distributions remain `NOT_EVALUATED`.

### Comparison with baseline

C00 is the only complete reference path. Isolated kernels, toy relations, upstream smokes, and projections are not directly comparable to its complete pool calls.

### Confounders

Dependency stops, differing relations/hardware, incomplete full paths, and absent external review limit comparison.

### Failures

Exact integrated proof binding, qualified security, live chain and required hardware.

### Interpretation

The gate result applies to this spike. A local pass or useful negative control cannot satisfy integration, security, transaction, or product gates.

### Artifact paths

- `research/two-call-state/status.json`
- `research/two-call-state/outputs/results.json`

## 21. L2/economic results

| Field | Content |
|---|---|
| Spike ID | SP-71/economic model |
| Hypothesis | An ordinary L2 route can preserve semantics and materially reduce cost. |
| Candidate IDs | OP-family; Arbitrum-family; Scroll ordinary paths |
| Source commits | 6f40453 |
| Completed scope | Signed transaction generation, source-pinned admission and synthetic fee projections. |
| Omitted scope | Required network receipts, exact verifier, live cost ratio, semantics evidence. |
| Gate result | FAIL |
| Primary evidence | research/l2-economics/status.json |
| Security status | Not security-qualified; external acceptance open. |
| Operational status | Research/benchmark-only; no custody or deployment authorization. |
| Recommendation | Close the named blocker only; do not promote. |

### Methodology

Apply the plan's common evidence classes and fail closed at missing dependencies.

### Exact implementation

Entrypoint `python3 research/l2-economics/generate.py` generates signed-size cases and source-limit admission results from `matrix.json`/`sources.json`; `python3 research/economic-throughput/run.py` computes only evidence-backed throughput rows. OP FastLZ inputs are synthetic, and absent Arbitrum/Scroll executables and network receipts remain null.

### Raw results

A 210 KiB ordinary transaction was rejected by all selected admission-limit projections; required network measurements are incomplete and product gate NOT_EVALUATED. [SP71]

### Confidence intervals/distributions

Where retained distributions exist, the complete CSV is linked. Otherwise the result is deterministic/status evidence and a confidence interval is not applicable. Missing distributions remain `NOT_EVALUATED`.

### Comparison with baseline

C00 is the only complete reference path. Isolated kernels, toy relations, upstream smokes, and projections are not directly comparable to its complete pool calls.

### Confounders

Dependency stops, differing relations/hardware, incomplete full paths, and absent external review limit comparison.

### Failures

Required network receipts, exact verifier, live cost ratio, semantics evidence.

### Interpretation

The gate result applies to this spike. A local pass or useful negative control cannot satisfy integration, security, transaction, or product gates.

### Artifact paths

- `research/l2-economics/status.json`
- `research/economic-throughput/status.json`

## 22. Prover UX results

| Field | Content |
|---|---|
| Spike ID | SP-73 |
| Hypothesis | A finalist can meet practical proving and deployment operations gates. |
| Candidate IDs | C00 operations reference |
| Source commits | 6f40453 |
| Completed scope | Retained-record validation and H1 warm baseline distributions. |
| Omitted scope | H1 cold, H2/H3, portability, CLI, setup, cancellation, pressure and recovery. |
| Gate result | FAIL |
| Primary evidence | research/prover-operations/status.json |
| Security status | Not security-qualified; external acceptance open. |
| Operational status | Research/benchmark-only; no custody or deployment authorization. |
| Recommendation | Close the named blocker only; do not promote. |

### Methodology

Apply the plan's common evidence classes and fail closed at missing dependencies.

### Exact implementation

Entrypoint `python3 research/prover-operations/analyze.py` validates the 60 C00 source records and their 480 declared artifacts, then computes retained H1-warm latency/RSS/storage distributions. `cli-workflow.json` is specification-only; no synthetic H1-cold, H2/H3, cancellation, pressure, or recovery values are emitted.

### Raw results

60 source records and 480 declared artifacts validated, but only H1 warm timing is complete and no finalist exists. [SP73]

### Confidence intervals/distributions

Where retained distributions exist, the complete CSV is linked. Otherwise the result is deterministic/status evidence and a confidence interval is not applicable. Missing distributions remain `NOT_EVALUATED`.

### Comparison with baseline

C00 is the only complete reference path. Isolated kernels, toy relations, upstream smokes, and projections are not directly comparable to its complete pool calls.

### Confounders

Dependency stops, differing relations/hardware, incomplete full paths, and absent external review limit comparison.

### Failures

H1 cold, H2/H3, portability, CLI, setup, cancellation, pressure and recovery.

### Interpretation

The gate result applies to this spike. A local pass or useful negative control cannot satisfy integration, security, transaction, or product gates.

### Artifact paths

- `research/prover-operations/status.json`
- `research/prover-operations/results.json`

## 23. Security and cryptanalysis review

| Field | Content |
|---|---|
| Spike ID | SP-01/SP-30/SP-80 |
| Hypothesis | Composed security and cryptanalysis can justify integration. |
| Candidate IDs | All candidate bundles |
| Source commits | 6f40453 |
| Completed scope | Internal methods, structural gate review, source packets and bundle checks. |
| Omitted scope | External cryptographic acceptance, complete QROM/composition and exact-instance structural review. |
| Gate result | FAIL |
| Primary evidence | research/security-model/status.json |
| Security status | Not security-qualified; external acceptance open. |
| Operational status | Research/benchmark-only; no custody or deployment authorization. |
| Recommendation | Close the named blocker only; do not promote. |

### Methodology

Apply the plan's common evidence classes and fail closed at missing dependencies.

### Exact implementation

Entrypoint `python3 research/cryptanalysis/review-packet/assemble.py` assembles the pinned transcript/hash review packet and manifest. It combines the SP-01 calculator, transcript claim graph, structural statuses, and explicit open QROM/MMCS/composition questions; it does not issue cryptographic acceptance.

### Raw results

No security-qualified candidate or bundle; internal independent review is explicitly not external cryptographic acceptance. [CP1] [SP80]

### Confidence intervals/distributions

Where retained distributions exist, the complete CSV is linked. Otherwise the result is deterministic/status evidence and a confidence interval is not applicable. Missing distributions remain `NOT_EVALUATED`.

### Comparison with baseline

C00 is the only complete reference path. Isolated kernels, toy relations, upstream smokes, and projections are not directly comparable to its complete pool calls.

### Confounders

Dependency stops, differing relations/hardware, incomplete full paths, and absent external review limit comparison.

### Failures

External cryptographic acceptance, complete QROM/composition and exact-instance structural review.

### Interpretation

The gate result applies to this spike. A local pass or useful negative control cannot satisfy integration, security, transaction, or product gates.

### Artifact paths

- `research/security-model/status.json`
- `research/cryptanalysis/review-packet/status.json`
- `research/integrated-finalists/status.json`

## 24. Advisory applicability matrix

| Field | Content |
|---|---|
| Spike ID | SP-02 |
| Hypothesis | Pinned advisories and analogous custom paths can be closed. |
| Candidate IDs | Plonky3 and custom Rust/Solidity paths |
| Source commits | 6f40453 |
| Completed scope | Applicability matrix and focused regression runner. |
| Omitted scope | Malformed-proof panic containment/panic-freedom and independent transcript/shape review. |
| Gate result | FAIL |
| Primary evidence | research/advisories/status.json |
| Security status | Not security-qualified; external acceptance open. |
| Operational status | Research/benchmark-only; no custody or deployment authorization. |
| Recommendation | Close the named blocker only; do not promote. |

### Methodology

Apply the plan's common evidence classes and fail closed at missing dependencies.

### Exact implementation

Entrypoint `python3 research/advisories/run_regressions.py` evaluates the pinned advisory applicability matrix and analogous Rust/Solidity paths, including malformed-proof behavior. The retained `regression-results.json` preserves the unresolved native panic boundary and therefore fails closed.

### Raw results

Archived failed: the native malformed-proof panic boundary is unresolved; integration remains blocked. [ADVISORY]

### Confidence intervals/distributions

Where retained distributions exist, the complete CSV is linked. Otherwise the result is deterministic/status evidence and a confidence interval is not applicable. Missing distributions remain `NOT_EVALUATED`.

### Comparison with baseline

C00 is the only complete reference path. Isolated kernels, toy relations, upstream smokes, and projections are not directly comparable to its complete pool calls.

### Confounders

Dependency stops, differing relations/hardware, incomplete full paths, and absent external review limit comparison.

### Failures

Malformed-proof panic containment/panic-freedom and independent transcript/shape review.

### Interpretation

The gate result applies to this spike. A local pass or useful negative control cannot satisfy integration, security, transaction, or product gates.

### Artifact paths

- `research/advisories/status.json`
- `research/advisories/run_regressions.py`

## 25. Candidate Pareto frontiers

Hard gates precede weighted scores. With zero eligible candidates there is no promotable Pareto winner; the complete machine-readable tables are `research/summaries/*.csv` and the eight complete axes are in `research/report-synthesis/pareto/`. [SP90]

### Minimum candidate matrix

All required plan rows are retained even where evaluation stopped by a justified dependency failure. [MINIMUM]

| Candidate | Hash relation | AIR/R1CS | Backend | Required status |
|---|---|---|---|---|
| C00 | v0.3 P2BB512 | 256x190 horizontal | hiding FRI q32 | reproduced |
| C01 | v0.3 P2BB512 | 256x190 horizontal | hiding FRI q48 | security/gas comparator |
| C10 | width-24 compression | best vertical | hiding FRI | measured if hash passes |
| C11 | width-32/12-field compression | best vertical | hiding FRI | required |
| C12 | width-32/12-field compression | second AIR geometry | hiding FRI | required |
| C20 | top relation | best AIR | HVZK-WHIR | required investigation |
| C21 | top relation | structured R1CS/CCS | Spartan-WHIR + ZK | required investigation |
| C22 | top inner proof | recursive verifier | transparent outer | required investigation |
| C23 | original Keccak relation | Flock repeated R1CS | Flock + ZK/outer | required investigation |
| C30 | best individual proof | aggregate proof | batch N=16 | required if recursion exists |
| C40 | best non-one-tx proof | two-call verifier | bounded checkpoint | required fallback |

### Candidate master table

| Candidate | Hash | AIR/R1CS | PCS | ZK | Accepted security | Proof B | Tx gas current | Tx gas 64 | Tx gas 96 | Deposit gas | Prove p50 | RSS | Runtime max | Gate |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| C00 [RUN_INDEX] | P2BB512 | horizontal AIR | hiding FRI q32 | yes | no | 208,940 median | A 16,179,681/16,664,641.5/16,953,270; B 13,333,063/13,959,759.5/14,264,492 min/p50/max | A 16,179,681/16,664,641.5/16,953,270; B 13,333,063/13,959,759.5/14,264,492 computed min/p50/max | A 16,179,681/16,664,641.5/16,953,270; B 13,333,063/13,959,759.5/14,264,492 computed min/p50/max | 13,991,021 | 604.969 ms | 29,483,008 B median | 17,827 B | FAIL |
| C10-fri [SP50] | frozen H0 | frozen AIR | hiding FRI sweep | yes | no | representative complete CSV | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | anchor CSV | anchor CSV | NOT_EVALUATED | FAIL |
| C20 [SP51] | upstream synthetic | upstream smoke | HidingWhirPcs | yes | no | 36,767 anchor-scale | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | 5.562 ms anchor-scale | 6,389,760 B | NOT_EVALUATED | DEFERRED |
| Bundles A–F [SP80] | mixed | mixed | mixed | required | no | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | FAIL |

### Security table

| Candidate | Primitive generic | Structural review | Proven proof bound | Conjectural proof estimate | Batch term included | QROM | ZK theorem | Multi-target result | Lowest term |
|---|---:|---|---:|---:|---|---|---|---:|---|
| C00 q32 [SEC] | manifest cap only | incomplete | 37 unconditional / 56 conditional | 107 | regime-dependent | incomplete | NOT_EVALUATED | calculator scenarios retained | 37 unconditional |
| H1/H3/H7 [SECURITY] | heuristic ceilings | incomplete | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | incomplete | NOT_EVALUATED | configurable | NOT_ACCEPTED |
| Integrated bundles [SP80] | NOT_EVALUATED | incomplete | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | incomplete | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED |

### Gas decomposition table

| Candidate | Parse/transcript | AIR/R1CS | Openings | LDT/PCS | MMCS | State/payout | Calldata | Floor binding? | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| C00 Part A [RUN_INDEX] | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | no, 0/60 current/64/96 computed-scenario rows | 16,664,641.5 / 16,664,641.5 / 16,664,641.5 current/64/96 p50 |
| C00 Part B [RUN_INDEX] | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | no, 0/60 current/64/96 computed-scenario rows | 13,959,759.5 / 13,959,759.5 / 13,959,759.5 current/64/96 p50 |
| V9 [SP31_RESULT] | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED |

### Proof byte ledger

| Candidate | Header | Statement | Global | Queries | Paths/frontiers | Salts/masks | LDT | Final | ABI overhead | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| C00 [PROOF] | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | 668 B median | 209,608 ABI median |
| C10-fri q111 representative [PROOF] | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | 484,577 raw anchor |
| Integrated bundles [SP80] | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED |

### Prover table

| Candidate | Hardware | Threads | Cold/warm | p50 | p95 | p99 | CPU s | RSS | Proof B |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|
| C00 [BASE] | macnch33z3.local-arm64 | 16 | warm | 604.969 ms | 834.257 ms | 1,086.470 ms | NOT_EVALUATED | 29,483,008 B median | 208,940 median |
| C20 upstream smoke [PROVER] | H1-MAC16-5-M4MAX-48G | 16 | NOT_APPLICABLE | 5.562 ms (two-anchor median) | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | 6,389,760 B | 36,767 anchor-scale |
| C30 non-hiding smoke [PROVER] | H1-MAC16-5-M4MAX-48G | 16 | NOT_APPLICABLE | 10.686 ms single run | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | 8,962,048 B | 17,407 anchor-scale |

Empty cells in source CSVs and every `NOT_EVALUATED` above mean unknown/unperformed, never numeric zero. Representative C20/C30 values are upstream/synthetic anchor-scale diagnostics, not PQTC integrated measurements. Full tables: `research/summaries/candidate-master.csv`, `security-master.csv`, `gas-decomposition.csv`, `proof-byte-ledger-master.csv`, and `prover-master.csv`.

## 26. One-transaction feasibility conclusion

One-transaction verification does **not** appear feasible on the committed evidence. C00 fails current robust limits, q32 is not security-qualified, q111 analytical rows cannot be promoted to measurements, and no alternative has a complete integrated transaction under current, 64-gas, and 96-gas schedules. A null full-path result is not a zero-gas result. [BASE] [CP3] [SP80]

## 27. Two-transaction fallback conclusion

No robust two-transaction build is recommended. C00's approximate split is reference evidence only; the FRI frontier's retained security-feasible rows all fail the two-call filter, Bundle F is blocked, and SP-72's state machine passes only its abstract safety/liveness scope while the projected gas and full-path binding gates fail. [CP3] [SP72] [SP80]

## 28. Recommended next-build architecture, if any

**No architecture is recommended.** The outcome is `OUTCOME_D` and the decision token is exactly `RECOMMEND_ADDITIONAL_TARGETED_RESEARCH`. A full plan, robust two-call build, aggregation/L2 promotion, or lineage stop would overstate the evidence. Targeted research should close the three executive risks in dependency order; a new build may be reconsidered only after an accepted relation and hiding backend jointly produce exact complete-path evidence. [CP4]

## 29. Rejected/deferred candidates

Every non-eligible scorecard is retained below; this intentionally preserves negative and deferred work rather than presenting only representative winners. Reason, last stage, measurement status/source, category, and revival are read or deterministically derived from each candidate's own scorecard `hard_gate`, `raw_metrics`, and `stop_record`; no generic stage or revival text is substituted. [CANDIDATES] [SCORECARDS]

| Candidate | Reason | Last completed stage | Measurements | Failure category | Revival condition |
|---|---|---|---|---|---|
| Bundle-A | BLOCKED_NO_ELIGIBLE_COMPONENTS: No accepted security qualification.; Checkpoints 2-4 authorize no integration or product candidate.; SP-80 records zero eligible bundles and zero complete prototypes. | BLOCKED_NO_ELIGIBLE_COMPONENTS | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=NOT_EVALUATED; complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/integrated-finalists/outputs/results.json`, `research/integrated-finalists/status.json`, `research/reviews/checkpoint-3-backends.json` | security/privacy/calldata/maturity | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| Bundle-B | BLOCKED_NO_ELIGIBLE_COMPONENTS: No accepted security qualification.; Checkpoints 2-4 authorize no integration or product candidate.; SP-80 records zero eligible bundles and zero complete prototypes. | BLOCKED_NO_ELIGIBLE_COMPONENTS | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=NOT_EVALUATED; complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/integrated-finalists/outputs/results.json`, `research/integrated-finalists/status.json`, `research/reviews/checkpoint-3-backends.json` | security/privacy/calldata/maturity | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| Bundle-C | BLOCKED_NO_ELIGIBLE_COMPONENTS: No accepted security qualification.; Checkpoints 2-4 authorize no integration or product candidate.; SP-80 records zero eligible bundles and zero complete prototypes. | BLOCKED_NO_ELIGIBLE_COMPONENTS | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=NOT_EVALUATED; complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/integrated-finalists/outputs/results.json`, `research/integrated-finalists/status.json`, `research/reviews/checkpoint-3-backends.json` | security/privacy/calldata/maturity | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| Bundle-D | BLOCKED_NO_ELIGIBLE_COMPONENTS: No accepted security qualification.; Checkpoints 2-4 authorize no integration or product candidate.; SP-80 records zero eligible bundles and zero complete prototypes. | BLOCKED_NO_ELIGIBLE_COMPONENTS | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=NOT_EVALUATED; complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/integrated-finalists/outputs/results.json`, `research/integrated-finalists/status.json`, `research/reviews/checkpoint-3-backends.json` | security/privacy/calldata/maturity | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| Bundle-E | BLOCKED_NO_ELIGIBLE_COMPONENTS: No accepted security qualification.; Checkpoints 2-4 authorize no integration or product candidate.; SP-80 records zero eligible bundles and zero complete prototypes. | BLOCKED_NO_ELIGIBLE_COMPONENTS | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=NOT_EVALUATED; complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/integrated-finalists/outputs/results.json`, `research/integrated-finalists/status.json`, `research/reviews/checkpoint-3-backends.json` | security/privacy/calldata/maturity | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| Bundle-F | BLOCKED_NO_ELIGIBLE_COMPONENTS: No accepted security qualification.; Checkpoints 2-4 authorize no integration or product candidate.; SP-80 records zero eligible bundles and zero complete prototypes. | BLOCKED_NO_ELIGIBLE_COMPONENTS | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=NOT_EVALUATED; complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/integrated-finalists/outputs/results.json`, `research/integrated-finalists/status.json`, `research/reviews/checkpoint-3-backends.json` | security/privacy/calldata/maturity | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| C20 | DEFERRED: exactTranscriptQromReduction=MISSING; externalCryptographicReview=NOT_PERFORMED | DEFERRED | proof=OBSERVED (2 rows; runs research-sp51-c20-native-r0…research-sp51-c20-native-r1); ABI=NOT_EVALUATED; prover=OBSERVED (2 rows; runs research-sp51-c20-native-r0…research-sp51-c20-native-r1); EVM components=NOT_EVALUATED; complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/candidates/C20-hvzk-whir/manifest.json`, `research/candidates/C20-hvzk-whir/status.json` | security/maturity | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| C30 | BENCHMARK_ONLY: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | BENCHMARK_ONLY | proof=OBSERVED (1 rows; runs research-sp52-c30-native); ABI=NOT_EVALUATED; prover=OBSERVED (1 rows; runs research-sp52-c30-native); EVM components=NOT_EVALUATED; complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/candidates/C30-stir/manifest.json`, `research/candidates/C30-stir/status.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| C40 | DEFERRED: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | DEFERRED | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=NOT_EVALUATED; complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/candidates/C40-circle/manifest.json`, `research/candidates/C40-circle/status.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| C50 | DEFERRED: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | DEFERRED | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=NOT_EVALUATED; complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/candidates/C50-spartan-whir/manifest.json`, `research/candidates/C50-spartan-whir/status.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| C60 | DEFERRED: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | DEFERRED | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=NOT_EVALUATED; complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/candidates/C60-recursion/manifest.json`, `research/candidates/C60-recursion/status.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| C70 | FLOCK_STOP_VEIL_DEFERRED: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | FLOCK_STOP_VEIL_DEFERRED | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=NOT_EVALUATED; complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/candidates/C70-flock-veil/manifest.json`, `research/candidates/C70-flock-veil/status.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| F0 | BENCHMARK_ONLY: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | BENCHMARK_ONLY | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=OBSERVED (27 rows; runs research-sp40-f0-field-benchmark); complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/candidates/F0/manifest.json`, `research/candidates/F0/status.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| F1 | BENCHMARK_ONLY: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | BENCHMARK_ONLY | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=OBSERVED (27 rows; runs research-sp40-f1-field-benchmark); complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/candidates/F1/manifest.json`, `research/candidates/F1/status.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| F2 | BENCHMARK_ONLY: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | BENCHMARK_ONLY | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=OBSERVED (27 rows; runs research-sp40-f2-field-benchmark); complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/candidates/F2/manifest.json`, `research/candidates/F2/status.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| F3 | BENCHMARK_ONLY: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | BENCHMARK_ONLY | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=OBSERVED (27 rows; runs research-sp40-f3-field-benchmark); complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/candidates/F3/manifest.json`, `research/candidates/F3/status.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| F4 | BENCHMARK_ONLY: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | BENCHMARK_ONLY | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=OBSERVED (27 rows; runs research-sp40-f4-field-benchmark); complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/candidates/F4/manifest.json`, `research/candidates/F4/status.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| F5 | BENCHMARK_ONLY: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | BENCHMARK_ONLY | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=OBSERVED (27 rows; runs research-sp40-f5-field-benchmark); complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/candidates/F5/manifest.json`, `research/candidates/F5/status.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| H0 | BENCHMARK_ONLY: Full three-language parity is not established; Solidity covers 8 suite-wide anchor vectors, not the required 10,000.; No new security claim is made. | BENCHMARK_ONLY | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=OBSERVED (8 rows; runs research-sp10-h0-gas); complete tx=NOT_EVALUATED; code/deployment=OBSERVED (8 rows; runs research-sp10-h0-gas); sources `research/candidates/H0/manifest.json`, `research/candidates/H0/status.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| H1 | BENCHMARK_ONLY: Binary application layout does not fit.; Full three-language parity is not established; Solidity covers 8 suite-wide anchor vectors, not the required 10,000. | BENCHMARK_ONLY | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=OBSERVED (2 rows; runs research-sp10-h1-gas); complete tx=NOT_EVALUATED; code/deployment=OBSERVED (2 rows; runs research-sp10-h1-gas); sources `research/candidates/H1/manifest.json`, `research/candidates/H1/status.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| H2 | DEFERRED: Full three-language parity is not established; Solidity covers 8 suite-wide anchor vectors, not the required 10,000.; No reviewed composition/security theorem or exact mode exists. | DEFERRED | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=NOT_EVALUATED; complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/candidates/H2/manifest.json`, `research/candidates/H2/status.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| H3 | BENCHMARK_ONLY: Full three-language parity is not established; Solidity covers 8 suite-wide anchor vectors, not the required 10,000.; Independent exact constrained-input mode review is absent. | BENCHMARK_ONLY | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=OBSERVED (8 rows; runs research-sp10-h3-gas); complete tx=NOT_EVALUATED; code/deployment=OBSERVED (8 rows; runs research-sp10-h3-gas); sources `research/candidates/H3/manifest.json`, `research/candidates/H3/status.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| H4 | BENCHMARK_ONLY: Full three-language parity is not established; Solidity covers 8 suite-wide anchor vectors, not the required 10,000.; Independent exact constrained-input mode review is absent. | BENCHMARK_ONLY | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=OBSERVED (2 rows; runs research-sp10-h4-gas); complete tx=NOT_EVALUATED; code/deployment=OBSERVED (2 rows; runs research-sp10-h4-gas); sources `research/candidates/H4/manifest.json`, `research/candidates/H4/status.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| H5 | BENCHMARK_ONLY: Exact mode-aware cryptanalysis and independent review are absent.; Full three-language parity is not established; Solidity covers 8 suite-wide anchor vectors, not the required 10,000. | BENCHMARK_ONLY | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=OBSERVED (8 rows; runs research-sp10-h5-gas); complete tx=NOT_EVALUATED; code/deployment=OBSERVED (8 rows; runs research-sp10-h5-gas); sources `research/candidates/H5/manifest.json`, `research/candidates/H5/status.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| H6 | BENCHMARK_ONLY: Exact width-32 mode analysis and independent review are absent.; Full three-language parity is not established; Solidity covers 8 suite-wide anchor vectors, not the required 10,000. | BENCHMARK_ONLY | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=OBSERVED (8 rows; runs research-sp10-h6-gas); complete tx=NOT_EVALUATED; code/deployment=OBSERVED (8 rows; runs research-sp10-h6-gas); sources `research/candidates/H6/manifest.json`, `research/candidates/H6/status.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| H7 | BENCHMARK_ONLY: Different field and sponge mode are explicit performance confounds.; Full three-language parity is not established; Solidity covers 8 suite-wide anchor vectors, not the required 10,000. | BENCHMARK_ONLY | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=OBSERVED (8 rows; runs research-sp10-h7-gas); complete tx=NOT_EVALUATED; code/deployment=OBSERVED (8 rows; runs research-sp10-h7-gas); sources `research/candidates/H7/manifest.json`, `research/candidates/H7/status.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| T0 | REFERENCE_CONTROL: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | REFERENCE_CONTROL | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=NOT_EVALUATED; complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/candidates/T0/manifest.json`, `research/candidates/T0/status.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| T1 | NOT_SELECTED: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | NOT_SELECTED | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=NOT_EVALUATED; complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/candidates/T1/manifest.json`, `research/candidates/T1/status.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| T2 | REJECTED_EFFICIENCY: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | REJECTED_EFFICIENCY | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=NOT_EVALUATED; complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/candidates/T2/manifest.json`, `research/candidates/T2/status.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| T3 | T3_EXTERNAL_REVIEW_ONLY: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | T3_EXTERNAL_REVIEW_ONLY | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=NOT_EVALUATED; complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/candidates/T3/manifest.json`, `research/candidates/T3/status.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| V1 | BENCHMARK_ONLY: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | BENCHMARK_ONLY | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=OBSERVED (3 rows; runs research-sp31-v1-isolated-benchmark); complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/candidates/V1/manifest.json`, `research/candidates/V1/status.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| V2 | BENCHMARK_ONLY: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | BENCHMARK_ONLY | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=OBSERVED (2 rows; runs research-sp31-v2-isolated-benchmark); complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/candidates/V2/manifest.json`, `research/candidates/V2/status.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| V3 | BENCHMARK_ONLY: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | BENCHMARK_ONLY | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=OBSERVED (2 rows; runs research-sp31-v3-isolated-benchmark); complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/candidates/V3/manifest.json`, `research/candidates/V3/status.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| V4 | BENCHMARK_ONLY: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | BENCHMARK_ONLY | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=OBSERVED (2 rows; runs research-sp31-v4-isolated-benchmark); complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/candidates/V4/manifest.json`, `research/candidates/V4/status.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| V5 | BENCHMARK_ONLY: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | BENCHMARK_ONLY | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=OBSERVED (3 rows; runs research-sp31-v5-isolated-benchmark); complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/candidates/V5/manifest.json`, `research/candidates/V5/status.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| V6 | BENCHMARK_ONLY: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | BENCHMARK_ONLY | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=OBSERVED (4 rows; runs research-sp31-v6-isolated-benchmark); complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/candidates/V6/manifest.json`, `research/candidates/V6/status.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| V7 | BENCHMARK_ONLY: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | BENCHMARK_ONLY | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=OBSERVED (1 rows; runs research-sp31-v7-isolated-benchmark); complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/candidates/V7/manifest.json`, `research/candidates/V7/status.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| V8 | BENCHMARK_ONLY: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | BENCHMARK_ONLY | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=OBSERVED (5 rows; runs research-sp31-v8-isolated-benchmark); complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/candidates/V8/manifest.json`, `research/candidates/V8/status.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| V9 | BENCHMARK_ONLY: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | BENCHMARK_ONLY | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=OBSERVED (14 rows; runs research-sp31-v9-isolated-benchmark); complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/candidates/V9/manifest.json`, `research/candidates/V9/status.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| SP-20 | STOPPED_BY_DEPENDENCY: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | STOPPED_BY_DEPENDENCY | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=NOT_EVALUATED; complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/candidates/air-geometry/manifest.json`, `research/candidates/air-geometry/status.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| deposit-batching | DEFERRED_STOP: measured positive amortized gas at an accepted batch size; real trustless transition proof backend | DEFERRED_STOP | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=NOT_EVALUATED; complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/candidates/deposit-batching/manifest.json`, `research/candidates/deposit-batching/status.json` | security/gas | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| hash-compression-common | BENCHMARK_ONLY: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | BENCHMARK_ONLY | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=NOT_EVALUATED; complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/candidates/hash-compression-common/manifest.json`, `research/candidates/hash-compression-common/status.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| merkle-shape | STOP_HIGHER_ARITY: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | STOP_HIGHER_ARITY | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=NOT_EVALUATED; complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/candidates/merkle-shape/manifest.json`, `research/candidates/merkle-shape/status.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| SP-21 | STOPPED_BY_DEPENDENCY: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | STOPPED_BY_DEPENDENCY | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=NOT_EVALUATED; complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/candidates/structured-relation/manifest.json`, `research/candidates/structured-relation/status.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| C00/v03-baseline | FAIL: SP-00 fails because 9/60 valid fresh Part-A transactions exceed the 16,777,216-gas EIP-7825 cap; abandoned checkpoint storage economics are unresolved | FAIL | proof=OBSERVED (60 rows; runs v03-corpus-01…v03-fixed-30); ABI=OBSERVED (60 rows; runs v03-corpus-01…v03-fixed-30); prover=OBSERVED (60 rows; runs v03-corpus-01…v03-fixed-30); EVM components=OBSERVED (360 rows; runs v03-corpus-01…v03-fixed-30); complete tx=OBSERVED (120 rows; runs v03-corpus-01…v03-fixed-30); code/deployment=OBSERVED (120 rows; runs v03-corpus-01…v03-fixed-30); sources `research/candidates/v03-baseline/manifest.json`, `research/candidates/v03-baseline/status.json` | security/privacy/gas/calldata | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| SP-31/V1-V9 | BENCHMARK_ONLY: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | BENCHMARK_ONLY | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=OBSERVED (36 rows; runs research-sp31-v1-isolated-benchmark…research-sp31-v9-isolated-benchmark); complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/candidates/verifier-optimization-common/manifest.json`, `research/candidates/verifier-optimization-common/status.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| C00 | FAIL_REPRODUCED_BASELINE: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | FAIL_REPRODUCED_BASELINE | proof=OBSERVED (60 rows; runs v03-corpus-01…v03-fixed-30); ABI=OBSERVED (60 rows; runs v03-corpus-01…v03-fixed-30); prover=OBSERVED (60 rows; runs v03-corpus-01…v03-fixed-30); EVM components=OBSERVED (360 rows; runs v03-corpus-01…v03-fixed-30); complete tx=OBSERVED (120 rows; runs v03-corpus-01…v03-fixed-30); code/deployment=OBSERVED (120 rows; runs v03-corpus-01…v03-fixed-30); sources `research/reviews/checkpoint-1-baseline.json`, `research/reviews/checkpoint-2-structural.json`, `research/reviews/checkpoint-3-backends.json`, `research/reviews/checkpoint-4-product.json` | security/gas/calldata | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| C01 | NOT_RUN_JUSTIFIED_GATE_FAILURE: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | NOT_RUN_JUSTIFIED_GATE_FAILURE | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=NOT_EVALUATED; complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/reviews/checkpoint-1-baseline.json`, `research/reviews/checkpoint-2-structural.json`, `research/reviews/checkpoint-3-backends.json`, `research/reviews/checkpoint-4-product.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| C10 | RESEARCH_ONLY_NO_WINNER: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | RESEARCH_ONLY_NO_WINNER | proof=OBSERVED (6 rows; runs research-sp50-c10-fri-b3-q111-c16x16-f0-r4-r0…research-sp50-c10-fri-b4-q48-c16x16-f0-r4-r1); ABI=NOT_EVALUATED; prover=OBSERVED (6 rows; runs research-sp50-c10-fri-b3-q111-c16x16-f0-r4-r0…research-sp50-c10-fri-b4-q48-c16x16-f0-r4-r1); EVM components=NOT_EVALUATED; complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/reviews/checkpoint-1-baseline.json`, `research/reviews/checkpoint-2-structural.json`, `research/reviews/checkpoint-3-backends.json`, `research/reviews/checkpoint-4-product.json` | security/gas/calldata | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| C11 | NOT_RUN_JUSTIFIED_GATE_FAILURE: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | NOT_RUN_JUSTIFIED_GATE_FAILURE | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=NOT_EVALUATED; complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/reviews/checkpoint-1-baseline.json`, `research/reviews/checkpoint-2-structural.json`, `research/reviews/checkpoint-3-backends.json`, `research/reviews/checkpoint-4-product.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| C12 | NOT_RUN_JUSTIFIED_GATE_FAILURE: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | NOT_RUN_JUSTIFIED_GATE_FAILURE | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=NOT_EVALUATED; complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/reviews/checkpoint-1-baseline.json`, `research/reviews/checkpoint-2-structural.json`, `research/reviews/checkpoint-3-backends.json`, `research/reviews/checkpoint-4-product.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| C20 | DEFERRED_UPSTREAM_CONTROL_NOT_INTEGRATED: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | DEFERRED_UPSTREAM_CONTROL_NOT_INTEGRATED | proof=OBSERVED (2 rows; runs research-sp51-c20-native-r0…research-sp51-c20-native-r1); ABI=NOT_EVALUATED; prover=OBSERVED (2 rows; runs research-sp51-c20-native-r0…research-sp51-c20-native-r1); EVM components=NOT_EVALUATED; complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/reviews/checkpoint-1-baseline.json`, `research/reviews/checkpoint-2-structural.json`, `research/reviews/checkpoint-3-backends.json`, `research/reviews/checkpoint-4-product.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| C21 | NOT_RUN_JUSTIFIED_GATE_FAILURE: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | NOT_RUN_JUSTIFIED_GATE_FAILURE | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=NOT_EVALUATED; complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/reviews/checkpoint-1-baseline.json`, `research/reviews/checkpoint-2-structural.json`, `research/reviews/checkpoint-3-backends.json`, `research/reviews/checkpoint-4-product.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| C22 | NOT_RUN_JUSTIFIED_GATE_FAILURE: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | NOT_RUN_JUSTIFIED_GATE_FAILURE | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=NOT_EVALUATED; complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/reviews/checkpoint-1-baseline.json`, `research/reviews/checkpoint-2-structural.json`, `research/reviews/checkpoint-3-backends.json`, `research/reviews/checkpoint-4-product.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| C23 | NOT_RUN_JUSTIFIED_GATE_FAILURE: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | NOT_RUN_JUSTIFIED_GATE_FAILURE | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=NOT_EVALUATED; complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/reviews/checkpoint-1-baseline.json`, `research/reviews/checkpoint-2-structural.json`, `research/reviews/checkpoint-3-backends.json`, `research/reviews/checkpoint-4-product.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| C30 | NOT_RUN_JUSTIFIED_GATE_FAILURE: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | NOT_RUN_JUSTIFIED_GATE_FAILURE | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=NOT_EVALUATED; complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/reviews/checkpoint-1-baseline.json`, `research/reviews/checkpoint-2-structural.json`, `research/reviews/checkpoint-3-backends.json`, `research/reviews/checkpoint-4-product.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| C40 | NOT_RUN_JUSTIFIED_GATE_FAILURE: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | NOT_RUN_JUSTIFIED_GATE_FAILURE | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=NOT_EVALUATED; complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/reviews/checkpoint-1-baseline.json`, `research/reviews/checkpoint-2-structural.json`, `research/reviews/checkpoint-3-backends.json`, `research/reviews/checkpoint-4-product.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| product-aggregation | STOP_BY_DEPENDENCY: accepted PQ-oriented aggregation or folding construction; accepted hiding individual proof | STOP_BY_DEPENDENCY | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=OBSERVED (22 rows; runs research-sp70-sp-70-foundry-components); complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/aggregation/status.json`, `research/reviews/checkpoint-4-product.json` | security/privacy/calldata/prover UX | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| product-individual-l1 | NO_SECURITY_QUALIFIED_FINALIST: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | NO_SECURITY_QUALIFIED_FINALIST | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=NOT_EVALUATED; complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/reviews/checkpoint-4-product.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| product-l2 | PRODUCT_GATE_NOT_EVALUATED_NOT_PASSED: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | PRODUCT_GATE_NOT_EVALUATED_NOT_PASSED | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=NOT_EVALUATED; complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/l2-economics/status.json`, `research/reviews/checkpoint-4-product.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| product-prover-operations | FAIL: CANCELLATION_MISSING; CRASH_RECOVERY_MISSING | FAIL | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=NOT_EVALUATED; complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/prover-operations/status.json`, `research/reviews/checkpoint-4-product.json` | security/prover UX/maturity | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |
| product-robust-two-call | FAIL_PROJECTION_FULL_PATH_NOT_EVALUATED: No security qualification or integration authorization is present in checkpoints 1-4 and SP-80. | FAIL_PROJECTION_FULL_PATH_NOT_EVALUATED | proof=NOT_EVALUATED; ABI=NOT_EVALUATED; prover=NOT_EVALUATED; EVM components=OBSERVED (3 rows; runs research-sp72-sp-72-foundry-harness); complete tx=NOT_EVALUATED; code/deployment=NOT_EVALUATED; sources `research/reviews/checkpoint-4-product.json`, `research/two-call-state/status.json` | security | Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate. |

## 30. Unresolved decisions

The authoritative concise register is [`UNRESOLVED_QUESTIONS.md`](UNRESOLVED_QUESTIONS.md). None is silently assigned zero or treated as passed. The largest blockers are external composed-security acceptance, an eligible fixed relation, and complete integrated operational evidence. Until they close, Outcome D and `RECOMMEND_ADDITIONAL_TARGETED_RESEARCH` remain controlling. [CP4]

## 31. Raw evidence index

Numeric provenance is machine-readable in [`report-source-map.json`](report-source-map.json). Run-level exact SHA-256 and Keccak-256 hashes are in `research/summaries/run-index.csv` and `research/run-records/evidence-manifest.json`; SP-91's complete snapshot inventory is `research/reproduction/evidence-manifest.json`. The final package manifest is intentionally generated separately after review.

- Baseline run records: `research/runs/v03-*.json`; proof/gas distribution: `research/summaries/v03-distribution.csv`.
- Research run records: paths and both hashes in `research/summaries/run-index.csv`.
- Five master tables: `research/summaries/candidate-master.csv`, `security-master.csv`, `gas-decomposition.csv`, `proof-byte-ledger-master.csv`, `prover-master.csv`.
- Scorecards/frontiers: `research/report-synthesis/scorecards/*.json`, `research/report-synthesis/pareto/*.csv`.
- Negative evidence: section 29, `research/reproduction/negative-results.json`, candidate status files, and checkpoints.
- SP-80 bundle evidence: `research/integrated-finalists/status.json` and `outputs/results.json`.
- SP-91 independent result: `research/reproduction/independent-result.json` at clean commit `e318928de5a5aff0bb0a4c0f92c03cb8eea13830`. [SP91]

## 32. Reproduction instructions

Run from repository root against the pinned environment. The exact already-recorded SP-91 commands are:

```sh
python3 research/reproduction/reproduce.py all-safe
python3 research/run-records/reproduce.py check
python3 research/report-synthesis/generate.py --check
python3 research/integrated-finalists/check.py
python3 research/candidates/air-geometry/check.py
python3 research/candidates/structured-relation/check.py
```

SP-92 generation and deterministic checking (the final manifest is separately owned):

```sh
python3 research/final/generate.py
python3 research/final/generate.py --check
```

For the frozen C00 action commands and prerequisites, use `python3 research/reproduction/reproduce.py commands C00`; the exact argv arrays are in `research/reproduction/command-registry.json`. Candidate actions unavailable because no finalist exists must fail closed as `NOT_AVAILABLE_NO_ELIGIBLE_FINALIST`; do not substitute component commands. No command in this section authorizes network broadcast, deployment, secret input, custody integration, or external cryptographic acceptance. [SP91] [REPRO_COMMANDS]

### Numeric source notes

[PLAN]: `PQTC_NEXT_GENERATION_RESEARCH_PLAN.md` (SHA-256 `2da7ab2b570695da4f05d23c135cae1911459b77ad5cc6c2981e6ab7e886353f`)
[BASE]: `research/candidates/v03-baseline/gas/measured-summary.json` (SHA-256 `b40323a7e59445286a95ee0f8604a86f07da1f2e6fc8e34be40e096216181fb6`)
[BASE_STATUS]: `research/candidates/v03-baseline/status.json` (SHA-256 `a6645e3851b02f9a734fcb93357e980f4b622c03a949667f3a97ef3dcb619cf6`)
[SEC]: `research/security-model/v03-q32.json` (SHA-256 `64906f01d7a864d984346436519d5e89677ffc5a5988ca4e02feb6119c4b112f`)
[SEC_STATUS]: `research/security-model/status.json` (SHA-256 `18613d09f3921f479957f3fc423d4241f1028cd1981e1900a92e5da22ca0c90f`)
[CP1]: `research/reviews/checkpoint-1-baseline.json` (SHA-256 `a7841c1581069fc4db87ccb8f0c23a80c05943233ad10cefc285bae6ea748bbb`)
[CP2]: `research/reviews/checkpoint-2-structural.json` (SHA-256 `f358ae71042aa6888a3cf43fe0534a3b40cadd5c0f060fd8f3cc075c1e3da3d2`)
[CP3]: `research/reviews/checkpoint-3-backends.json` (SHA-256 `c84297a081923a9c2fcdfd1963f5178b337c186fb9201028cb816435564d2416`)
[CP4]: `research/reviews/checkpoint-4-product.json` (SHA-256 `978c65c77f5ee137745aa279a2da8dfb8229b13ecd244432e80c91c738975526`)
[SP10]: `research/candidates/hash-compression-common/status.json` (SHA-256 `10f3c7827bf9ee54ba03870ab5dc904547d392c6d9136a613965db8250365dba`)
[SP11]: `research/candidates/merkle-shape/status.json` (SHA-256 `5d1db6c9aa3aa2763cebdacbdd7d94695e71646e60250918fc7b3454cdd5440c`)
[SP20]: `research/candidates/air-geometry/status.json` (SHA-256 `8321cc23f96e39580cd883a2e4c0c5273cae5e1c3d4c20727a4b2eec896618f1`)
[SP21]: `research/candidates/structured-relation/status.json` (SHA-256 `4be57fede7e0a6060ba6472840d2541292f4537846c2f283162e4e8cd9599ad1`)
[SP31]: `research/candidates/verifier-optimization-common/status.json` (SHA-256 `6e38c2e19a783f3c6cc6019f33379cb1d492fa86f778c3a6d084c139677009cf`)
[SP31_RESULT]: `research/candidates/V9/outputs/benchmark.json` (SHA-256 `fe73c1a12d2445bf175d462b88d25dcf297e046b43de63e4b532d57fa87ce5bd`)
[SP40]: `research/candidates/field-bakeoff-common/status.json` (SHA-256 `f6a7ce97ef7f6208c148a3a6fc35e9d9b599ab9543e7c9a31be0178bfddb317a`)
[SP50]: `research/fri-pareto/status.json` (SHA-256 `bc97cbd955ab678dc5062a996e268f1e82774f16e2f4b1c8f66450d2fdd4248e`)
[SP51]: `research/candidates/C20-hvzk-whir/status.json` (SHA-256 `704e9713f6a89a69481fb09e9e5366629cf70035142128d5dff75794a118b355`)
[SP52]: `research/candidates/C30-stir/status.json` (SHA-256 `2de22d525da839a8939d62d35fdd7963559fac9de581a1aed99467d424942fe3`)
[SP53]: `research/candidates/C40-circle/status.json` (SHA-256 `0f02c185f5bb8216df09efacab905812d1a9765b18a5c6bdd06098035213844a`)
[SP60]: `research/candidates/C50-spartan-whir/status.json` (SHA-256 `e31f38dd317166fd7e2ba01b8c59e2570df4c809953aa215b889609567d130ae`)
[SP61]: `research/candidates/C60-recursion/status.json` (SHA-256 `4ca31e4263ba5b8326b771e39e439a99c40551b59f9b6a7b47ee919c849c0111`)
[SP62]: `research/candidates/C70-flock-veil/status.json` (SHA-256 `94f28e66d12278d183fcb7c4ec3dc80bf3ef97a2fb69d5f8cb6dc448b4f7e9aa`)
[SP70]: `research/aggregation/status.json` (SHA-256 `06a3d71a50ac22e062dc6b086111287917c7f44258da02491bf4461b45e49815`)
[SP71]: `research/l2-economics/status.json` (SHA-256 `37c3044ca217f3f99ec3237152ca4a48224c541d378e5bb876db230c95c764ae`)
[SP72]: `research/two-call-state/status.json` (SHA-256 `407538bf1572c859b15bc86a36e4782dafe7ca92ef787ec99385d742bd7e271d`)
[SP73]: `research/prover-operations/status.json` (SHA-256 `e602826a700841f60abbde910f6c78f5c9ee5f7ddd3ebe35e04a2e043ed1e8b9`)
[SP80]: `research/integrated-finalists/status.json` (SHA-256 `337a451fe3380f1c2169999417cd87372a35545fdc5e278b7c4fd11010da4b6d`)
[SP80_RESULT]: `research/integrated-finalists/outputs/results.json` (SHA-256 `98334597a3e55cba1d6e7da8ab3ab99af451ae7d96fe7fe423480d45131abedb`)
[SP91]: `research/reproduction/independent-result.json` (SHA-256 `28e3d6ab5ed818a89d5f62706cc24e8b44a5fe93521086589a1c7cfb362ebf7c`)
[ADVISORY]: `research/advisories/status.json` (SHA-256 `8851a890f7011735515c9b17e4c880ad1be3e1c2cbce70ade6841de82c625156`)
[FORMAL]: `research/formal-assurance/status.json` (SHA-256 `84977b8742f14542eb033889c47b6c7cfa3cfe973996f777eb4bf4e288fa30cc`)
[RUNTIME]: `research/runtime-binding/status.json` (SHA-256 `402e9face9b75fa31a907b58f5a058b1ade86168fa3cb498743ea79c16b1308a`)
[PUBLIC]: `research/public-statement/status.json` (SHA-256 `5a977458ecd79353628fb201db0406b397edf2ff4e8a7af848f1aa2ce4e68a3a`)
[DIGEST]: `research/digest-width/status.json` (SHA-256 `a94e24e03b6b483e981530d9733a5c6b72572b68fcfad79e3eb284af6efbf370`)
[CANDIDATES]: `research/summaries/candidate-master.csv` (SHA-256 `3d0a6a7e494449d49597fee4b719c933e54a6294cc4fa759d78d2b92105b6239`)
[SECURITY]: `research/summaries/security-master.csv` (SHA-256 `8af2a3b716a96386885f08c45f8f45ff72bca666bd2d9e2cd2feb37fb9f081ce`)
[GAS]: `research/summaries/gas-decomposition.csv` (SHA-256 `b3c668f844b4cd3a2d0c69c66352051dbffca63b530f56f721a5da71b72014f9`)
[PROOF]: `research/summaries/proof-byte-ledger-master.csv` (SHA-256 `6e702397a4ae9e15a9391c9b0bbe111bacf5f92882fcf8dcf2268e20703a94a8`)
[PROVER]: `research/summaries/prover-master.csv` (SHA-256 `09394dd0650780723209ece4dcb2f3086e63226d31a196692caffe85a01b8550`)
[RUN_INDEX]: `research/summaries/run-index.csv` (SHA-256 `6ffb7146836a1a6edd9e762cbd42bf2b41310af7418b643be6e1fee65a8a24aa`)
[SCORECARDS]: `research/summaries/candidate-scorecards.csv` (SHA-256 `59dbc8bf29eb02a4fc45aa02bedde046c73a60b6a85fd02ac3241a13210fa77a`)
[MINIMUM]: `research/summaries/minimum-candidate-matrix.csv` (SHA-256 `afd1811bd3449b6d3f25e28024c5128a09a2f497feca73a9048c14ad82744afc`)
[SP90]: `research/summaries/spike-results.json` (SHA-256 `dd05ab3de76e61dc2af054eb405bb75bf5cea66234c505ba817f5d73d967541e`)
[REPRO_COMMANDS]: `research/reproduction/command-registry.json` (SHA-256 `257eafca97be3523dab85c35a7d274c9d7dc8e74e89cbce54e5c20cc0def2cf6`)
[REPRO_NEGATIVE]: `research/reproduction/negative-results.json` (SHA-256 `0401e81c7e672e374b26fa33c4d6bdb014d04c04e56dc4726020ab835e345501`)

