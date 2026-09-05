# R2 resumed research return

**Status: RESEARCH_RETURN_WITH_DISPOSITIONS. No experiments running.**
This is an explicitly incomplete return, not full plan acceptance, cryptographic qualification or production readiness.

## Read first

1. `governance/resume-status.json`: authoritative package-by-package state.
2. `final/TARGETED_RESEARCH_REPORT.md` and `final/DECISION.md`: measured results and withheld final selection.
3. `final/ACCEPTANCE_DISPOSITIONS.json`: all124 normative headings and their requirements, with explicit incomplete scope.
4. `final/UNRESOLVED_QUESTIONS.md`, `final/FINDINGS.json`, `final/OPPORTUNITY_MATRIX.csv`.
5. `../../pqtc-independent-review/FOLLOW_UP_RESEARCH_PLAN.md`: requirements are unchanged, not waived by the return.
6. `final/REPRODUCTION.md`, `final/RUN_MANIFEST.json`, `final/EVIDENCE_MANIFEST.json`.

Run retained-record validation before changes:

```sh
python3 research/r2/final/validate_checkpoint.py
```

## What executed after bc71758

-76 verified parameter-anchor proofs; typed codec models have zero residual.
-240 measured causal proofs: C0/C1/C2/C3,30 fixed and30 varied each;16 excluded warmups,256 unique hashes.
-23322 shared full-role parity cases and51 actual misuse cases; five H0/H5 tiers and50 benchmark rows; source-matched parity reuse is explicit.
-Seven bounded geometry controls, native mutation campaigns and public-context study; all seven Solidity arithmetic diagnostics passed parity. Capped arithmetic attempts returned out-of-gas, not full-verifier failure.
-36 component gas rows on18 fixed-profile proofs with whole held-out b4/q48; exact complete verifier gas remains unknown.
-Exact non-hiding H0 WHIR proof verified after degree-hint repair; opening-only hiding control is not a private withdrawal. The standalone Solidity control hit31856-byte code size against24576.
-Conditional gates, exact native transport and64 portable ARM proofs executed. Commodity x86 is unavailable.

## Deliberately incomplete domains

R2-05 remains **explicitly deferred by user**. Do not restart changed-transcript/local-EVM work automatically.
R2-08 source preparation ended with a provider interruption. `operations/RESUME_INCOMPLETE.json` is the entrypoint for that domain; its missing operational campaign is not a measured failure.
Independent reviews remain separately deferred and are not permission gates for local measurement.
No final architecture category was selected: none has its required evidence. There is more than one missing technical result, so a claim that only a small spike remains would be false.

## Runtime safety and restart

Both disposable Anvil nodes were stopped after final experiments. Chain state was not persisted. Historical addresses must not be reused. Node exit137 events have no established cause; successful final cost runs used fresh nodes without optional `--steps-tracing`. Traces from interrupted attempts remain partial.
Use isolated `/tmp` Foundry workspaces, public development keys and disposable balances only. Never read/source `.env`, use funded wallets or broadcast to public networks. Run timed workloads serially.

## Reproduction sources

The previous halt instructions and original validator are in `governance/halt-bc71758/`. The first resumed progress checkpoint is `a1495e7646cb716093d77b7df4253591bfde6133`.
Exact successful commands: `governance/resume-final-experiments.json`, `governance/resume-experiment-suite-02.json`, and per-domain `runs/**/command.json`.
All commands require **new output directories**. Copy a manifest and replace output destinations before replay; do not overwrite retained evidence. Rebuild excluded targets first. In particular, use the explicit C0 binary path `research/r2/models/target/release/pqtc-r2-model-anchors`; the runner default points elsewhere.
For old commands, preserve their original source epochs rather than attaching current source hashes retroactively. Fresh OS entropy means new proofs need not have historical proof hashes.

## Next action

Use the unresolved-question owner and smallest decisive experiment, not a new broad plan. Reopen the interrupted operational domain when its source preparation can proceed; leave R2-05 deferred until explicit instruction. New evidence can change the current dispositions. No security or deployment approval is implied.
