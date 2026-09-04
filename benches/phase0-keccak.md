# Phase 0 Hiding-FRI Keccak Spike

Measured on Apple M4 Max, arm64 Darwin, release profile. Plonky3 commit `3152b14a89067c83775a8076cc262ffc48a1fd7c`; Rust 1.97.0. Command:

```text
/usr/bin/time -l cargo run --release -p pqtc-cli -- benchmark-keccak
```

| Metric | Result |
|---|---:|
| Active Keccak-f permutations | 1 |
| Trace rows | 32 |
| Keccak AIR columns | 2,633 |
| Canonical Postcard proof bytes | 115,199 |
| Prove time | 20 ms |
| Native verify time | 8 ms |
| Maximum resident set size | 12,255,232 bytes |

The proof uses BabyBear, its degree-4 extension, `HidingFriPcs`, four-byte canonical field leaves, eight random BabyBear salt elements per leaf, two random codewords in the `dev` profile, 512-bit Keccak-pair MMCS digests, and the typed 512-bit Keccak transcript. Two proofs made through one configuration differ and both verify.

This spike is a feasibility result, not a security result. The `dev` profile has two FRI queries and no grinding. Its proof is already larger than the direct-verifier target because the maintained reference Keccak AIR is wide. The result supports the staged-verifier decision: one query opens about 10.5 KiB of trace field data before authentication paths and FRI openings, which can fit the 32 KiB staged query target, while a complete compact proof is not expected to fit the 96 KiB direct target.
