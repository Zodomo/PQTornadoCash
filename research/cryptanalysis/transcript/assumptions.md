# SP-30 transcript assumptions

- Repository v0.3 and Plonky3 commit `3152b14a89067c83775a8076cc262ffc48a1fd7c` are frozen comparison inputs.
- The production proof shape is degree bits 9, base degree bits 8, no preprocessed commitment, trace width 190, 16 quotient chunks, four hiding codewords, nine binary FRI rounds, and 32 queries.
- BabyBear uses modulus `2013265921`; field decoding rejects rather than reduces, and extension coefficients use basis order.
- `K512` means two Ethereum Keccak-256 calls with distinct one-byte half prefixes and a one-byte domain tag.
- A zero-bit PoW check observes and squeezes nothing, matching the pinned trait implementation; v0.3 uses nonzero 16- and 8-bit checks.
- The deterministic corpus exercises canonical full widths. It is not represented as a canonical production proof and cannot support a full-path EVM claim.
- JavaScript instrumentation counts final accepted transcript work, not discarded prover grinding trials; vector generation is deterministic.
- Solidity prefix/parser gas and bytecode sizes are executable focused-run observations under the recorded canonical profile. EVM memory expansion and integrated full-verifier gas remain `NOT_EVALUATED`.
- The language APIs are unconstrained transcript primitives, not protocol claim/boundary state machines; premature sampling is possible and blocks integration.
- Generator-local label mutations do not establish serialized-grammar rejection or Rust/Solidity parity.
- Full-width vector retention does not complete the continuation redesign: `bytes32` identifiers, single-slot lookup overwrite, and hashed-record comparison remain unresolved.
- The research grammar deliberately domain-separates T1–T3 and the versioned T0 mode. T0 production-compatible mode omits that new version prefix solely to reproduce v0.3.
- A 32-byte key is an index only; security-relevant comparisons use full-width stored values.
- No public network, RPC, `.env`, live key, classical wrapper, or noncanonical serialization participates.
