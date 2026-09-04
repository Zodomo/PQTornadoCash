# F4: Mersenne31 / degree 4

Status: **BENCHMARK_ONLY**. Challenge field: `i^2 + 1; u^2 - (2+i) (QM31 tower)`.

This package contains the candidate manifest, explicit no-silent-inheritance protocol matrix, decision record, assumptions, negative results, refreshed source/evidence hashes, and deterministic vectors. Shared executable Rust and Solidity kernels live in `../field-bakeoff-common/`. Native timing is `DIAGNOSTIC_NOT_COMMON_PROTOCOL` and cannot rank candidates. Encoding and 64/96 opened-row floors are generated in `../field-bakeoff-common/outputs/projection-latest.json`.

MEDIUM_BACKEND_SPECIFIC: pinned circle, complex DFT, QM31, and Poseidon2 code exist, but the frozen relation and EVM verifier are not circle ports.

No complete proof, production compatibility, deployment readiness, nondominance, or Pareto victory is asserted.
