# F4 negative results and stops

- The base field cannot run the frozen multiplicative two-adic FFT/FRI path beyond size two; a circle-backend port is mandatory.
- The approximately 124-bit challenge space is below a strict 128-bit uniform challenge target.
- PCS commit/open/verify is not benchmarked because SP-40 does not freeze the required hash/MMCS/transcript/PCS tuple; selecting one would add a protocol decision.
- Peak RSS is process-wide rather than per-operation, and thread-scaling includes worker creation; neither is a complete prover resource result.
- No complete hiding proof, complete verifier gas, proof byte count, or Pareto win is claimed.

These stops are gates, not zero-cost entries. Unsupported or unmeasured work must not be converted into a favorable score.
