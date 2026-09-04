# ADR — Advance Only the Native HVZK-WHIR Attempt

Research cutoff: **2026-09-04**.

## Decision

Advance **SP-51 native HVZK-WHIR** as the only implementation attempt authorized by this landscape review. Use pinned Plonky3 0.6.0 commit `3152b14a89067c83775a8076cc262ffc48a1fd7c` and its complete `HidingWhirPcs` masking pipeline. This is authorization to implement and measure the native PQTC relation; it is not an EVM pass, a security qualification, or permission to claim a concrete QROM security level. [S1–S5]

No other candidate is advanced to finalist implementation by this ADR. The `PASS` recorded for native full-ZK Spartan-WHIR in `matrix.json` is a technical native-sub-spike disposition: its public API can express a full-ZK R1CS proof without inventing a hiding protocol. It remains reference work under this decision, not a second authorized implementation track, because its exact PQTC relation, license grant, EVM path, and implementation-specific QROM argument are unresolved. [S12–S14, S33]

## Rationale

HVZK-WHIR is the only primary hiding-PCS track for which both the published construction and complete pinned implementation exist. The source includes ZK Reed-Solomon encoding, masked sumcheck, code-switching rounds, a masked base case, and a multilinear PCS adapter requiring cryptographically secure randomness. Implementing the native relation therefore does not require designing a new hiding protocol. [S1–S4]

The authorization is deliberately native-first. No public hiding-WHIR Solidity verifier matching `HidingWhirPcs` was located. The existing Solidity WHIR line has a different, plain proof format and placeholder Spartan fields, so it cannot serve as the verifier or codec for this attempt. [S15–S17]

## Required gates for the authorized attempt

The implementation attempt must:

1. Use the pinned Plonky3 commit and the hiding `HidingWhirPcs` surface, not plain WHIR, STIR, Circle-FRI, or an unqualified non-ZK PCS. [S2, S4–S5, S7, S11]
2. Build and audit the exact PQTC multilinear relation and public-input binding; do not infer preservation of repeated-block structure from a generic backend.
3. Source mask and WHIR randomness from a `CryptoRng`; predictable randomness invalidates witness hiding. [S4]
4. Match the complete masked transcript and proof shape in every prover/verifier implementation.
5. Produce an independent end-to-end soundness and binding budget. Plonky3's hiding base-case report is diagnostic only and does not certify the compiled PCS or preceding reductions. [S3]
6. Treat Fiat–Shamir, malicious-verifier security, and QROM security as explicit obligations for the exact hash, transcript, parameters, and composition. The interactive HVZK/RBR theorem does not discharge those obligations automatically. [S1, S3–S4]
7. Make no EVM, gas, calldata, deployability, or custody claim until a matching hiding verifier is implemented and measured.

Failure of any required gate prevents qualification; it must not be relabeled as a partial pass.

## Permitted lower-bound work

The following measurements may run only as isolated, prominently labeled lower bounds. They cannot become privacy-qualified finalist evidence:

- **STIR:** `BENCHMARK_ONLY`, explicitly non-hiding because pinned `TwoAdicStirPcs` sets `ZK = false`. [S6–S8]
- **Historical Flock batch-44:** non-hiding historical baseline only, after checkout of parent `c2d0c2485a54f7b7694e19f4f59730ffde3405cf`. The harness proves capacity 48 for 44 requested inputs by adding four valid all-zero Keccak permutations. No upstream batch-44 result exists. [S25–S27]
- **Existing `sol-spartan-whir` figures or reruns:** standalone plain-WHIR lower bounds only. Every record must say **“standalone WHIR — not Spartan and not PQTC.”** [S15–S17]

A lower-bound run does not reopen a deferred or stopped finalist decision.

## Deferred tracks

- **Circle-FRI (`DEFERRED`):** the paper's hiding route is not exposed by pinned `CirclePcs`, the non-interactive treatment is postponed, and no matching generic EVM verifier or concrete QROM theorem was located. [S9–S11]
- **`sol-spartan-whir` as an EVM finalist (`DEFERRED`):** the current exporter and fixtures contain placeholder Spartan fields around standalone plain WHIR. A full-ZK exporter, matching verifier, deployability architecture, and conformance vectors are absent. [S15–S17]
- **Plonky3 recursion (`DEFERRED`):** the tree uses Plonky3 0.7.0 rather than the mandated 0.6.0 pin; the Keccak path remains non-ZK; recursive WHIR mirrors the ordinary verifier rather than the hiding adapter; no EVM or recursion-specific QROM/privacy theorem was located. [S18–S21]
- **VEIL over Flock (`DEFERRED`):** the PoC's concrete adapter is KoalaBear degree-4 with stacked Basefold, not Flock's binary-field Ligerito/transcript. The binary-field adapter, Flock verifier compiler, transcript binding, soundness analysis, and EVM backend are missing. [S28–S32]
- **Native full-ZK Spartan-WHIR as a separate program:** technically `PASS` for a native sub-spike, but not advanced by this ADR pending the exact PQTC R1CS, explicit redistribution license, and the same transcript/QROM review required of any finalist. [S12–S14, S33]

## Stopped track

**Flock batch-44 is `STOP` as a PQTC finalist.** Its paper states that the implementation is not zero knowledge; the official tree has no EVM verifier; and current Flock removed both Keccak encoders and their consumers at exact commit `0f0d63268e1373c585251e95152b3a6943e2d818`. The missing zero knowledge, current Keccak relation, PQTC glue, and EVM verifier cannot be cured by relabeling a historical throughput benchmark. [S22–S24]

VEIL remains deferred research and does not rescue or reopen this stopped Flock decision. [S28–S32]

## License consequences

Plonky3's inspected pin declares `MIT OR Apache-2.0`. [S5] The `ethereum/spartan-whir` and `ethereum/sol-spartan-whir` repositories have no detected GitHub license and no complete LICENSE file at their inspected commits; obtain an explicit grant before copying or redistributing either codebase. The Solidity README's trailing `MIT` text does not clear that gate. See `L1`–`L5` in `sources.json`.

## Evidence boundary

This ADR is based only on pinned papers, repository source, repository metadata, and upstream documentation recorded in `sources.json`. The source researcher ran **no command**. Reproduction entrypoints in `matrix.json` and `README.md` are identified but unexecuted. Quoted timing, proof-size, calldata, and gas numbers remain upstream standalone measurements and are not PQTC evidence.

Absence findings are bounded to the official repositories, issues, and papers inspected at the recorded pins and cutoff. No CVE or GHSA fixed range is used to justify this decision.
