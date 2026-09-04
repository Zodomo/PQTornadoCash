# ADR — Defer the Plonky3 recursion path

Research cutoff: **2026-09-04**.

## Decision

Keep C60 `DEFERRED`. Permit exactly one positive reproduction: the pinned `recursive_fibonacci` example with `--zk`, labeled as an upstream full-ZK recursion architecture smoke and **not PQTC**. Do not treat `recursive_keccak --zk` as hiding evidence and do not port or integrate the recursion tree.

## Source-controlled reasons

At commit `34e3a2c3837834a7bf98a0b65063e0180e7fbb7b`:

- `Cargo.toml` pins Plonky3 crates, including `p3-whir`, to 0.7.0. The mandated backend pin is Plonky3 0.6.0 at `3152b14a89067c83775a8076cc262ffc48a1fd7c`; direct dependency compatibility therefore fails.
- `recursive_keccak.rs` states that the base proof always uses non-ZK `p3-uni-stark`, all recursive layers use non-ZK configuration, and `--zk` has no effect for this example.
- The in-circuit WHIR verifier mirrors ordinary `WhirVerifier::verify`, not the full PCS adapter or `HidingWhirPcs`; adapter transcript work remains caller-owned.
- No EVM verifier or measured gas/calldata path exists.

## Evidence boundary

A successful Fibonacci run proves only that the upstream toy example can exercise its advertised ZK recursive architecture. Fibonacci is not the frozen v0.3/H0 relation. It must carry `UPSTREAM_ARCHITECTURE_SMOKE_NOT_PQTC`; no toy-Fibonacci output may be labeled PQTC.

No new hiding construction, cross-version port, transcript theorem, recursion-composition theorem, or EVM verifier is authorized by this package.
