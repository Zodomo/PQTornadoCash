# SP-80 integrated finalist evaluation

## Conclusion

`CURRENT_RESEARCH_FRONTIER_NO_VIABLE_NEXT_BUILD`

All six plan-required bundles were evaluated. Eligible: **0**. Finalists: **0**. Complete prototypes: **0**. Because no bundle passed every prerequisite gate, this package intentionally contains no verifier, proof adapter, pool, custody path, or partial prototype.

## Deterministic evaluation

Run:

```sh
python3 research/integrated-finalists/check.py --check
python3 research/integrated-finalists/check.py --self-test
```

Normal `--check` and `--write` are fail-closed against the committed pins. After an intentional upstream evidence correction, refresh only the same fixed paths and regenerate with:

```sh
python3 research/integrated-finalists/check.py --refresh-source-hashes
```

The refresh mode cannot add, remove, or redirect a prerequisite record and cannot alter executable pass predicates. It recomputes hashes for the fixed catalog, then runs the same zero-finalist evaluation; a changed status that actually passed every predicate would stop at the required zero-frontier assertion rather than silently preserve this conclusion.

The checker:

1. loads every prerequisite's local status, manifest, and result record from `manifest.json`;
2. verifies the exact SHA-256 pin before using a record;
3. evaluates semantic, hiding, security, native, EVM, calldata, gas, and source-binding predicates by exact equality;
4. treats a missing pointer, missing file, null, benchmark-only label, projection, and open review as non-passing;
5. requires all direct components and at least one all-gates-passing member of each alternative group;
6. requires bundles A-F exactly once, the complete thirteen-item prototype checklist, and the fixed zero-finalist conclusion; and
7. mutates the first blocked component gate to `PASS` and proves exact recomputation rejects it.

`outputs/results.json` is the complete matrix and evidence ledger. Every component entry includes its exact status/manifest/result path and SHA-256, every gate includes the decisive JSON pointer, required value, observed value, and evidence pin, and every bundle includes last completed stage, blockers, omitted prototype requirements, and revival conditions. `status.json` pins the result, schema, and manifest.

## Bundle matrix

| Bundle | Required architecture | Last completed stage | Eligibility | Main blockers | What could revive it |
|---|---|---|---|---|---|
| A | optimized Poseidon2 compression → vertical AIR → batched Keccak transcript → hiding FRI → direct Solidity | SP-10 Stage-A benchmark package | Blocked | `NO_AIR_CANDIDATE`; AIR stopped; transcript integration blocked; FRI has no security-qualified winner or measured direct-EVM finalist | Promote reviewed compression; implement exact AIR; close transcript/QROM/MMCS/advisory gates; measure complete direct-EVM path and binding |
| B | optimized compression/AIR → HVZK-WHIR → modular Solidity | upstream HidingWhirPcs native smoke | Blocked | no accepted PQTC relation; no matching EVM verifier; no exact-transcript reduction or external review | Integrate reviewed HVZK-WHIR on exact relation; contain malformed proof panics; implement/measure canonical EVM path |
| C | fixed compression → repeated R1CS/CCS → Spartan/sumcheck → hiding WHIR/VEIL → modular Solidity | upstream full-ZK maturity and standalone plain-WHIR build controls | Blocked | structured relation is hypothesis-only; no exact-PQTC native reproduction; full EVM Spartan and gas absent; license blocked | Implement/freeze relation; reproduce full hiding backend; complete license-clear EVM Spartan/HVZK verifier and measurements |
| D | best hiding inner proof → recursive relation → transparent outer proof → one-tx Solidity | upstream recursive Fibonacci architecture smoke | Blocked | zero eligible inner proofs; dependency mismatch; recursive Keccak non-ZK; no hiding adapter or EVM verifier | Qualify an inner proof; implement reviewed hiding-preserving recursion and exact one-call EVM path |
| E | Keccak relation → Flock → ZK/outer compression | source check and experimental non-PQTC VEIL PoCs | Blocked | SP-62 failed: current Flock has no Keccak, ZK, or EVM; historical run panics; no VEIL adapter | Upstream current Keccak/ZK/EVM support and reproducible security-qualified capacity; exact reviewed adapter and measurements |
| F | strongest proof that cannot fit one call → robust SP-72 state handling | SP-72 research state harness | Blocked | no security-qualified proof to select; full-path binding not evaluated; gas projection fails | First qualify and measure exact proof; establish intrinsic two-call need; bind it into SP-72 and measure both exact ABI calls |

## Minimum complete prototype checklist

The plan requires all of the following as one end-to-end artifact:

1. note generation;
2. commitment/nullifier derivation;
3. depth-20 tree/path;
4. full witness construction;
5. hiding proof generation;
6. native verification;
7. canonical proof codec;
8. Solidity proof verification;
9. pool statement reconstruction;
10. nullifier consumption;
11. recipient/relayer payout in a harness;
12. exact ABI transaction measurement; and
13. source-bound parameter manifest.

For each bundle, `outputs/results.json` carries all thirteen entries with `implemented: false`, `evidencePath: null`, and the gate-stop reason. Null is not interpreted as zero or as a passing measurement. A partial implementation was not authorized.

## Evidence interpretation

A narrow `PASS` is preserved only at its original scope. In particular, an upstream smoke is not an exact-PQTC native proof, standalone plain-WHIR Solidity is not full EVM Spartan-WHIR, source-derived capacity is not a benchmark, a model-only state harness is not a bound two-call proof, source pins are not deployed runtime binding, and distinct proofs are not a hiding proof. SP-80 reports no new measured metric: `metricClaims` is empty.

## Files

- `ADR.md` — stop decision and consequences.
- `assumptions.json` — fail-closed policy and evidence boundaries.
- `manifest.json` — exact prerequisite status/manifest/result paths and SHA-256 pins.
- `negative-results.json` — preserved stops and prohibited inferences.
- `result.schema.json` — machine-result contract.
- `outputs/results.json` — complete A-F matrix and normalized component gates.
- `status.json` — zero-eligible/finalist/prototype disposition and output pins.
- `check.py` — deterministic evaluator, exact output validator, and mutation defense.
