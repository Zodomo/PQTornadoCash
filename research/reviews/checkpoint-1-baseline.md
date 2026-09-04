# Checkpoint 1 — baseline method freeze

**Verdict:** `METHOD_FREEZE_APPROVED` at commit `d956ac0a7cd878b200be240fa8fd9a1a3da09d30`.

This is an internal independent review. It is not external cryptographic acceptance.

- SP-00: `FAIL`. Nine of 60 Part A runs exceed the active EIP-7825 transaction cap. Pool internal creation gas is independently over that cap. Top-level deployment gas and mined receipts remain not evaluated. The Part B total-gas median differs from the prior report by -1.036% without isolated attribution.
- SP-01: internal methodology `ACCEPTED_WITH_LIMITATIONS`. For q32, random-words is 107 conjectural bits, LDR is 56 conditional bits under the Johnson correlated-agreement assumption, and UDR is 37 unconditional-theorem-regime bits. External review remains open.
- SP-02: `FAIL_ARCHIVED_FAILED`. Focused advisory regressions pass, but the native malformed-proof panic boundary remains unresolved.

No high- or medium-severity evidence-consistency finding remains after `checkpoint-1-corrections.json`. The approved next scope is isolated benchmarking only. Candidate integration, deployment, and security qualification remain forbidden.
