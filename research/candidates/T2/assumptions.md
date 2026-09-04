# T2 assumptions

- Frozen comparison target: repository v0.3 and Plonky3 `3152b14a89067c83775a8076cc262ffc48a1fd7c`.
- BabyBear fields are unsigned big-endian 32-bit words strictly below `2013265921`; extension values are four such coefficients in basis order.
- Every commitment and transcript state is represented as a 64-byte left-then-right digest in the research vectors, but continuation identifiers remain bytes32 and the full-width redesign is incomplete.
- Production shape is 190 trace columns, 16 quotient chunks, four hiding codewords, nine binary FRI rounds, 32 queries, 16-bit commit PoW, 8-bit query PoW, and 13-bit query indices.
- Synthetic deterministic vector bytes exercise the exact full widths but are not claimed to be a retained canonical production proof.
- The transcript primitives are not protocol state machines: they permit premature sampling, and the TypeScript label oracle is not serialized-grammar validation.
- Rust/Solidity mutation execution and cross-language parity execution have not been completed.
- Focused EVM measurements cover the standalone prefix and parser harness; integrated full-verifier gas and EVM memory expansion remain unmeasured.
- The Solidity bytes32 lookup has unresolved single-slot overwrite and hashed-record-comparison concerns; it is not approved as authoritative storage.
- No public network, RPC, environment secret, live key, classical wrapper, or noncanonical encoding is used.
- All cryptographic and integration gates remain closed.
