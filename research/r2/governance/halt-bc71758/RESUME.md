# R2 research resume checkpoint

**Status: paused by user on 2026-09-05. Do not restart experiments without a request to resume.**
This is a halt checkpoint, not a completed research return or a production-readiness decision.

## Read first

1. `governance/resume-status.json`: authoritative package-by-package execution state.
2. `final/TARGETED_RESEARCH_REPORT.md`: partial return using all19 template sections.
3. `final/FINDINGS.json` and `final/UNRESOLVED_QUESTIONS.md`: corrections and open work.
4. `../../pqtc-independent-review/FOLLOW_UP_RESEARCH_PLAN.md`: the complete remaining acceptance criteria. All R2-00 through R2-10 requirements remain tracked; the halt does not silently remove any.
5. `final/RUN_MANIFEST.json`, `final/EVIDENCE_MANIFEST.json`, and `final/REPRODUCTION.md`: evidence, hashes and command provenance.

The user deferred further security reviews, then explicitly requested documenting the current transcript/local-EVM domain incomplete and moving to **R2-06**, then halted all research. Resume R2-06 first. Do not make cryptographic-review approval an execution gate. There is no global quota. Fixed experiment grids and per-command timeouts are experimental controls, not a global research budget.

## What actually ran

- R2-00: clean public-pin checkout, all five metadata checks, clean Rust/Foundry builds, one retained and ten fresh native/codec/Foundry proof checks. Five fresh fixed-witness and five varied-witness proofs; distinct proof identities.
- Signed capped Osaka CREATEs: AIR3,906,341gas; query verifier2,859,327; registry2,894,140; original pool constructor failed at16,777,216gas. This is a measured original-constructor limit, not a limit on all future pool designs.
- Retained baseline A failed inside a verifier call under the actual cap, using16,425,128gas. The separate high-gas Prague control completed A/B at16,761,123/13,965,052gas. A receipt below the cap in a high-gas run does not establish that submission with that cap succeeds; the capped call trace records an inner out-of-gas.
- C1 decomposed H0: one verified native hiding proof,316,794postcard bytes;2,833.1275ms prove;3.743166ms verify;468,205,568bytes RSS.
- C2 complete horizontal H5: one verified native hiding proof,171,691postcard bytes;236.829417ms prove;30.297125ms verify;20,250,624bytes RSS.
- C3 decomposed H5: one verified native hiding proof,287,584postcard bytes;1,760.42675ms prove;3.77425ms verify;290,848,768bytes RSS. C2/C3 use the same H5 case.
- These are single observations, not warmed distributions or a final winner. C0 canonical two-part bytes are not comparable directly to C1/C2/C3 postcard bytes. H5 also proves13 additional public-role permutations; preserve that causal caveat.
- C0 security arithmetic, exact hiding PCS API compile barriers, corrected model checks/historical byte residuals, exact retained L2 envelopes, a64-commit local Flock search, and hardware inventory executed.
- Native availability: two valid controls accepted; seven serialized mutations and ten constructed in-memory mutations rejected. No natural panic occurred. The tests do not prove global panic-freedom or a Solidity bypass.
- Corpus:256 exact H0 mappings plus a complete4096-deposit native history and279 deposit-backed withdrawal cases. The first eight match an independently constructed full-tree control. These are public synthetic fixtures, not4096 mined deposits.

## First executable continuation: R2-06

Run from the repository root, after explicit authorization to resume:

```sh
python3 research/r2/final/validate_checkpoint.py
python3 research/r2/execute.py --output research/r2/models/runs/resume-anchor-01 --env RAYON_NUM_THREADS=1 -- python3 research/r2/models/run.py --plan research/r2/models/anchor-plan.json --relations C0 --anchor fixed-b4-q32 --c0-binary research/r2/models/target/release/pqtc-r2-model-anchors --input research/r2/corpus/h0/fixed --output research/r2/models/outputs/resume-c0-first-anchor
```

**That anchor was not executed before the halt.** The explicit `--c0-binary` is necessary: the runner default points to `models/rust/target`, but Main built into `models/target`.

If binaries are absent, rebuild first; a fresh checkout intentionally excludes build products:

```sh
python3 research/r2/execute.py --output research/r2/models/runs/resume-build-01 --env CARGO_TARGET_DIR=research/r2/models/target --env CARGO_BUILD_JOBS=4 -- cargo build --release --locked --manifest-path research/r2/models/rust/Cargo.toml
```

Use fresh output directories for every attempt. Run only one timed prover process at a time; keep builds and EVM workloads outside timing windows. The predeclared grid permits at most12 distinct initial configurations per selected relation; it is not permission to duplicate two observations into a30-run distribution.

Next, feed explicit measured ledgers to the model and run the current security shape adapter in a **new** output directory with `--shapes` for C1/C2/C3. Existing C0 normalization results are at `research/r2/security/outputs/c0/normalized-profiles.json`, not the worker handoff's shorter default path. Do not label a profile normalized merely because a target was requested.

## Same-codec C0 control still needed

The export option was implemented and compiled, but not executed. It verifies the decoded canonical proof and a postcard roundtrip before export:

