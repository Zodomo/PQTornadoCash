# PQTornadoCash — Targeted Research Return

**Return:** R2.1 progress from `bc7175895ebef241914bb15f2902a55683d5485b`; research continues, no final decision.
**Public review pin:** `e51a5c5ccc4f50e0beb07cdf04d7f8dd258c7997`.
**Authorization:** isolated local research only. Security qualification and production readiness are not claimed. Further reviews and R2-05 remain separately deferred.

## 1. Decision and what changed

Continue the existing plan. The resumed experiments now include76 verified parameter-anchor proofs, all bounded AIR geometries, actual AIR mutation proofs, candidate security arithmetic and an exact H0 non-hiding WHIR proof after a bounded compatibility repair. No complete new hiding EVM path or engineering specification is selected.

## 2. Required experiment completion matrix

`../governance/resume-status.json` is the current package ledger. R2-00 retained baseline evidence remains valid; R2-01 candidate arithmetic executed; R2-02 full hash parity/cost retry is running; R2-03/R2-04 geometries and mutations executed, distributions/EVM arithmetic remain; R2-05 is explicitly deferred; R2-06 native anchors executed and EVM fitting remains; R2-07 native/repair controls executed and standalone Solidity control remains; R2-08 source preparation was interrupted; R2-09 eligible branch execution remains; R2-10 synthesis continues. None of these labels means external acceptance.

## 3. Provenance and reproduction

The retained checkpoint validation passed for3137 evidence files,20 findings,11 baseline proof records,3 AIR proof records and7 reconciled receipts before changes. Original halt files and manifest are archived in `../governance/halt-bc71758/`. Original pre-R2 evidence is unchanged. Run commands and source epochs remain attached to their actual attempts, not retroactively replaced with newer source hashes. `../governance/resume-node-provenance.json` records fresh loopback Osaka/Prague chains; halted state was not restored. Foundry runs use isolated `/tmp` roots; no `.env` was read or sourced.

## 4. Baseline distribution and byte ledger

The original60 records remain historical. The halt retained one control plus10 fresh native/codec/Foundry proofs. The newly executed same-codec exporter verified canonical decoding and postcard roundtrip for fresh-06: `../operations/outputs/resume-c0-postcard/`. The distribution adapter also generated and exported a fresh matched case0 proof at `../models/outputs/resume-c0-distribution-smoke-01/`. These are not a30-sample distribution. Canonical A/B, research C10 and postcard codecs remain distinct.

## 5. Baseline gas and deployment

Retained capped Osaka CREATE gas: AIR3,906,341; query verifier2,859,327; registry2,894,140; original pool failed at16,777,216. Retained capped A failed with inner out-of-gas, receipt16,425,128. Separate high-gas Prague A/B controls used16,761,123/13,965,052; these do not establish capped feasibility. `GAS_LEDGER.csv` retains nonoverlapping receipt reconciliation and explicit residuals. New hash-deposit envelopes are not this frozen pool.

## 6. Security-model results

Three calculators processed C0/C1/C2/C3 shapes:83,304 term rows and72 pinned native rows at `../security/outputs/resume-shapes-02/`. First attempt failed because observed commitments use numeric IDs whereas the adapter compared names; the repair matched the actual inventory, and changed-width regression checks reject mismatches. C0 q111/b3 and C2 q101/b4 reach the declared100-bit no-additional-Johnson arithmetic target. C1/C3 and all conditional-Johnson profiles do not reach that target in the declared sweep. This is conditional arithmetic, not system security. The210/330/524 theorem-object distinction, QROM, lifetime, MMCS and hiding composition remain open.

## 7. Exact hash modes and structural review

Complete H5 role semantics remain source-pinned and unqualified. Constants comparison and Solidity compilation executed during resume-full-02 after correcting generated Yul parameter shadowing. Full shared-vector/misuse execution is now attempted before expensive diagnostic constructor tracing. Applicable attacks with unknown cost remain unknown; no full-round break is claimed.

## 8. Matched implementation-tier results

Five H0/H5 tiers compiled and local deployments/capped constructor-deposit attempts are retained in `../hash/outputs/resume-full-02/`. That run stopped when a full diagnostic constructor trace disconnected. The receipt remains measured; missing attribution is unknown. `resume-full-03` continues full parity and matched measurements with a bounded trace-repair attempt. Limited traces, if returned, cannot establish full opcode attribution. Native, internal, estimated and transaction gas remain separate.

## 9. Causal AIR comparison

All seven matched case0 controls verified: C1 decomposed322131bytes, whole-round331773, lanes4373415; C2 horizontal177444; C3 decomposed284455, whole-round302271, lanes4342341. These are single postcard observations, not final statistical rankings. The decomposed controls remain the primary bounded comparison because they used fewer bytes and less proving time in these observations. H5 includes22 private-relation and13 additional public-role permutations; it is not merely H0 with a different compressor.

