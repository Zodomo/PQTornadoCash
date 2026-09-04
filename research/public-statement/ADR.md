# ADR: Preserve semantics; investigate transport packing only

## Status

Research decision accepted; production adoption prohibited.

## Context

The frozen v0.3 statement exposes 64 ordered BabyBear values: sixteen limbs each for scope, root, nullifier hash, and payout digest. The same ordering participates in AIR constraints, Fiat–Shamir transcript state, both proof-part headers, cross-part statement identity, pool validation, replay state, and transfers. A change at only one layer is unsound or non-interoperable.

Five minimization families were considered: removal, on-chain derivation, digest commitment, packing, and reordering. Deriving scope and payout at the pool boundary does not eliminate their AIR inputs; it only moves transport work. Root and nullifier are transaction-selected state identities and cannot be inferred from pool immutables. Bare removal loses required binding. Reordering saves no bytes and creates interpretation ambiguity. Digest commitment can reduce proof public inputs only after the AIR proves the full ordered preimage.

## Decision

1. Keep all four semantic groups and all 64 canonical limbs.
2. Permit research on a minimal ABI-only encoding of eight big-endian `u32` lanes per `bytes32`, decoded back to the exact v0.3 order before every consumer.
3. Require a new selector, statement/layout domain, codec version, parameter manifest, and complete caller migration. The changed layout has `v03Compatible = false`.
4. Stop the aggressive 16-field statement-digest design. Reconsider only after an implemented AIR constrains all 64 preimage fields, the transcript and both proof parts use an unambiguous versioned encoding, the pool still checks root/nullifier/payout semantics, and leakage, audit, and security gates pass.
5. Treat byte counts derived from static encodings as exact. Treat gas, changed AIR constraints/columns, and performance as projected until implemented and measured.

## Consequences

The minimal design can reduce each registry call's public-value ABI payload from 2,048 to 256 bytes while leaving the 256-byte proof-header statement and 64 AIR inputs unchanged. It is a transport optimization, not statement minimization.

The aggressive design would reduce each proof header by 192 bytes and a fixed ABI statement argument by 1,984 bytes, but no safe implementation exists. A naive current-hash schedule would add a projected 19 active permutations and overflow the current 256-row schedule (`240 + 19`). No gas or constraint saving is claimed.

No payout, replay, state-root, consumer, version, or parameter binding may be removed to recover compatibility or performance.
