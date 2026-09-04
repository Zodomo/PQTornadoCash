# T0 — field-by-field v0.3 baseline

Classification: **BENCHMARK_ONLY**. Production-compatible initialization and one K512 absorb per canonical field or commitment.

Normative grammar and dependency graph live in `../../cryptanalysis/transcript/`. Run the complete deterministic focused measurement path from the repository root with:

`python3 research/cryptanalysis/transcript/run-focused.py`

The candidate entry points are `rust/src/lib.rs`, `solidity/Candidate.sol`, and `typescript/index.ts`. `measurements/transcript.json` distinguishes measured standalone fields from the unintegrated full verifier path. `vectors/misuse.json` records actual parser/binding rejection results. The Solidity `TranscriptGasHarness` emits prefix transcript gas, parser gas, calldata bytes, memory high-water bytes, Keccak calls/input bytes, explicit copies, runtime code size, and proof/calldata deltas. Its full-path field is the minimum signed-integer sentinel because these candidates are intentionally not integrated into the frozen verifier path.

Gate result: **REFERENCE_CONTROL**. Retained as the exact comparison control; it is not a new deployment candidate.
