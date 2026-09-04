# V2 assumptions

- Inherited: Frozen v0.3 relation, q32 profile, transcript, BabyBear modulus, two-call semantics, and 512-bit proof digests remain unchanged unless the experiment row explicitly says otherwise.
- New: Witnesses are accepted only for denominators whose nonzero obligation is independently enforced. Zero-legal batch and selector legs retain native handling.
- Encoded BabyBear fields are canonical big-endian u32 or the explicitly framed little-endian 31-bit stream; neither form reduces out-of-range values.
- Full-transaction gas, runtime attribution, proof/prover delta, and dynamic opcode counts remain unmeasured until a canonical full verifier variant exists.
- No isolated microbenchmark delta is added to another to claim complete-verifier savings.
