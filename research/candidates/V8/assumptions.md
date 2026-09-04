# V8 assumptions

- Inherited: Frozen v0.3 relation, q32 profile, transcript, BabyBear modulus, two-call semantics, and 512-bit proof digests remain unchanged unless the inheritance matrix explicitly marks a layer modified or replaced.
- New: 31-bit packing has exact section lengths, canonical field rejection, and zero terminal padding. Derived-value omission is allowed only when recomputed from prior transcript state.
- Encoded BabyBear fields are canonical big-endian u32 or the explicitly framed little-endian 31-bit stream; neither form reduces out-of-range values.
- Full-transaction gas, runtime attribution, proof/prover delta, and dynamic opcode counts remain unmeasured until a canonical full verifier variant exists.
- Rust `bench()` totals have no warmup or distribution and are DIAGNOSTIC_NOT_COMMON_PROTOCOL; only isolated Solidity gas is classified as measured.
- No isolated microbenchmark delta is added to another to claim complete-verifier savings.
