# ADR — Reproduce HidingWhirPcs, defer PQTC integration

## Decision

Compile the complete `HidingWhirPcs` commit/open/verify API from pinned Plonky3, using deterministic public proxy data and a newly OS-seeded `CryptoRng` for each of two proofs. Require both proofs to verify and their serialized bytes to differ. Capture proof bytes, prover and verifier wall time, process peak RSS, and the upstream hiding base-case security report.

Classify every result as `UPSTREAM_BASELINE_NOT_PQTC`. This smoke establishes upstream API executability and fresh masking only. It does not implement or measure the PQTC relation.

## Relation boundary

No SP-10 compression candidate was accepted. Frozen v0.3/H0 is therefore the only faithful control: fixed-denomination withdrawal semantics, binary depth-20 P2BB512-v1 tree, 16-field digest, 256×190 AIR, 1,186 constraints, degree seven, 240 application permutations, 220 Merkle-path permutations, and a public statement binding scope, root, nullifier, recipient, relayer, and fee. The smoke implements none of those constraints or bindings.

## Integration gate

C20 is `DEFERRED`, despite the executable upstream hiding path, until all of these gates clear:

1. SP-02 native malformed-proof panic containment;
2. an accepted SP-10 relation and exact common-corpus mapping;
3. a matching complete EVM verifier and canonical codec/transcript;
4. an end-to-end security and exact-transcript QROM argument; and
5. external cryptographic review.

The upstream diagnostic security report cannot clear those gates.
