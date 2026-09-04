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

No expensive proof batch, EVM batch, deployment profile, second-client route, or opcode profile is committed as pre-evaluated evidence. Their status is `NOT_EVALUATED` until the reproducible commands execute. The report's historic values are reference values only and are not copied into fresh-run measured fields.

## Gate result

`NOT_EVALUATED`. Source identity checking is implemented. Promotion requires 60 generated records, native and EVM success, measured deployment gas, and comparison of the resulting gas distribution to the report.

## Decision and compatibility

Accept C00 as the immutable comparison definition, not as a deployable candidate. It intentionally preserves all v0.3 protocol incompatibilities and introduces no alias, fallback, codec, or custody change. Generated research fixtures are incompatible with production use.

## Review still required

Independent AIR/verifier review, P2BB512 structural analysis, a complete QROM treatment, a full hiding/ZK analysis, multi-target security accounting, maximum valid frontier/gas analysis, abandoned-checkpoint economics, runtime-hash-bound deployment manifests, a second-client reproduction, and a public-network review remain outstanding.
