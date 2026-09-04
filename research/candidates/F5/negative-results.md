# F5 negative results and stops

- Every raw base/challenge element is 32 bytes: eight times a 31-bit raw element.
- No pinned default application-permutation parameters or complete PQTornado PCS configuration are available.
- PCS commit/open/verify is not benchmarked because SP-40 does not freeze the required hash/MMCS/transcript/PCS tuple; selecting one would add a protocol decision.
- Peak RSS is process-wide rather than per-operation, and thread-scaling includes worker creation; neither is a complete prover resource result.
- No complete hiding proof, complete verifier gas, proof byte count, or Pareto win is claimed.

These stops are gates, not zero-cost entries. Unsupported or unmeasured work must not be converted into a favorable score.
