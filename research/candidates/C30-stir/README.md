# C30 — pinned STIR non-hiding lower bound

This package runs the exact upstream Plonky3 `TwoAdicStirPcs` commit/open/verify API at commit `3152b14a89067c83775a8076cc262ffc48a1fd7c`. A compiled assertion requires `Pcs::ZK == false`. The public BabyBear/quartic polynomial has 4,096 values, width one, and one opening point, matching C20's polynomial geometry without pretending the two protocols have identical security or overhead.

Run from the repository root:

```sh
./research/candidates/C30-stir/run-focused.sh
```

An optional first argument selects the retained JSON path; the default is `outputs/latest.json`. The runner uses a clean temporary source checkout and target directory, verifies the exact pin and recorded source hashes, executes the adapter, validates its result, and retains only the JSON.

Every result is **`UPSTREAM_BASELINE_NOT_PQTC`** and `BENCHMARK_ONLY`. Proof bytes and single-run time/RSS observations are a non-hiding lower bound, not a privacy-qualified or PQTC measurement.

## Frozen relation map

Frozen v0.3/H0 is the only faithful relation control because no SP-10 compression candidate passed. It requires fixed-denomination withdrawal semantics; a binary depth-20 P2BB512-v1 tree; 16-field application digest; 256×190 AIR with 1,186 constraints and maximum degree seven; and a public statement binding scope, root, nullifier, recipient, relayer, and fee. This smoke implements none of those constraints, bindings, or common-corpus derivations.

See `manifest.json`, `ADR.md`, `assumptions.md`, `status.json`, `source-hashes.json`, `negative-results.json`, and `result.schema.json`.
