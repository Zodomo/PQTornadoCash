# F1 negative results and stops

- The challenge space is below 2^124 and cannot by itself supply a strict 128-bit uniform challenge.
- Base two-adicity 24 is lower than BabyBear's 27, although it covers the frozen 256-row relation.
- PCS commit/open/verify is not benchmarked because SP-40 does not freeze the required hash/MMCS/transcript/PCS tuple; selecting one would add a protocol decision.
- Peak RSS is process-wide rather than per-operation, and thread-scaling includes worker creation; neither is a complete prover resource result.
- No complete hiding proof, complete verifier gas, proof byte count, or Pareto win is claimed.

These stops are gates, not zero-cost entries. Unsupported or unmeasured work must not be converted into a favorable score.
