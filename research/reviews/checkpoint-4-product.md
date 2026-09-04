# Checkpoint 4 — product architecture

**Verdict:** `PASS_NEGATIVE_DECISION`. Selected product path: none.

This is an internal independent review. It grants no security, deployment, custody, liveness, sequencer, or external cryptographic acceptance.

- Individual Ethereum L1: no security-qualified finalist. The C00 baseline fails nine of 60 Part A cap checks and its internal pool creation cost exceeds the active transaction cap.
- Aggregation: `STOP_BY_DEPENDENCY`; no accepted hiding inner or outer proof and no complete settlement totals.
- Robust two-call: the state-machine attack harness passes, but every retained active/64/96 projection misses the 12M/12M/20M gate and no exact integrated proof path exists.
- L2: the SP-71 product gate is `NOT_EVALUATED_NOT_PASSED`. The separate ordinary-path admission sweep rejects 210 KiB on OP, Arbitrum, and Scroll. Required local/testnet, OP testnet, and Arbitrum-family testnet measurements are incomplete.
- Prover operations: `FAIL`; H1 cold, H2/H3, required workflows, and a practical implemented CLI are absent.

Only blocker-closing evidence acquisition may proceed. Product promotion, custody integration, and deployment remain forbidden.
