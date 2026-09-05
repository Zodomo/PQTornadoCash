# Reproducing this halt checkpoint

This checkpoint preserves evidence; it does not complete R2. Do not restart research until requested.

## Validate retained records

From the repository root:

```sh
python3 research/r2/final/validate_checkpoint.py
```

The validator checks the evidence manifest, proof/byte-ledger invariants, gas reconciliation and findings references without proving, starting nodes, contacting an RPC endpoint or signing transactions. `checkpoint-validation.json` is the observed validation result. The validation output and evidence manifest exclude themselves from the hash set to avoid a circular dependency. `RUN_MANIFEST.json` indexes retained command records; interrupted and failed records stay in the index.

## Reproduce experiments only after resumption

`../RESUME.md` gives the exact next R2-06 command, rebuild commands, deferred domains and local-node launch specs. Each retained `command.json` records the actual argument vector and execution result for its attempt. Inspect that attempt's stdout/stderr and package results; command success alone is not proof verification or security qualification.

Use new output directories. Do not overwrite historical runs, write-once corpus inputs or interrupted attempts. Run timed workloads serially and keep builds outside their timing windows. All witnesses in these research artifacts are public synthetic inputs, not funded notes.

## Compiler provenance archive

`../baseline/outputs/r2-main/compiler-artifacts.tar.gz` preserves the instrumented workspace's `contracts/src`, `lib/forge-std/src`, baseline EVM source/tests/configuration, and full Foundry output including AST/source-map/build-info artifacts. Extract it into an empty temporary directory if the original `/tmp` workspace disappears. Archive paths are relative to the original instrumented repository root. Compact Foundry build-info can be resolved against the archived source paths and contract artifacts. This is compiler provenance, not a portable cache of Rust binaries.

The clean source pin and instrumentation are recorded under the baseline output directory. Recreate an absent workspace with the baseline `prepare` phase and a new run ID. Do not blindly repeat the write-once `prepare-corpus` step over the retained corpus.

## Source epochs and limits

The C0 security analysis ran before the later repeated-`--shapes` adapter; its source version is retained at commit `3242e02`. The containment run predates the optional C0 postcard exporter. Run-local hashes describe those historical binaries/sources, not current build products.

The original baseline capped Osaka transactions and separate high-gas Prague controls must remain separate. Nodes were stopped and chain state was not persisted. A new node requires redeployment/replay; old addresses do not establish state on it.

Foundry can discover `.env` files through parent directories. Use isolated temporary projects without dotenv ancestry, sanitized command environments, public local development keys and disposable balances. No public-network deployment is part of this checkpoint or its validation.
