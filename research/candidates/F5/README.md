# F5: BN254 scalar field / degree 1

Status: **BENCHMARK_ONLY**. Challenge field: `none (base-field challenge)`.

This package contains the candidate manifest, decision record, assumptions, negative results, pinned-source hashes, and deterministic vectors. Shared executable Rust and Solidity kernels live in `../field-bakeoff-common/`. Run commands are recorded in `manifest.json`. Encoding and 64/96 opened-row floors are generated in `../field-bakeoff-common/outputs/projection-latest.json`.

MEDIUM_FIELD_LOW_STACK: pinned scalar arithmetic exists; no frozen PQTornado application permutation, PCS, Solidity codec, or complete proof uses this field.

No complete proof, production compatibility, deployment readiness, or Pareto victory is asserted.
