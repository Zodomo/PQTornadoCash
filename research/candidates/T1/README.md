# T1 — typed-array absorb

Classification: **BENCHMARK_ONLY**. One length-and-count-delimited absorb for each logical field array; scalars and commitments remain typed items.

Normative grammar and dependency graph live in `../../cryptanalysis/transcript/`. Run the complete deterministic focused measurement path from the repository root with:

`python3 research/cryptanalysis/transcript/run-focused.py`

The candidate entry points are `rust/src/lib.rs`, `solidity/Candidate.sol`, and `typescript/index.ts`. `measurements/transcript.json` distinguishes measured standalone fields from the unintegrated full verifier path. `vectors/misuse.json` records actual parser/binding rejection results. The Solidity `TranscriptGasHarness` emits prefix transcript gas, parser gas, calldata bytes, memory high-water bytes, Keccak calls/input bytes, explicit copies, runtime code size, and proof/calldata deltas. Its full-path field is the minimum signed-integer sentinel because these candidates are intentionally not integrated into the frozen verifier path.

Gate result: **NOT_SELECTED**. Fewer hash calls than T0, but T3 measures fewer calls while making challenge boundaries explicit.
