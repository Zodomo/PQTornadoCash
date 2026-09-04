# ADR: Stop SP-80 before prototype construction

## Status

Accepted: `CURRENT_RESEARCH_FRONTIER_NO_VIABLE_NEXT_BUILD`.

## Context

SP-80 requires consideration of bundles A-F, but authorizes full implementation only for bundles that pass their component gates. A complete prototype must include all thirteen items listed in the plan; a partial verifier plus projected economics is explicitly insufficient.

The local records do not contain a security-qualified fixed compression, an implemented finalist AIR or structured relation, an integration-authorized transcript, or a complete exact-PQTC EVM backend. The narrow successful observations are controls: Rust/TypeScript compression parity, upstream native HidingWhirPcs, standalone plain-WHIR Solidity build/tests, recursive Fibonacci architecture smoke, VEIL PoCs, and the SP-72 state model. Their own status records forbid promoting them to integrated PQTC finalists.

## Decision

Use a deterministic, fail-closed checker over hash-pinned local evidence. For every required component, separately evaluate semantic, hiding, security, native, EVM, calldata, gas, and source-binding gates. Exact equality to the coded pass predicate is required. Missing or null evidence is non-passing, never zero and never an implied success. A bundle with an alternative inner/backend group needs one alternative that passes all eight gates.

No bundle passes. Therefore:

- eligible count is zero;
- finalist count is zero;
- prototype count is zero;
- every minimum-complete-prototype item is recorded as omitted for every bundle;
- no partial verifier, proof adapter, pool harness, or payment/state integration is implemented;
- no isolated gas delta or projection is combined into an integrated metric; and
- SP-80 concludes `CURRENT_RESEARCH_FRONTIER_NO_VIABLE_NEXT_BUILD` rather than forcing a winner.

`check.py` keeps predicates in executable code and hashes in `manifest.json`. Changing a status/result file without updating its pin fails the hash check. Updating a pin alone cannot change the coded predicate. Changing a blocked gate to `PASS` in the generated result fails exact deterministic recomputation; `--self-test` exercises that mutation.

## Bundle decisions

| Bundle | Last completed stage | Decisive stop |
|---|---|---|
| A | SP-10 Stage-A benchmark package | No compression candidate reached AIR; SP-20 stopped; transcript and FRI security/EVM gates remain open. |
| B | Upstream HidingWhirPcs native smoke | No accepted PQTC relation, matching EVM verifier, transcript reduction, or external review. |
| C | Upstream full-ZK maturity and standalone plain-WHIR build controls | Structured relation absent; no exact-PQTC native reproduction or full EVM Spartan path. |
| D | Upstream recursive Fibonacci architecture smoke | No eligible hiding inner proof, hiding recursion adapter, compatible pin, or EVM verifier. |
| E | Source check and experimental non-PQTC VEIL PoCs | SP-62 is STOP/DEFERRED; Flock lacks current Keccak, ZK, EVM, and a reproducible retained benchmark. |
| F | SP-72 research state harness | No security-qualified proof to split; full-path binding untested and gas projection fails. |

The machine result contains every blocking gate, exact evidence path/hash, full omitted checklist, and revival condition.

## Consequences

There is no deployable or custody-qualified output from SP-80. Existing component measurements keep their original research/control labels. A future rerun can revive a bundle only after upstream evidence changes, hashes are deliberately refreshed, and the unchanged semantic predicates pass; weakening predicates is a new decision requiring review.
