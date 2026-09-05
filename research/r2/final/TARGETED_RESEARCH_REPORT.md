# PQTornadoCash — Targeted Research Return

**Return version:** R2.0 halt checkpoint,2026-09-05. **Status: PAUSED_BY_USER; research incomplete.**
**Public review commit:** `e51a5c5ccc4f50e0beb07cdf04d7f8dd258c7997`.
**Published progression before halt:** `d273f5a`, `3242e02`; current checkpoint is the commit containing this report.
**Environment:** Darwin24.6.0/arm64, Apple M4 Max,48GiB; Rust1.97.0; Foundry1.7.1 commit4072e48705af9d93e3c0f6e29e93b5e9a40caed8.
**External cryptographic review:** not accepted; further reviews deferred by user. No public deployment authorized by this document.

## 1. Decision and what changed

The user halted research. No final R2 architectural decision, winning configuration, or full engineering specification is selected. The next requested domain is R2-06, not an automatic restart of the deferred R2-05 transcript work.

Unlike the earlier metadata-only stops, this checkpoint contains actual C1/C2/C3 native hiding proofs, clean baseline reproduction, exact signed local capped transactions, formula execution and concrete PCS trait failures. The original pool constructor and a retained withdrawal A failed under the actual local cap. These are specific measured failures, not a rejection of privacy research or of every architecture. Product readiness and cryptographic qualification remain separate from permission to experiment.

## 2. Required experiment completion matrix

| Package | Completed executable stage | Remaining at halt | Evidence |
|---|---|---|---|
| R2-00 | Clean builds; five metadata checks; retained+10 fresh proof/codec/Foundry checks; signed local CREATE/A/B controls and ledgers | Wider capped distribution and synthesis | `../baseline/outputs/r2-main/results.json` |
| R2-01 | Three arithmetic paths, full-m objectives, object mapping, reduced-round experiment | Candidate-shape normalization; unresolved theorem conditions | `../security/outputs/c0/results.json` |
| R2-02 | Complete role/tier source; Rust build | Constants/three-language parity/misuse and matched measurements | `../hash/execution.json` |
| R2-03 | One C1 decomposed native hiding proof | Other geometries, mutations, repetitions, normalized and EVM results | `../air/outputs/C1-decomposed/results.json` |
| R2-04 | One complete C2 and one matched C3 hiding proof | Full causal/codec controls, repetitions, parity/mutations, EVM arithmetic | `../air/outputs/C2-horizontal-02/results.json`, `../air/outputs/C3-decomposed/results.json` |
| R2-05 | Source and q32 native build | Complete experiment explicitly deferred by user | `../transcript/INCOMPLETE.json` |
| R2-06 | Model checks and historical byte residuals; actual anchor binary built | First fresh anchor, grid, EVM fit and frontier | `../models/outputs/historical-calibration.json` |
| R2-07 | Missing-trait reproducers executed; actual native controls compiled | Execute native/repair and standalone EVM control | `../backend/outputs/api/results.json` |
| R2-08 | Frozen baseline local transactions; native availability and real native deposit history | New pool, transcript splits/lifecycle, payout adversaries,100-proof workload | `../operations/outputs/containment-01/results.json` |
| R2-09 | Exact retained L2 envelopes; bounded Flock source search; hardware inventory | Conditional entry checks and eligible executions | `../conditional/outputs/` |

The overall stop is a **user-requested project-policy pause**, not a cryptographic failure or resource quota. The received internal reviews do not constitute external acceptance or completion of checkpoints A–F.

## 3. Provenance and reproduction

`REPRODUCTION.md`, `RUN_MANIFEST.json` and `EVIDENCE_MANIFEST.json` provide the command/evidence index. All five clean public-pin checks returned0: manifest, all-safe, run-records, report and final. They are explicitly metadata-only. Clean Rust/Foundry builds and fresh proofs were separate commands.

