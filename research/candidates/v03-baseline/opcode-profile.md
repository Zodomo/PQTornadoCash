# C00 opcode and component profile

**Component status: PASS for 60 Foundry A/B simulations. Raw opcode-count status: PASS_T8N_SIMULATION.**

The retained `gas/evm/v03-*.trace.log` set contains 60 complete call traces. Every trace records a passing pool-facing A/B execution, and the synthesizer byte-checks the four gas values against its run JSON. Part A execution ranges from 14,643,477 to 15,205,581 gas (p50 14,974,675.5); part B ranges from 11,815,711 to 12,486,352 (p50 12,271,183.5).

go-ethereum t8n evidence is retained for 1 passing fixture(s), with two sequential successful simulated receipts per fixture and 7,178,838 aggregated opcode steps. The pinned client identity and per-transaction opcode maps are retained in each `gas/t8n/*/evidence.json`. 1 additional capped simulation failure(s) remain visible in `failure-evidence.json`; they do not weaken the candidate's FAIL gate. Raw multi-gigabyte JSONL is deleted only after deterministic aggregation. These are deterministic Prague state-transition simulations, not mined receipts.

Foundry traces are component evidence. t8n receipts are simulated state-transition receipts. Neither is represented as a mined network receipt.
