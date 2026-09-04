# T3 — challenge-boundary frame

Classification: **BENCHMARK_ONLY**. Typed claims are framed and flushed once immediately before each challenge boundary.

Normative grammar and dependency graph live in `../../cryptanalysis/transcript/`. Run the complete deterministic focused measurement path from the repository root with:

`python3 research/cryptanalysis/transcript/run-focused.py`

The candidate entry points are `rust/src/lib.rs`, `solidity/Candidate.sol`, and `typescript/index.ts`. `measurements/transcript.json` distinguishes measured standalone fields from the unintegrated full verifier path. `vectors/misuse.json` records actual parser/binding rejection results. The Solidity `TranscriptGasHarness` emits prefix transcript gas, parser gas, calldata bytes, memory high-water bytes, Keccak calls/input bytes, explicit copies, runtime code size, and proof/calldata deltas. Its full-path field is the minimum signed-integer sentinel because these candidates are intentionally not integrated into the frozen verifier path.

Gate result: **T3_EXTERNAL_REVIEW_ONLY**. Independent review permits external study only and blocks integration: candidate APIs lack a claim/boundary state machine, mutation/parity evidence is incomplete, and the full-width continuation redesign is not implemented.