The clean/instrumented source workspace is recorded in `../baseline/outputs/r2-main/workspaces.json`; it is disposable and may be absent on another machine. Compiler JSON artifacts are archived separately. Exact original source pins, instrumentation patch, source epochs and cleanup-before/after checks are retained. Build products are excluded from Git and must be rebuilt. The original pre-R2 evidence was not rewritten.

Current `security/run.py` gained a shape-input adapter after the executed C0 analysis; use the source version at3242e02 for that historical observation. Current native worker source also has an unexecuted export option added after containment measurements. Historical source/binary hashes are not silently replaced with current hashes.

## 4. Baseline distribution and byte ledger

The original60 runs remain historical and are not pooled with the11 new retained/fresh verification records. R2 generated ten fresh proofs: five fixed-witness and five varied cases; all ten distinct proof IDs. The eleventh is a retained control, not a fresh sample.

Exact `Reader::take` spans, raw sections, ABI sections and signed-unbroadcast RLP sizes are retained per fixture. `BYTE_LEDGER.csv` indexes component rows; each raw and ABI component sum is checked. The fresh case000 control has208,812 raw canonical A+B bytes and209,480 ABI A+B bytes. This checkpoint does not claim a30-run distribution, high-percentile uncertainty interval or100-proof operational campaign.

## 5. Baseline gas and deployment

Actual signed local transactions used Osaka with explicit EIP-7825 enforcement and a16,777,216 block/transaction gas limit. Runtime/initcode limits were not disabled. Prague with a1,000,000,000 block limit was a separate diagnostic endpoint, not a cap-feasibility measurement.

| Frozen component | Capped CREATE gas used | Outcome | Compiled runtime bytes |
|---|---:|---|---:|
| AIR verifier | 3,906,341 | Success | 17,827 |
| Query verifier | 2,859,327 | Success | 12,989 |
| Registry | 2,894,140 | Success | 13,122 |
| Pool | 16,777,216 | Failed constructor | 7,494 |

Retained A used108,644 ABI bytes and failed under the cap, with receipt gas16,425,128. The call trace contains an inner `out of gas`. Separate high-gas A/B completed at16,761,123/13,965,052gas; B used104,228 ABI bytes. A below-cap gas-used value in a high-gas execution is therefore not sufficient evidence that a capped submission succeeds. Gas forwarding and nested call limits must remain part of the actual submission experiment.

`GAS_LEDGER.csv` points to nonoverlapping attribution and residuals. Call-trace inclusive totals are not added as independent components. Calldata floors are not added to execution gas. Constructor/hash/storage/code-deposit data and compressed full opcode traces are retained. No new optimized-constructor pool deployment was executed.

## 6. Security-model results

### 6.1 Pinned-equivalent versus alternative analysis

The executed C0 package produced9,180 term rows and18 pinned native rows. For the declared q32 conditional-Johnson, quantum-grinding-only sensitivity, optimizing FRI alone selects m185 and56.201226486bits; optimizing the full minimum selects m23 and71.007139340bits. The corresponding dominant-epsilon error-sum at m23 is70.055062367bits; optimizing a minimum and optimizing a probability sum are not the same objective.

These values are conditional arithmetic, not system security. The supplied independent sensitivity, untouched native APIs and translated formulas remain separate. Dominant/full epsilon, classical/quantum-grinding-only and UDR/conditional models retain their labels. Current C1/C2/C3 shapes have not yet been processed through the normalization experiment.

### 6.2 Actual batching-object mapping

The C0 source inventory distinguishes210 nominal functions,330 committed base columns including extension decomposition/masks, and524 point-specific reductions including the second trace opening. No count is automatically substituted for a theorem's batching parameter. The new proof inventories export observed matrix widths, rotations and quotient chunks for later analysis.

### 6.3 Threat games and lifetime

Eight separate games and their assumptions are retained in `../security/threat-games.json` and executed output tables. Note theft, useful collisions, membership/proof forgery, continuation substitution and witness hiding are not reduced to one digest-width number. Exact theorem object applicability, lifetime/useful-attack reductions, Fiat–Shamir/QROM, commitment binding and hiding composition remain unresolved. Review deferral does not gate measurements.

