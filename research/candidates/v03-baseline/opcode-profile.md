# C00 opcode and component profile

**Component status: PASS for 60 Foundry A/B simulations. t8n coverage: PARTIAL_COVERAGE: PASS_1_FAIL_1_NOT_EVALUATED_58.**
The retained `gas/evm/v03-*.trace.log` set contains 60 complete call traces. Every trace records a passing pool-facing A/B execution, and the synthesizer byte-checks the four gas values against its run JSON. Part A execution ranges from 14,643,477 to 15,205,581 gas (p50 14,974,675.5); part B ranges from 11,815,711 to 12,486,352 (p50 12,271,183.5).

go-ethereum t8n coverage is run-scoped: 1 PASS (`v03-fixed-19`), 1 FAIL (`v03-fixed-01`), and 58 NOT_EVALUATED. The passing fixture has two sequential successful simulated receipts and 7,178,838 aggregated opcode steps. Pinned client identity and per-transaction opcode maps remain in its `evidence.json`; the capped failure remains in `failure-evidence.json`. Raw multi-gigabyte JSONL is deleted only after deterministic aggregation. These are deterministic Prague state-transition simulations, not mined receipts.

Foundry traces are component evidence. t8n receipts are simulated state-transition receipts. Neither is represented as a mined network receipt.