C1/C2/C3 each generated three actual invalid-trace proofs and rejected them natively; all64/173/173 public-value mutations and configuration substitutions were rejected. Direct AIR mutations and public-context study are retained under `../air/outputs/resume-*`. Warmed fixed/varied distributions and EVM arithmetic are next.

## 10. Transcript, codec, and verifier integration

R2-05 remains explicitly deferred by user. Its source/q32 build is not a completed changed-transcript proof or local-EVM experiment. New splits and lifecycle checks that depend on it remain deferred. Native AIR configuration binding and existing frozen transcript controls do not restart that domain.

## 11. Calibrated FRI/Pareto analysis

First C0 anchor plus remaining grid produced20 distinct verified proofs; C1/C2/C3 grid produced18/20/18 more. All76 accepted anchor rows have zero structural byte residual. The first AIR grid attempt generated a valid native proof but its old model rejected it: BabyBear Montgomery binary serde uses fixed four-byte little-endian fields, not varints. The corrected typed postcard re-encoder exactly matches native bytes; its regression rejects changed wire bytes. No cryptographic failure is inferred from the old model error.

Two observations per parameter point are anchors, not distributions. Unreachable normalized slots remain blocked; fixed controls are never relabeled normalized. EVM fitting, separated frontiers and the field-entry assessment remain in progress. Complete gas stays null/UNKNOWN.

## 12. Same-relation alternative backend

At32, the original non-hiding H0 control generated a proof but returned `Zerocheck(FinalSumMismatch)`. The bounded repair removed the univariate degree7 hint from a backend-local wrapper, allowing pinned multilinear zerocheck to derive degree8 without changing H0 constraints. The repaired serialized proof verified:34,290bytes,79.323667ms prove,6.765125ms verify, one observation. Scope/root/nullifier/payout, opening and truncation mutations rejected. Evidence: `../backend/outputs/resume-h0-degree-32/`.

Two exact-trace hiding PCS openings verified and revealed the eight requested synthetic secret limbs by construction. This is not a break of the PCS hiding guarantee; it demonstrates why that repair is not a complete hiding outer relation proof. Exact128 zero-PoW requests failed with required35/native and41/hiding PoW bits. No guessed replacement preset or global128-bit impossibility claim. Full hiding outer zerocheck and prescribed-point adapter remain missing; licenses are declarations, not legal clearance.

## 13. Complete local operational results

No new complete operational pipeline is claimed. The operational source-preparation worker ended with provider `cyber_policy` error; it did not finish its handoff or execute the new constructor/deposit/payout/100-proof campaign. `../operations/RESUME_INCOMPLETE.json` preserves that state. This interruption is neither an EVM failure nor a cryptographic result. Independent avenues continue.

## 14. State, privacy, and availability

The halt's two valid controls, seven wire mutations, ten constructed mutations and recovery checks remain measured; no natural panic was observed. The4096-deposit native history and279 withdrawal cases are synthetic regenerators, not4096 mined deposits. New checkpoint expiry/replacement/censorship and payout rollback remain unexecuted. Part A is not an ownership proof.

## 15. Conditional branches

Source-pinned gate inputs and exact native-payload transport commands are prepared under `../conditional/`. Portable proof measurements remain to run; commodity x86 availability remains an external prerequisite. Recursion/aggregation/STIR/Circle require actual compatible proof paths and exact composition prerequisites, not a metadata promotion.

## 16. Negative results and rejected hypotheses

Retain original capped constructor/A failures; numeric security adapter mismatch and repair; all-varint postcard model falsification and typed repair; generated Yul shadowing and compilation repair; diagnostic hash trace disconnect and bounded trace retry; non-hiding WHIR degree-hint mismatch and successful bounded repair;128 zero-PoW derivation failures; operational provider interruption. Each has its own scope. None rejects all architectural alternatives.

## 17. Remaining questions

`UNRESOLVED_QUESTIONS.md`, `FINDINGS.json` and package resume status retain owners and decisive experiments. All20 original finding identities remain intact. Further reviews do not gate authorized experiments.

## 18. Proposed next action

Complete the current serial hash run, causal distributions, AIR EVM arithmetic, held-out component gas fit, standalone backend harness and eligible conditional experiments. Keep R2-05 deferred and R2-08 interrupted rather than silently claiming completion. Then publish explicit criterion dispositions and an evidence-based return decision.

## 19. Evidence validation record

`validate_checkpoint.py` verifies artifact hashes, original findings, byte ledgers, accepted anchor identities and null complete-gas semantics. It does not rerun proofs or qualify security. Large new raw traces/tables are losslessly compressed with original and compressed hashes in `../governance/resume-lossless-compression-01.json`; decompression restores historical artifact-ledger bytes exactly. Active outputs are excluded from a progress freeze until their commands finish.
