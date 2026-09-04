# ADR — Reproduce frozen v0.3 as C00

## Hypothesis

The frozen v0.3 source and generated identity can be reproduced without changing protocol code, and fresh q32 hiding proofs can establish a baseline distribution for later candidates.

## Exact construction

C00 imports the frozen Rust crates by path and calls their public production APIs. It fixes profile `sepolia-v0.3`, parameter ID `0x35ad…7779`, 256×190 AIR, 1,186 constraints, degree seven, q32 hiding two-adic FRI, four masking codewords, and eight MMCS salt fields. Each proof is created in an independent process with OS entropy and natively verified before and after A/B encoding. Candidate corpus bytes are mapped with the domain-separated rejection sampler documented in the README and retained per case.

The EVM harness compiles the frozen contracts in a nested Foundry root. A research-only subclass installs a synthetic scope/root at a fixed address, then exact retained calldata invokes the unchanged full pool `beginWithdrawal` and `withdraw` entry points. This state fixture is not protocol code and cannot support a deployment claim.

## Assumptions

The frozen source implements the report's intended relation; the pinned toolchains and Plonky3 commit have the stated semantics; OS entropy is available; Keccak behaves as an XOF-like rejection-sampling derivation for this deterministic corpus mapping; and Foundry's local execution models Prague as configured. Cryptographic assumptions and qualification gaps are enumerated in `assumptions.md` and are not upgraded by benchmark success.

## Alternatives considered

- Editing the frozen CLI to expose metrics: rejected because SP-00 freezes v0.3 source.
- Modulo reduction of corpus seeds: rejected because it is biased and violates the common-corpus contract.
- Claiming report fixture gas for fresh proofs: rejected because query collisions/frontiers vary.
- Mocking the verifier or payout: rejected; the harness executes the complete frozen registry and pool calls.
- Requiring corpus roots to arise from a full deposit history: deferred because arbitrary synthetic sibling paths cannot generally be recreated by append-only deposits; the research loader makes this limitation visible.

## Measurements

Sixty fresh q32 proofs were generated and verified natively; all 60 exact calldata pairs passed the complete Foundry pool-facing A/B simulation. Part-A total gas ranges 16,179,681–16,953,270 with p50 16,664,641.5; part B ranges 13,333,063–14,264,492 with p50 13,959,759.5. Nine part-A samples exceed 16,777,216; no part-B sample does.

Against the report, p50 deltas are 0.561% (A execution), 0.758% (A total), -0.689% (B execution), and -1.036% (B total). The B-total delta exceeds 1%. The exact cause is not isolated: fresh query/calldata variation and current harness/compiler instrumentation both differ from the single report fixture, so no stronger attribution is made. Reproduced deposit execution gas is exactly 13,991,021, matching the report.

Deployment profiling establishes EIP-170/EIP-3860 code-size passes. Pool internal `new` gas is 18,873,630, above 2^24; exact top-level creation transaction gas remains NOT_EVALUATED. Raw opcode status is PASS_T8N_SIMULATION; second-client status is PASS_T8N_SIMULATION_NOT_MINED. Any t8n receipt is explicitly a simulation, not mined evidence.

## Gate result

`FAIL`. Native, deposit, and Foundry correctness passed, but 9/60 observed valid part-A transactions exceed EIP-7825. Missing top-level creation and mined-receipt evidence remain visible and cannot convert an observed cap failure into PASS.

## Decision and compatibility

Accept C00 as the immutable comparison definition, not as a deployable candidate. It intentionally preserves all v0.3 protocol incompatibilities and introduces no alias, fallback, codec, or custody change. Generated research fixtures are incompatible with production use.

## Review still required

Independent AIR/verifier review, P2BB512 structural analysis, a complete QROM treatment, a full hiding/ZK analysis, multi-target security accounting, maximum valid frontier/gas analysis, abandoned-checkpoint economics, runtime-hash-bound deployment manifests, a second-client reproduction, and a public-network review remain outstanding.