```sh
python3 research/r2/execute.py --output research/r2/operations/runs/resume-postcard-c0-01 -- research/r2/operations/target/release/verify-worker --statement research/r2/baseline/outputs/r2-main/proofs/fresh-06/statement.json --parameter 35adfcc070249bb0393c2fd45f0bbd48ef03cbfc08070d03335eaf952975e62ab7bc82ead4f8c1f1c39b3372be85195853134dfc9d24f43b97a5e0454ea07779 --part-a research/r2/baseline/outputs/r2-main/proofs/fresh-06/part-a.pqtc --part-b research/r2/baseline/outputs/r2-main/proofs/fresh-06/part-b.pqtc --export-dir research/r2/operations/outputs/resume-c0-postcard
```

C1's first run used the legacy `swc-v1-000` mapped input paths. Future causal runs should use the frozen R2 H0 paths explicitly and verify the input identity. C2/C3 already used those paths. See `air/experiment.json` for remaining geometries, mutations, public-context study and cost commands.

## Next backend avenue

Both API barriers and both native binaries exist. The actual non-hiding H0 control and hiding trace-opening repair have **not** run:

```sh
python3 research/r2/execute.py --output research/r2/backend/runs/resume-h0-32 --env RAYON_NUM_THREADS=1 -- python3 research/r2/backend/run.py --security-level 32 --output research/r2/backend/outputs/resume-h0-32
```

Then attempt128 using a new output directory. The non-hiding control and exposed evaluation repair are not a complete hiding withdrawal proof. Retain actual results rather than converting a missing interface into a security or architectural rejection. `backend/commands.json` also contains the standalone Solidity harness repair.

## Deferred domains and known engineering fixes

- `transcript/INCOMPLETE.json`: R2-05 deferred by user. q32 Rust compiled; q48 source generated; neither complete transcript experiment executed. Do not implicitly restart it while working on models.
- H5 full-role Rust/TypeScript/Solidity parity, constants parity and matched gas measurements remain unexecuted. `hash/execution.json` contains commands. Rust compiled only.
- C1's first compilation needed an explicit `&BabyBear` coefficient type. Fixed.
- C2 initially stalled before proof generation in the symbolic AIR-to-EVM exporter. Shared `Arc` DAGs were recursively expanded. Pointer memoization now makes compilation/evaluation visit each DAG node once; the C2 retry completed and verified. Keep the interrupted directory; it is not a failed cryptographic proof.
- Original local CREATE signing used flags after `cast mktx --create`, causing a CLI parse error. Fixed by putting common flags before the CREATE subcommand. `--local-id` now preserves separate attempts without overwriting a fixture.
- Opcode traces are gzip-compressed and their readers updated. No raw trace information was discarded.
- Rust LSP was unavailable: toolchain1.97.0 did not contain `rust-analyzer`. This did not prevent successful builds.
- `operations/make_pool.py` and `operations/solidity/PayoutReceiver.sol` have not been exercised or Solidity-compiled. They must not be called verified pool implementations.
- BabyBear degree8 challenge extensions exist in the pinned upstream source, but no alternate-extension experiment was implemented or run. Enter at most one such branch only after the plan's measured bottleneck condition.

## Local state and runtime restoration

Both managed nodes were explicitly stopped, exit0; no background research job remains. Their chain state was not persisted. Do not reuse old deployment addresses against a newly started node without replaying the runner.

Use the harness process manager for nodes, not a shell background process. The observed working launch specs were:

```text
pqtc-r2-osaka:
  anvil --host 127.0.0.1 --port 18545 --chain-id 31337 --hardfork osaka --enable-tx-gas-limit --gas-limit 16777216 --steps-tracing --balance 100000 --silent
pqtc-r2-prague-diagnostic:
  anvil --host 127.0.0.1 --port 18546 --chain-id 31337 --hardfork prague --gas-limit 1000000000 --steps-tracing --balance 100000 --silent
```

Use `detached:true` if the same harness teardown problem recurs, then explicitly stop both nodes when finished. Earlier ordinary and `persist:true` services unexpectedly exited137 in pairs; the cause was not established. Detached services survived the successful170-second baseline local run. Keep diagnostic Prague receipts separate from capped Osaka feasibility.

Never read/source `.env`. Foundry may discover dotenv files even after environment sanitization: all Foundry/cast work must use the isolated `/tmp` projects without dotenv ancestry. Use only public local development keys and disposable balances. No public-chain deployment occurred.

The existing clean/instrumented baseline workspace is `/tmp/pqtc-r2-baseline-r2-main-18olw4dw`, recorded in `baseline/outputs/r2-main/workspaces.json`. It may disappear after reboot. Its compiler JSON artifacts are archived in the checkpoint; Rust targets and disposable checkouts are not committed. If the workspace is absent, run baseline `prepare` with a **new** run ID. The committed R2 corpus already exists; do not rerun the write-once `prepare-corpus` against it blindly. Reuse or deliberately regenerate to a new location after preserving the original.

## Publication and source epochs

Prior public progress: `d273f5a` and `3242e02`; public review pin:`e51a5c5ccc4f50e0beb07cdf04d7f8dd258c7997`. The halt checkpoint is the commit containing this file and its evidence manifest. Original pre-R2 research remains unchanged.

The executed C0 security `run.py` version is preserved at commit3242e02. The current source later gained repeated `--shapes` support without a new analysis run. Its changed source hash must not be retroactively attached to the old C0 observation. The first native containment run likewise predates the optional postcard exporter. Historical run/binary hashes remain historical, not promises of current binary identity.

Before a future final return: finish or explicitly disposition every package, update all20 findings, execute the missing validations, establish properly separated distributions/ledgers, and then make the plan's final decision. This pause checkpoint does not select an engineering specification.
