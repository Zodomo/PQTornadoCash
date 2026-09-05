# PQTornadoCash — Targeted Research Return

**Return:** R2.2 resumed research return with explicit incomplete dispositions. No final architecture selection or engineering specification.
**Public review pin:** `e51a5c5ccc4f50e0beb07cdf04d7f8dd258c7997`.
**Authorization:** isolated local research only. Security qualification and production readiness are not claimed. Further reviews and R2-05 remain separately deferred.

## 1. Decision and what changed

No full engineering specification is recommended. `DECISION.md` records why none of the allowed final-selection categories is established. This is a dispositioned incomplete return, not full plan acceptance. R2-05 remains explicitly user-deferred and R2-08 interrupted. Independent experiments did execute:76 parameter anchors,240 measured causal proofs plus16 warmups, full hash parity/misuse and matched costs, seven Solidity arithmetic evaluations, held-out component gas fits, backend controls and64 portable ARM proofs.

## 2. Required experiment completion matrix

`../governance/resume-status.json` gives completed and missing scope for every R2-00 through R2-10 package. `ACCEPTANCE_DISPOSITIONS.json` retains all124 normative headings and their requirement text with explicit package dispositions; it does not infer individual acceptance from a package label. R2-00/01/02/03/04/06/07/09 have executed evidence and scoped gaps. R2-05 is user-deferred; R2-08 is interrupted; external review checkpoints and final selection remain incomplete.

## 3. Provenance and reproduction

The retained checkpoint validation passed for3137 evidence files,20 findings,11 baseline proof records,3 AIR proof records and7 reconciled receipts before changes. Original halt files and manifest are archived in `../governance/halt-bc71758/`. Original pre-R2 evidence is unchanged. Run commands and source epochs remain attached to their actual attempts, not retroactively replaced with newer source hashes. `../governance/resume-node-provenance.json` records fresh loopback Osaka/Prague chains; halted state was not restored. Foundry runs use isolated `/tmp` roots; no `.env` was read or sourced.

## 4. Baseline distribution and byte ledger

The original60 historical records and11 retained baseline proof/ledger controls remain separate. Fresh causal observations comprise30 fixed and30 varied proofs per C0/C1/C2/C3, with two discarded warmups per stratum, independent process invocations and256 unique proof hashes overall. C0 canonical proofs were decoded and exported to the same postcard1.1.3 representation used for the comparison. Canonical A/B, research C10 and postcard remain distinct. `BYTE_LEDGER.csv` retains detailed original canonical ledgers and appends disjoint native sections. New C0 distribution canonical sub-section instrumentation is not claimed; whole-proof bytes and export verification are known.

## 5. Baseline gas and deployment

Retained capped Osaka CREATE gas: AIR3,906,341; query verifier2,859,327; registry2,894,140; original pool failed at16,777,216. Retained capped A failed with inner out-of-gas, receipt16,425,128. Separate high-gas Prague A/B controls used16,761,123/13,965,052; these do not establish capped feasibility. `GAS_LEDGER.csv` retains nonoverlapping receipt reconciliation and explicit residuals. New hash-deposit envelopes are not this frozen pool.

## 6. Security-model results

Three calculators processed C0/C1/C2/C3 shapes:83,304 term rows and72 pinned native rows at `../security/outputs/resume-shapes-02/`. First attempt failed because observed commitments use numeric IDs whereas the adapter compared names; the repair matched the actual inventory, and changed-width regression checks reject mismatches. C0 q111/b3 and C2 q101/b4 reach the declared100-bit no-additional-Johnson arithmetic target. C1/C3 and all conditional-Johnson profiles do not reach that target in the declared sweep. This is conditional arithmetic, not system security. The210/330/524 theorem-object distinction, QROM, lifetime, MMCS and hiding composition remain open.

## 7. Exact hash modes and structural review

H5 exact role/layout and attack/game matrices are retained under `../security/outputs/resume-shapes-02/`. Constants comparison,23322 shared full-role vectors and51 actual misuse cases passed across Rust, TypeScript and the deployed Solidity tiers in `../hash/outputs/resume-full-03/`. The final cost continuation reused that parity only after checking source hashes; it did not count it as new samples. Generated Yul parameter shadowing was corrected before successful compilation. This establishes scoped implementation parity, not hash security or a full-round break.

## 8. Matched implementation-tier results