## 7. Exact hash modes and structural review

`../hash/spec.json` pins the complete H5 width32/d12 roles, constants, controls, feed-forward and output layout. Independent Rust/TypeScript and Solidity reference/optimized tiers exist. Only the Rust package was built; no10000-vector three-language parity, constants-comparison or implementation misuse campaign ran before the halt.

The executed reduced-round experiment demonstrates a scoped first-round mechanism and a second-round nonextension example. It is not a full-round H5 break. Attack applicability with unknown cost remains unknown; no concrete full-mode attack work factor is fabricated.

## 8. Matched implementation-tier results

All new matched H0/H5 Solidity tier gas, two constant-access strategies, complete experimental deposit and constructor results are **not evaluated**. No generic hash gas multiplied by20 is presented as a complete deposit. The original frozen pool measurements in section5 are distinct from the unexecuted new hash envelope.

See `../hash/execution.json` for the exact pending command, five tier names, constants regeneration and full-role/misuse requirements. Optional H6 was not implemented or measured.

## 9. Causal AIR comparison

| Pipeline | Native verified | Codec | Proof bytes | Prove ms | Verify ms | Peak RSS bytes | Samples |
|---|---|---|---:|---:|---:|---:|---:|
| H0 horizontal C0 | Yes,11 verification records | Canonical two-part | Per-fixture ledger | Per-run metadata | Per-run metadata | Per-run metadata | 10fresh+1retained |
| H0 vertical C1 decomposed | Yes | Postcard1.1.3 | 316,794 | 2,833.1275 | 3.743166 | 468,205,568 | 1 |
| H5 horizontal C2 | Yes | Postcard1.1.3 | 171,691 | 236.829417 | 30.297125 | 20,250,624 | 1 |
| H5 vertical C3 decomposed | Yes | Postcard1.1.3 | 287,584 | 1,760.42675 | 3.77425 | 290,848,768 | 1 |

All three first controls used q32, log-blowup4, four hiding random functions and16/16 grinding settings. Shapes, constraints, quotient chunks, actual matrix widths and recursive byte ledgers are retained. C2/C3 share the same complete H5 case. H5 includes22 private-relation plus13 public-role permutations, unlike the frozen H0 predicate; do not attribute all differences to compression alone.

The same-codec C0 exporter compiled but was not run. No cross-codec byte winner or fixed-versus-security-normalized conclusion is selected. Other geometries, actual mutation proofs and repeated fixed/varied timings remain pending.

## 10. Transcript, codec, and verifier integration

**Incomplete and explicitly deferred by user.** q32/q48 typed-epoch and full-width continuation source, codec, TypeScript/Solidity parity runners and64-block lifecycle logic were implemented; q32 native compilation passed. The complete changed-transcript proof, cross-language verification and signed local one-call/split tests were not executed. No savings, lifecycle correctness or q48 feasibility is claimed from source alone.

## 11. Calibrated FRI/Pareto analysis

Model invariant checks passed. The historical byte formula matched all six retained observations over three historical configurations with zero byte residual. These were not re-proved or new timing samples. No alternative EVM workloads were available for fitting: gas coefficients remain null and the gas model remains uncalibrated.

The status migration preserves old rows while replacing an unmeasured physical failure with null/UNKNOWN in R2. The11-slot real anchor runner compiled but **no new anchor ran**. It is the next resume domain. Separate measured/projected frontiers and assumption groups remain required; missing complete gas is not failure.

## 12. Same-relation alternative backend

Executed compiler reproducers demonstrate that pinned `HidingWhirPcs` lacks the frozen uni-stark `Pcs` and multi-stark `PrescribedPointPcs` interfaces. The exact H0 non-hiding WHIR control and actual-trace Poly hiding repair compiled. Neither binary was executed before the halt.

The repair's intended exposed-evaluation experiment and the outer zerocheck hiding gap are described in `../backend/adapter.json`; they remain unexecuted hypotheses/experiments, not claimed recovered-secret measurements. Full hiding relation completion, malformed/privacy checks,32/128 derivations and the standalone Solidity harness repair remain pending. License declarations/unknowns are recorded without legal clearance claims.

