# C60 — Plonky3 recursion architecture control

C60 is `DEFERRED`. The only executable positive path is the upstream `recursive_fibonacci --zk` toy architecture smoke at exact commit `34e3a2c3837834a7bf98a0b65063e0180e7fbb7b`. It is **not the frozen v0.3/H0 relation and not PQTC**.

## Exact commands

First verify byte hashes, Plonky3 0.7.0 dependencies, the non-ZK Keccak branch, and the ordinary-WHIR verifier boundary:

```sh
python3 research/candidates/C60-recursion/run.py source-check \
  --workspace /absolute/path/c60-work --output /absolute/path/c60-source-check
```

Run the only permitted architecture smoke:

```sh
python3 research/candidates/C60-recursion/run.py architecture-smoke \
  --workspace /absolute/path/c60-work --output /absolute/path/c60-fibonacci
```

The runner executes exactly:

```sh
cargo run --profile optimized --example recursive_fibonacci -- --field baby-bear --hash poseidon1 --n 1000 --num-recursive-layers 5 --zk
```

The result label is `UPSTREAM_ARCHITECTURE_SMOKE_NOT_PQTC`; its relation field is `TOY_FIBONACCI_NOT_PQTC`.

The retained run completed successfully (`execution_status=COMPLETED`, exit code 0) and is stored under `outputs/architecture-smoke/`. This is a `PASS` only for the upstream toy architecture smoke; C60 remains `DEFERRED`.

## Negative control

The pinned upstream negative-control entrypoint is:

```sh
cargo run --profile optimized --example recursive_keccak -- --zk
```

It is intentionally not executed by this package. Source lines in `recursive_keccak.rs` prove that the base layer is non-ZK and that `--zk` has no effect. Running it would only produce non-ZK upstream evidence.

## Deferred gates

- Upstream recursion uses Plonky3 0.7.0; mandated Plonky3 is 0.6.0.
- In-circuit WHIR mirrors ordinary `WhirVerifier`, not `HidingWhirPcs`.
- No exact v0.3/H0 relation, recursion-specific privacy/composition theorem, concrete QROM analysis, or EVM verifier exists here.

Each action writes a machine-readable `result.json`; command actions also retain hashed stdout/stderr logs. Validate against `result.schema.json`. Exact byte hashes are in `source-hashes.json`.
