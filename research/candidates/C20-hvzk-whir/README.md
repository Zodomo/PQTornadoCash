# C20 — pinned HVZK-WHIR native smoke

This package reproduces the complete upstream Plonky3 `HidingWhirPcs` commit/open/verify lifecycle at commit `3152b14a89067c83775a8076cc262ffc48a1fd7c`. It uses stable public polynomial data and points while creating a fresh OS-seeded `StdRng` through the compiled `CryptoRng`-bounded API for each proof. Both proofs must verify and must have different serialized hashes.

Run from the repository root:

```sh
./research/candidates/C20-hvzk-whir/run-focused.sh
```

Pass an optional result path as the first argument. The default retained output is `outputs/latest.json`. The runner clones the exact source into a clean temporary directory, verifies the commit and recorded SHA-256 hashes, copies the adapter into that checkout, builds into a separate clean temporary target, validates the JSON, then retains only the result.

The output includes proof payload bytes, single-run prover/native-verifier wall times, process peak RSS, and the upstream hiding base-case security report. These are all labeled **`UPSTREAM_BASELINE_NOT_PQTC`**. They are not timing benchmarks, ABI calldata, security qualification, or PQTC measurements.

## Frozen relation map

The only faithful relation control is frozen v0.3/H0: fixed-denomination one-note withdrawal; binary depth-20 P2BB512-v1 tree; 16 BabyBear-element digest; 256×190 AIR; 1,186 constraints; maximum degree seven; and a statement binding scope, root, nullifier, recipient, relayer, and fee. The deterministic 4,096-element public polynomial proxy implements none of that relation and does not consume the common corpus.

C20 integration is `DEFERRED`: SP-02 panic containment fails, SP-10 has no accepted relation, and a matching EVM verifier, exact-transcript QROM argument, and external review are absent. See `manifest.json`, `ADR.md`, `assumptions.md`, `status.json`, `source-hashes.json`, `negative-results.json`, and `result.schema.json`.
