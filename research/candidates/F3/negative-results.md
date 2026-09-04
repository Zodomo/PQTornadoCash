# F3 negative results and stops

- Eight-byte base elements double raw trace-opening bytes relative to 31-bit candidates.
- The field has slightly fewer than 2^64 elements, so the quadratic challenge space is slightly below 2^128 and has a 127-bit floor.
- PCS commit/open/verify is not benchmarked because SP-40 does not freeze the required hash/MMCS/transcript/PCS tuple; selecting one would add a protocol decision.
- Peak RSS is process-wide rather than per-operation, and thread-scaling includes worker creation; neither is a complete prover resource result.
- No complete hiding proof, complete verifier gas, proof byte count, or Pareto win is claimed.

These stops are gates, not zero-cost entries. Unsupported or unmeasured work must not be converted into a favorable score.
