# C10 assumptions and projection formulas

## Frozen facts

- Relation: v0.3/H0 `WithdrawalAir`; logical height 256, proof degree bits 9 after one complete-hiding padding bit, width 190, 1,186 constraints, maximum degree 7, 16 quotient chunks.
- PCS: pinned Plonky3 `HidingFriPcs`, binary folding, `MerkleTreeHidingMmcs` with eight salt fields, BabyBear and degree-4 BabyBear challenge extension, KeccakPair512 transcript.
- Entropy: each proof independently seeds MMCS and PCS `StdRng` instances from operating-system entropy. No deterministic prover seed exists.
- Security: only the independent calculator's `single_target.best_proven.floor_quantum_bits` is eligible. Random-words is conjectural and batch-unmodeled and is excluded.

## Buildability

Complete hiding requires at least one random codeword. Degree 7 requires `2^log_blowup >= 7`, hence log blowup 2 fails and 3 is the minimum buildable point. Query count must be 1 through 65,535, binary arity is fixed to one, final-polynomial log length must be below proof degree bits, and grinding is fail-closed above 31 bits in this research executable.

## Broad-grid projection, formula version 1

These quantities are `PROJECTED_BASELINE_REGRESSION_NOT_MEASURED`. Let `q` be queries, `b` log blowup, `r` random codewords, and `f` final-polynomial log length. Production A/B proof bytes are projected as

`max(0, 20,012 + 5,904q + 768q(b-4) + (r-4)(76q+304) + 16(2^f-1))`.

The intercept and q coefficient exactly recompose the C00 60-run q32 median of 208,940 bytes. The blowup component is twelve 64-byte input/FRI authentication-digest opportunities per query per extra LDE bit. The hiding component is 19 batches of one 4-byte leaf value per query plus 19 16-byte global extension openings. The final component is one 16-byte extension value per added coefficient. This is a transparent linear/component estimate, not a codec proof-size theorem.

The projected split uses the measured fixed-proof ratio `108326 / 212204` for A and the remainder for B. ABI overhead is 318 bytes for A and 350 bytes for B. Zero-byte share uses the 60-run median zero count divided by median proof bytes.

Regular A/B gas scales the corresponding C00 p50 total gas by `q/32 * (0.35 + 0.65*2^(b-4))`. Calldata floors are independently applied as `21000 + 10z + 40n` (active EIP-7623), `21000 + 64(z+n)` (scheduled-unactivated scenario), and `21000 + 96(z+n)` (draft-unscheduled scenario). All projected gas remains non-exact because execution was not run for research codecs.

Projected prover time scales C00 p50 by `(0.50 + 0.50*2^(b-4)) * (0.70 + 0.30*q/32)`. Projected RSS scales by `(0.60 + 0.40*2^(b-4))`.

## Open assumptions

MMCS quantum binding is a manifest cap, not structural cryptanalysis. No complete QROM proof covers the custom transcript and Fiat-Shamir composition. LDR rows additionally require the calculator-recorded Johnson correlated-agreement assumption. No projection establishes a formal maximum over all valid proofs or exact production EVM behavior.