## 13. Complete local operational results

Only the **frozen actual-verifier baseline** was exercised locally. Its capped A failed; the diagnostic A/B path completed and the runner checked state/payout/checkpoint outcomes. There is no completed new local pipeline, no direct one-call measurement and no executed12/20,14/18 or stronger-regime comparison.

The scope-pinned pool source generator, payout receiver, transcript integration and100-proof operational workload remain pending. Do not substitute the native4096-deposit history or a source-only pool for mined pool behavior.

## 14. State, privacy, and availability

The native availability diagnostic accepted two valid controls, rejected seven serialized mutations and ten constructed mutations, and recovered for valid requests. No natural panic was observed. Input byte ceilings and process/wall-time containment were exercised; no platform-enforced RSS ceiling or global panic-freedom proof is claimed.

R2 corpus corrections distinguish public byte seeds from mapped canonical fields. Public deterministic fixture entropy is zero; the Fp^8 domain-size logarithm is247.2551247706009, not fixture secrecy. The4096-deposit native regenerator retains279 valid withdrawal cases and matched the first eight outputs of an independent full-tree implementation.

New checkpoint expiry, cancellation, replacement, malicious prefixes, replay, payout rollback and censorship experiments have not run. Part A is not treated as a proof of ownership or complete knowledge.

## 15. Conditional branches

Exact retained A/B proof/ABI envelopes were evaluated offline under pinned L2 source/fee rules. Concatenation is a transport control, not a valid combined verifier ABI. No L2 receipts or exact L2 verifier gas were measured.

The Flock search inspected64 existing local commits; no supported same-commit M21 candidate was found. This is a bounded source-availability result, not an architecture failure; no guessed preset was built. Hardware inventory found this arm64 host, no configured SSH hosts and no x86 emulator. Portable proof execution, recursion, proof-only aggregation and STIR/Circle entry checks remain pending.

## 16. Negative results and rejected hypotheses

- Frozen capped pool constructor failed; revisit with a scope-correct constructor optimization and actual signed CREATE.
- Frozen capped A failed despite its separate high-gas receipt being below the nominal cap; revisit actual split/gas-forwarding behavior, not component-sum estimates.
- Initial CREATE signing failed at CLI parsing; common flags were moved before `--create`, and the retry executed.
- C2 stalled in symbolic DAG export before proof generation; memoization repaired it and the retry proved/verified. The interrupted attempt is not a cryptographic rejection.
- An offline calculator build lacked a cached locked dependency; downloading it resolved the build.
- Initial geometry compilation needed an explicit coefficient type; fixed and rebuilt.
- Paired local service exit137 events had no established cause. Detached services completed the local run and were later explicitly stopped.
- User-reported platform cybersecurity interruptions are recorded separately from compiler/EVM/proof outcomes; their internal cause was not available to the assistant.

## 17. Remaining questions

`UNRESOLVED_QUESTIONS.md` assigns owners, decisive experiments, dependencies and affected decisions. `FINDINGS.json` retains all20 original findings with scoped R2 corrections and unresolved portions. Neither an unexecuted implementation nor a successful metadata check closes a scientific question.

## 18. Proposed next action

Keep the research paused. When the user requests resumption, validate this checkpoint, run the explicit R2-06 C0 anchor command in `../RESUME.md`, then continue the bounded model/backend avenues. Preserve the user's R2-05 deferral rather than silently restarting it. No broad research reset or production engineering specification is warranted by this halt record.

## 19. Evidence validation record

`validate_checkpoint.py` checks retained artifact hashes, raw/ABI and recursive postcard byte sums, proof flags, all20 original finding identities, paused goal state and manifest invariants. Its result is `checkpoint-validation.json`. This is record validation only: it does not rerun proofs, restart nodes, qualify security, establish missing experiments or assert report completeness from headings. Final comparative validation and external review remain future work.
