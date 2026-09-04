# F2: KoalaBear / degree 5

Status: **BENCHMARK_ONLY**. Challenge field: `x^5 + x^2 - 1`.

This package contains the candidate manifest, decision record, assumptions, negative results, pinned-source hashes, and deterministic vectors. Shared executable Rust and Solidity kernels live in `../field-bakeoff-common/`. Run commands are recorded in `manifest.json`. Encoding and 64/96 opened-row floors are generated in `../field-bakeoff-common/outputs/projection-latest.json`.

MEDIUM: the specialized quintic is implemented and tested upstream, but it is not the frozen PQTornado challenge field and has no EVM integration history here.

No complete proof, production compatibility, deployment readiness, or Pareto victory is asserted.
