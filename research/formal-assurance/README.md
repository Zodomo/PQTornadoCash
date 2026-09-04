# Formal and semi-formal assurance

This research-only package covers section 18 of the next-generation plan. It inventories assurance surfaces in frozen v0.3 and current research, retains a deterministic exhaustive checker for an abstract two-call state machine, and estimates the remaining finalist-specific work. There is no finalist and no security-qualified candidate.

**Nothing in this package is a formal-verification claim, a protocol proof, a cryptographic soundness claim, an audit, external acceptance, or deployment authorization.** The checker is semi-formal: it checks every transition in a deliberately finite abstract model but has no refinement proof to Solidity, EVM execution, proof bytes, or cryptography.

## Reproduce

From the repository root, regenerate the retained result:

```sh
python3 research/formal-assurance/run.py
```

Verify that a fresh deterministic result is byte-identical to the retained output:

```sh
python3 research/formal-assurance/run.py --check
```

Both commands exit nonzero if the reference model violates an invariant or any declared plausible mutation is not detected. `--check` also exits nonzero for a missing or byte-different retained result. The output is `results/checker-results.json`, governed by `result.schema.json`; `manifest.json` records the complete output plan.

## Inventory

`inventory.json` is the authoritative machine-readable inventory. Its dispositions are:

| Surface | Frozen v0.3 evidence | Current disposition | Principal gap |
|---|---|---|---|
| Single-source AIR/R1CS | Separate Rust AIR and Solidity evaluator; no exact R1CS | Blocked pending finalist | No checked relation IR or target-preservation proof |
| Symbolic constraint coverage | Row/limb/boundary and corpus mutation tests | Partial test evidence only | No stable constraint IDs or solver-backed completeness result |
| Lean/Coq/Isabelle | No retained development | Targets mapped, assistant not selected | No finalist semantics, toolchain pin, or imported-assumption ledger |
| Finite controller transitions | v0.3 pool/registry semantics | Abstract exhaustive checker complete | No Solidity/EVM refinement, byte model, concurrency, gas, or liveness |
| Proof-codec parsing | Strict Rust/Solidity readers and round trips | Tested, not verified | No normative grammar or parser/refinement proof |
| Rust/Solidity arithmetic equivalence | Shared constants, vectors, integrated proof runs | Evidence only | No complete field/hash/transcript/AIR arithmetic refinement |

The mapped proof-assistant targets are intentionally narrow. Lean is amenable to executable relation/arithmetic refinement, Coq to a canonical codec grammar and parser theorems, and Isabelle to controller transition refinement. This is an option map, not a selection or a claim that three ports are required.

## Abstract finite-state checker

The model has one checkpoint slot and one nullifier. Consumer, statement, core-proof ID, global-data digest, and checkpoint digest each range over two equality classes. Pool validation, common parsing, second-half verification, and both transfers range over Boolean outcomes. Starting from an empty checkpoint and unspent nullifier, `checker.py` computes the least reachable fixed point and checks every action from every reachable state.

Checked invariants include:

- Part A requires valid pool state and an unspent nullifier;
- an exact Part A retry is idempotent, while a conflicting checkpoint cannot overwrite the existing one;
- Part B requires the stored consumer, statement, core proof, global data, and checkpoint bindings;
- common parsing, second-half verification, and both transfers must succeed;
- successful completion consumes the checkpoint and spends the nullifier exactly once;
- spent nullifiers block replay; and
- every failed transition is atomic, including failures after logical checkpoint deletion or during payout.

`mutations.json` removes or corrupts each of these controls. The retained result includes a deterministic counterexample path for every mutation. Mutation detection demonstrates that the checker can catch these modeled faults; it does not establish that the abstraction is complete or that production code implements it.

The abstraction omits hash collisions, exact proof IDs, proof bytes and cursor arithmetic, field arithmetic, the cryptographic verifier, reentrancy call frames, multiple concurrent slots/nullifiers, gas, liveness, chain reorganization, and deployed-chain behavior. H2/H3 hardware and live-chain behavior remain `NOT_EVALUATED`; external cryptographic acceptance remains `OPEN`.

## Next-build scope

`scope-estimates.json` contains integer **PROJECTION** planning ranges. Under its assumptions, summed serial effort is **52–88 engineer-weeks**:

| Workstream | Engineer-weeks |
|---|---:|
| Single-source relation IR and AIR/R1CS generation | 10–16 |
| Symbolic constraint coverage | 6–10 |
| One proof-assistant refinement target | 12–20 |
| Controller SMT/refinement linked to Solidity/EVM semantics | 4–7 |
| Codec grammar and parser verification | 8–14 |
| Rust/Solidity arithmetic equivalence | 8–14 |
| Integration, CI, and review packet | 4–7 |

These are explicit **PROJECTION** planning ranges, not measurements or schedule promises. They assume the finalist relation and both implementation boundaries are frozen first and that one of Lean, Coq, or Isabelle is chosen. They exclude a complete protocol theorem, new primitive proofs, external cryptographic review/acceptance, audit findings and remediation, gas optimization, hardware evaluation, and deployment qualification. Those omissions are real gaps, not zero-cost work.

## Records

- `manifest.json`: artifacts, bounds, commands, schema, and retention policy.
- `assumptions.json`: abstract-model and estimate assumptions.
- `inventory.json`: evidence-backed assurance map.
- `scope-estimates.json`: next-build ranges and exclusions.
- `source-pins.json`: frozen/current commits, canonical Solidity settings, and source hashes.
- `negative-results.json`: claims that were rejected, deferred, or not evaluated.
- `status.json`: machine-readable disposition.
