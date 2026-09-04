# C70 — Historical Flock Keccak and VEIL controls

Flock is `STOP`: it is non-ZK, has no EVM verifier, and current Flock removed Keccak. VEIL over Flock is `DEFERRED` because its concrete PoC adapter does not match Flock's field, PCS, or transcript. Nothing in this package is PQTC and no custom integration is included.

## Exact source check

```sh
python3 research/candidates/C70-flock-veil/run.py source-check \
  --workspace /absolute/path/c70-work --output /absolute/path/c70-source-check
```

This checks exact source bytes at:

- Flock release `43f0eee06d887d87ad25d72614cbc2b17fe91430`;
- historical Keccak parent `c2d0c2485a54f7b7694e19f4f59730ffde3405cf`;
- Keccak removal `0f0d63268e1373c585251e95152b3a6943e2d818`;
- SP1/VEIL `6d7ee5c091ad19e957a5faa5869de8739a76aa78`.

It asserts that the four retired Keccak encoder/bench paths are absent at the removal commit, that no Solidity/Yul/EVM path exists, and that the frozen paper record says Flock is not zero knowledge. At the historical parent it also verifies that the Ligerito registry starts at `m=22` and that `m21_fast.toml` is absent. It checks the VEIL `KoalaBearDegree4Duplex` stacked-PCS adapter against Flock's binary-field Ligerito description.

## Exact historical benchmark attempt — known failure

```sh
python3 research/candidates/C70-flock-veil/run.py flock-benchmark \
  --workspace /absolute/path/c70-work --output /absolute/path/c70-flock-44
```

The runner checks out the historical parent and executes exactly the failing upstream entrypoint:

```sh
KECCAK3_KS=44 cargo bench --bench keccak3_proof
```

The exact pinned attempt compiled and then panicked before measurement: `KECCAK3_KS=44` selects `(m=21, profile=fast)`, but no matching embedded security config exists. The registry starts at `m=22`; adding `m21_fast.toml`, registering it, or passing an ad-hoc configuration would patch the pinned source/parameters and is prohibited. The disposition is `UNEXECUTABLE_AT_PIN/FAIL`; there is no upstream or successful local batch-44 number.

The unchanged negative evidence is retained in `outputs/flock-benchmark/`: `result.json` records `execution_status=FAILED` and exit code 101, while `stderr.log` contains the exact panic. Hashes are recorded in `negative-results.json`.

The source-derived capacity record is `batch-capacity.json`: 44 requested permutations form 15 three-wide blocks, rounded to 16 blocks and capacity 48, with four valid all-zero dummy permutations. These are harness allocation semantics only, not a successful measurement. Every number in that record carries the package-wide `UPSTREAM_BASELINE_NOT_PQTC` classification.

## VEIL PoC controls

The exact upstream PoC commands are available without any Flock adapter:

```sh
python3 research/candidates/C70-flock-veil/run.py veil-poc --example root \
  --workspace /absolute/path/c70-work --output /absolute/path/c70-veil-root
python3 research/candidates/C70-flock-veil/run.py veil-poc --example mle_eval \
  --workspace /absolute/path/c70-work --output /absolute/path/c70-veil-mle
python3 research/candidates/C70-flock-veil/run.py veil-poc --example zerocheck \
  --workspace /absolute/path/c70-work --output /absolute/path/c70-veil-zerocheck
```

These execute `cargo run --release -p slop-veil --example <name>` and label results `EXPERIMENTAL_UPSTREAM_POC_NOT_PQTC`. All three retained PoC runs completed successfully and are stored under `outputs/veil-root/`, `outputs/veil-mle/`, and `outputs/veil-zerocheck/`. These are `PASS` results only for the experimental upstream PoCs; they do not integrate Flock and VEIL remains `DEFERRED`.

Each action writes `result.json`; command actions retain hashed stdout/stderr logs. Validate with `result.schema.json`.
