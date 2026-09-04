# C40 — pinned CirclePcs source watch

This package deliberately contains no Circle proof adapter. Its focused command checks a clean checkout of Plonky3 `3152b14a89067c83775a8076cc262ffc48a1fd7c`, verifies the recorded `circle/src/pcs.rs` hash, and confirms that pinned `CirclePcs` requires `ComplexExtendable`, sets `Pcs::ZK = false`, and exposes no `HidingCirclePcs` API.

Run from the repository root:

```sh
./research/candidates/C40-circle/run-focused.sh
```

An optional first argument selects the retained JSON path; the default is `outputs/latest.json`. The runner creates clean temporary source and unused build directories, validates the source-watch JSON, and retains only that JSON. It does not execute or measure a proof.

## No-code boundary

A comparable C20/C30 lower bound would need the same BabyBear/quartic 4,096-element geometry. CirclePcs requires a different `ComplexExtendable` field. Because SP-10 accepted no replacement relation, translating frozen H0 into that field would invent relation glue rather than reproduce a matched lower bound. No ZK wrapper, transcript theorem, or EVM verifier is invented here.

Frozen v0.3/H0 remains the only faithful control: fixed-denomination withdrawal semantics; binary depth-20 P2BB512-v1 tree; 16-field digest; 256×190 AIR with 1,186 degree-at-most-seven constraints; and binding of scope, root, nullifier, recipient, relayer, and fee. This source watch implements none of it.

C40 is `DEFERRED`, is not a privacy finalist, and produces `SOURCE_WATCH_NOT_MEASUREMENT`. See `manifest.json`, `ADR.md`, `assumptions.md`, `status.json`, `source-hashes.json`, `negative-results.json`, and `result.schema.json`.
