# ADR — Stop Flock and defer VEIL over Flock

Research cutoff: **2026-09-04**.

## Decision

Set Flock to `STOP` as a PQTC privacy finalist. Retain the exact historical `KECCAK3_KS=44` attempt as failed `UPSTREAM_BASELINE_NOT_PQTC` evidence with disposition `UNEXECUTABLE_AT_PIN`; do not patch its configuration. Set VEIL over Flock to `DEFERRED`; do not create a custom adapter or integration.

## Flock findings

The Flock paper states that its implementation provides succinctness, not zero knowledge. The official source tree has no Solidity, Yul, or EVM verifier. Commit `0f0d63268e1373c585251e95152b3a6943e2d818` removed both Keccak encoders, all Keccak benches, and their only consumers. Therefore the Keccak3 harness is reproducible only at its historical parent `c2d0c2485a54f7b7694e19f4f59730ffde3405cf`.

For `KECCAK3_KS=44`, the three-wide harness needs $\lceil44/3\rceil=15$ blocks, rounds to 16 slots, and allocates capacity 48. Four slots are valid all-zero Keccak permutations. These are source-derived harness semantics, not a published or locally completed batch-44 measurement and not PQTC.

The exact pinned command compiled, then panicked before measurement: Ligerito requested `(m=21, profile=fast)`, while the embedded configuration registry starts at `m=22` and no `m21_fast.toml` exists. The panic explicitly asks for a new TOML/registry entry or an ad-hoc explicit configuration. Either change would alter the pinned source or parameters, so the benchmark is `UNEXECUTABLE_AT_PIN/FAIL`. The unchanged logs and result are retained in `outputs/flock-benchmark/`.

## VEIL findings

At SP1 commit `6d7ee5c091ad19e957a5faa5869de8739a76aa78`, the experimental and unaudited VEIL PoC instantiates `KoalaBearDegree4Duplex` with a stacked PCS. Flock instead uses Boolean R1CS and Ligerito over a binary field. The binary-field adapter, Flock verifier compiler, transcript binding analysis, soundness analysis, EVM backend, and concrete QROM treatment are missing.

VEIL does not rescue or reopen the stopped Flock route. Its examples may run only as experimental upstream PoC evidence labeled not PQTC.

## Consequences

- Flock: `STOP`.
- Historical batch-44: `UNEXECUTABLE_AT_PIN/FAIL`; non-hiding, no EVM, no benchmark number. Capacity semantics remain `UPSTREAM_BASELINE_NOT_PQTC`.
- VEIL over Flock: `DEFERRED`.
- No privacy finalist and no custom integration.