`../hash/outputs/resume-costs-06/` completed five deployed tiers,50 benchmark rows, native repeated workloads and constructor/deposit receipts. Twenty-level compute-only estimates: H0Reference127933472 gas; H0Optimized14571299; H5Reference43461999; H5Packed6974225; H5Straight6438564. These are `eth_estimateGas` workloads, not complete withdrawal receipt gas. State-changing deposit receipts remain separately identified.

Full/limited diagnostic trace attempts and later node exit137 interruptions remain retained. Both nodes were restarted without optional step tracing for the successful cost continuation. Complete opcode attribution is missing; no cause for exit137 was established. Native times, estimated gas, internal kernel gas and receipt totals are never pooled.

## 9. Causal AIR comparison

All seven bounded geometry controls and C1/C2/C3 invalid-trace/public/configuration mutation campaigns executed. Decomposed vertical geometries remained the primary comparison based on the observed smaller/faster controls. H5 includes22 private-relation and13 additional public-role permutations, not merely a substituted compressor. The public-context study is `../air/outputs/resume-public-context/public-context-study.json`.

| Candidate | Stratum | n | Postcard bytes median | Prove ms median | Verify ms median |
|---|---|---:|---:|---:|---:|
| C0-fixed-b4-q32 | fixed | 30 | 195318.0 | 546.069 | 2.126 |
| C0-fixed-b4-q32 | varied | 30 | 195048.0 | 544.948 | 2.124 |
| C1-fixed-b4-q32 | fixed | 30 | 316603.5 | 2476.538 | 3.743 |
| C1-fixed-b4-q32 | varied | 30 | 316316.0 | 2452.691 | 3.714 |
| C2-fixed-b4-q32 | fixed | 30 | 173634.5 | 384.646 | 28.471 |
| C2-fixed-b4-q32 | varied | 30 | 172923.0 | 398.380 | 28.792 |
| C3-fixed-b4-q32 | fixed | 30 | 291468.5 | 1617.899 | 3.881 |
| C3-fixed-b4-q32 | varied | 30 | 289898.0 | 1652.107 | 3.805 |

Source: `../air/outputs/resume-causal-distributions-01/summary.json`; includes min/max, dispersion and nearest-rank percentiles. Thirty samples do not establish a population p99. C2 saves about11% of postcard bytes relative to C0 but takes about13 times as long to verify natively. Vertical scheduling does not improve proof bytes in this comparison.

All seven capped arithmetic evaluator calls returned out-of-gas after successful deployment. Separate Prague diagnostics passed Solidity/native arithmetic parity and changed-tape/noncanonical-input rejection. Receipt gas: C1-decomposed: 34161834 gas; C1-lanes4: 34645818 gas; C1-whole-round: 33430153 gas; C2-horizontal: 85093629 gas; C3-decomposed: 49640090 gas; C3-lanes4: 53993833 gas; C3-whole-round: 48067337 gas. These tape interpreters are not STARK verifiers; their costs include tape calldata and interpretation. They do not bound an optimized complete verifier.

## 10. Transcript, codec, and verifier integration

R2-05 remains explicitly deferred by user. Its source/q32 build is not a completed changed-transcript proof or local-EVM experiment. New splits and lifecycle checks that depend on it remain deferred. Native AIR configuration binding and existing frozen transcript controls do not restart that domain.

## 11. Calibrated FRI/Pareto analysis

First C0 anchor and grid produced20 verified proofs; C1/C2/C3 added18/20/18. All76 accepted rows have zero structural byte residual. The typed postcard model corrected the false all-varint assumption: Montgomery fields use fixed four-byte little-endian serialization. The retained regression rejects changed wire bytes.

`RESUMED_MEASUREMENTS.json` separates native frontiers by relation, codec and security regime. Two observations per parameter point are anchors, not distributions. C0/C2 conditional arithmetic-normalized profiles remain distinct from fixed controls; unreachable slots remain unavailable.

`../models/outputs/resume-component-gas-02/` contains36 actual component rows for18 fixed-regime proofs and a whole predeclared held-out b4/q48 profile. Maximum held-out error:2093.08 gas for independent-node hashing,777.00 gas for base-field opening accumulation. Parse/scan controls and rank diagnostics are separate. Fits include implementation-specific overhead and prioritize only within their stated domain; full verifier/transaction gas remains null. The gas adapter was repaired to exclude nonexecuted normalized records rather than treating absent command records as measurements.

The field-continuation gate executed at `../models/outputs/resume-field-decision.json`. No alternate field entered: there is no nonoverlapping complete narrow-verifier arithmetic inventory. AIR-only and base-field component measurements cannot supply that denominator.

