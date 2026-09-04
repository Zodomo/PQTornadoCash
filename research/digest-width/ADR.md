# ADR: No digest-width adoption from cross-cutting section 13

## Status

**NO_ADOPTION.** This is a research decision, not a production architecture change and not cryptographic acceptance.

## Context

Section 13 requires an exact comparison of KeccakPair-512, two-branch 384- and 320-bit truncations, and single-Keccak-256 as a nonqualifying lower bound. The project target is at least 100 quantum-adjusted binding bits after composition and multi-target accounting. The two truncated constructions have neither a complete reduction nor independent analysis. The frozen v0.3 KeccakPair construction also lacks a complete composition/QROM reduction.

## Decision

Do not adopt any width change.

- Keep KeccakPair-512 only as the frozen v0.3 baseline for comparison; this study does not approve it or change v0.3.
- Mark both truncated two-branch variants `STOP_PENDING_EXTERNAL_ANALYSIS`, regardless of favorable nominal generic exponents or byte savings.
- Reject single-Keccak-256 as `REJECT_NONQUALIFYING_LOWER_BOUND`: its single-target generic BHT exponent is `256/3`, whose integer floor is 85 bits, below the 100-bit target before any multi-target loss.
- Do not infer full-protocol gas from the Solidity component benchmark. A complete protocol variant would need exact serialization, all digest call sites, verifier behavior, storage transitions, calldata, and transaction accounting.

## Canonical constructions compared

Let `K(x) = keccak256(x)`, `t` be one byte, and `m` be exact payload bytes.

- 512: `K(0x00 || t || m) || K(0x01 || t || m)`.
- 384: `K(0x00 || t || m)[0:24] || K(0x01 || t || m)[0:24]`.
- 320: `K(0x00 || t || m)[0:20] || K(0x01 || t || m)[0:20]`.
- 256 lower bound: `K(0x00 || t || m)`; branch one is not evaluated.

Ranges are zero-based byte slices. Prefix means leftmost/MSB bytes. There is no implicit ABI framing.

## Consequences

At depth 20, sibling-only paths are exactly 1,280, 960, 800, and 640 bytes respectively. The 384- and 320-bit encodings still occupy two fixed EVM storage slots per digest; only the 256-bit lower bound drops to one. Their calldata savings therefore do not imply proportional storage-gas savings. The generic lifetime sweep remains decision support only because the two-branch reduction, every digest use, correlated targets, and external cryptographic review remain open.

## Reversal gate

Reconsider 320 or 384 only after an independent analysis covers the exact branch framing and truncation, combined collision and second-preimage properties, multi-target protocol volume, every application/MMCS/transcript/identifier use, and applicable QROM composition. Any candidate must retain at least 100 accepted bits after those adjustments. A new full-protocol implementation and measurement is separately required for adoption.
