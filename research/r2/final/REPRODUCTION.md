# Reproducing retained R2 evidence

## Offline validation

```sh
python3 research/r2/final/validate_checkpoint.py
```

This checks retained records; it does not rerun experiments. Refresh manifests only after authorized changes, then validate:

```sh
python3 research/r2/final/refresh_evidence.py
python3 research/r2/final/validate_checkpoint.py
```

## Recorded source epochs

| Role | Identity |
|---|---|
| Public review input | e51a5c5ccc4f50e0beb07cdf04d7f8dd258c7997 |
| Halt/resume input | bc7175895ebef241914bb15f2902a55683d5485b |
| First resumed measured checkpoint | a1495e7646cb716093d77b7df4253591bfde6133 |
| This report/evidence freeze | Commit containing this file; obtain with git log |
| Original source/cleanup reproduction | Retained baseline outputs and governance/halt-bc71758 records |

Command records retain compiler versions, environment, binary/source/input hashes, stdout/stderr, exit status and scope. Source-epoch directories accompany hash attempts. Preserve these identities; current source hashes must not be attached to older executions. Missing source qualification is not an experiment failure.

## Rebuild excluded binaries

Run through the scrubbed execution wrapper and use fresh output paths:

```sh
python3 research/r2/execute.py --output research/r2/models/runs/rebuild-new --env CARGO_TARGET_DIR=research/r2/models/target -- cargo build --release --locked --manifest-path research/r2/models/rust/Cargo.toml
python3 research/r2/execute.py --output research/r2/air/runs/rebuild-new --env CARGO_TARGET_DIR=research/r2/air/target -- cargo build --release --locked --manifest-path research/r2/air/rust/Cargo.toml
```

C0 anchor runner requires `--c0-binary research/r2/models/target/release/pqtc-r2-model-anchors`. AIR uses `research/r2/air/target/release/pqtc-r2-air`. Baseline, exporter, hash and portable rebuild commands are retained in their run records and handoff manifests. Rust1.97.0 and local Solc0.8.30 were used; consult exact recorded Foundry pins.

## Experiment recipes

- Parameters: `models/anchor-plan.json`, recorded `models/runs/resume-*` commands, and separated normalized selections.
- Causal distributions: `models/resume-causal-distribution-manifest.json`;30 samples plus2 warmups per fixed/varied stratum.
- Hash parity: `hash/runs/resume-full-03`; successful source-matched cost continuation in `governance/resume-final-experiments/hash-costs-final/command.json`.
- Arithmetic diagnostics: `governance/resume-experiment-suite-02.json` and `air/outputs/resume-diagnostic2-cost-*`.
- Component gas: `models/runs/resume-component-gas-02/command.json`; whole fixed-b4-q48 profile held out.
- Backend: `backend/runs/resume-h0-degree-32`; standalone code-size barrier in `backend/outputs/resume-standalone-solidity-01`.
- Conditional and portable: `conditional/commands.json`, `governance/resume-final-experiments.json`.

Copy manifests and substitute new output directories before replay. Proof entropy is intentionally fresh, so byte-for-byte proof identity is not expected on rerun. Timings are serial independent-process observations. Requested portable thread settings are not measured thread utilization.

## Local chains and traces

Both nodes stopped cleanly after the last runs. State is disposable and was not persisted. Recreate loopback chain31337 only: Osaka with enabled transaction gas cap16777216 on18545; Prague diagnostic gas limit1000000000 on18546. Start outside the repository, without optional step tracing for cost-only runs. Recreate all contracts and deposits; never reuse historical addresses. Full trace attempts and exit137 interruptions are retained separately; their cause is not established.

Foundry projects must be isolated outside repository dotenv ancestry. No `.env` reads, public broadcasts or funded keys. Public Anvil development keys are test data. High-gas diagnostic successes do not establish capped feasibility.

## Tables and limitations

Canonical original byte partitions, native disjoint leaves and unsplit component/receipt records are distinct. `GAS_LEDGER.csv` marks new whole receipts unattributed, rather than fabricating opcode attribution. `SECURITY_TERMS.csv` is the full retained83304-row term table; its conditions are not accepted theorems. `ACCEPTANCE_DISPOSITIONS.json` preserves the normative requirement text, not a blanket pass.

Oversized RPC logs and traces are stored losslessly. `../governance/resume-lossless-compression-01.json` and `resume-lossless-compression-02.json` retain original and compressed paths, sizes and hashes. Decompress with Python's `gzip` module to recover original artifact-ledger bytes; do not replace historical hashes with compressed-file hashes. The final validator verifies decompression of the RPC log that exceeded GitHub's file limit.

R2-05 remains user-deferred. R2-08 is interrupted. Their absence must remain visible during reproduction. Further independent reviews remain separate from measurement permission.