## 12. Same-relation alternative backend

At32, the original non-hiding H0 control generated a proof but returned `Zerocheck(FinalSumMismatch)`. The bounded repair removed the univariate degree7 hint from a backend-local wrapper, allowing pinned multilinear zerocheck to derive degree8 without changing H0 constraints. The repaired serialized proof verified:34,290bytes,79.323667ms prove,6.765125ms verify, one observation. Scope/root/nullifier/payout, opening and truncation mutations rejected. Evidence: `../backend/outputs/resume-h0-degree-32/`.

Two exact-trace hiding PCS openings verified and revealed the eight requested synthetic secret limbs by construction. This is not a break of the PCS hiding guarantee; it demonstrates why that repair is not a complete hiding outer relation proof. Exact128 zero-PoW requests failed with required35/native and41/hiding PoW bits. No guessed replacement preset or global128-bit impossibility claim. Full hiding outer zerocheck and prescribed-point adapter remain missing; licenses are declarations, not legal clearance. The bounded standalone Solidity harness repair reached the actual upstream runtime-size barrier:31856 bytes exceeds24576. No receipt was produced, and no gas number is inferred from that pre-broadcast barrier.

## 13. Complete local operational results

No new complete operational pipeline is claimed. The operational source-preparation worker ended with provider `cyber_policy` error; it did not finish its handoff or execute the new constructor/deposit/payout/100-proof campaign. `../operations/RESUME_INCOMPLETE.json` preserves that state. This interruption is neither an EVM failure nor a cryptographic result. Independent avenues continue.

## 14. State, privacy, and availability

The halt's two valid controls, seven wire mutations, ten constructed mutations and recovery checks remain measured; no natural panic was observed. The4096-deposit native history and279 withdrawal cases are synthetic regenerators, not4096 mined deposits. New checkpoint expiry/replacement/censorship and payout rollback remain unexecuted. Part A is not an ownership proof.

## 15. Conditional branches

Source-pinned conditional gates and five exact-native-payload transport diagnostics executed. Native postcard/C10 payload transport is not EVM ABI compatibility, L2 verifier execution or an actual fee. Flock remains blocked by the supported M21 configuration gap in the64-commit search; STIR/Circle and recursion/aggregation lack the exact compatible hiding/outer paths recorded in the gate evidence. No proxy proof or guessed preset was used.

Portable `target-cpu=generic` ARM build completed;64 proofs verified across requested thread settings1 and4: one first-process observation, one excluded warmup and30 subsequent independent processes per setting. `../conditional/outputs/resume-portable-summary.json` retains the results. This is the same ARM machine, not scalar/no-SIMD proof, actual worker-thread utilization or commodity-x86 performance. An explicit compatible x86 host/executable remains unavailable; no private SSH configuration was read.

## 16. Negative results and rejected hypotheses

Retain original capped constructor/A failures; numeric security adapter mismatch and repair; all-varint postcard model falsification and typed repair; generated Yul shadowing and compilation repair; diagnostic hash trace disconnect and bounded trace retry; non-hiding WHIR degree-hint mismatch and successful bounded repair;128 zero-PoW derivation failures; operational provider interruption. Each has its own scope. None rejects all architectural alternatives.

## 17. Remaining questions

`UNRESOLVED_QUESTIONS.md`, `FINDINGS.json` and package resume status retain owners and decisive experiments. All20 original finding identities remain intact. Further reviews do not gate authorized experiments.

## 18. Proposed next action

No production or engineering-spec scope is selected. `DECISION.md`, `OPPORTUNITY_MATRIX.csv` and `UNRESOLVED_QUESTIONS.md` record exact missing artifacts and reopen conditions. R2-08 may resume from its interrupted record; R2-05 must not restart without explicit user instruction. All experiments have stopped; disposable node state was not persisted.

## 19. Evidence validation record

`validate_checkpoint.py` checks manifest hashes, all20 original finding identities, original canonical ledgers, accepted anchor bytes, component receipt/parity records,256 unique causal proofs and eight30-sample measured strata. `GAS_LEDGER.csv` retains original exclusive reconciliations and labels new unsplit receipt totals as unattributed, never component-derived complete gas. `RESUMED_RECEIPTS.csv` records158 new distinct receipts. The validator does not rerun proofs, qualify security or certify full plan acceptance. Large raw traces/tables retain lossless compression mappings and historical source epochs.
