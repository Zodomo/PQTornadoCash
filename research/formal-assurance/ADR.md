# ADR: Bound assurance work to mapped surfaces and a semi-formal controller model

## Status

Accepted for next-generation plan section 18 research. No production or protocol acceptance follows.

## Context

Section 18 asks whether finalist implementations are amenable to single-source AIR/R1CS generation, symbolic constraint coverage, a Lean/Coq/Isabelle target, finite controller checks, verified proof-codec parsing, and Rust/Solidity arithmetic equivalence. The research program currently has no finalist and no security-qualified candidate. Frozen v0.3 supplies concrete evidence, but it must remain unchanged and its tests, vectors, strict parsers, and parallel Rust/Solidity implementations are not formal proofs.

The v0.3 two-call path has a useful bounded control problem: Part A creates a consumer- and statement-bound checkpoint; Part B must match all bindings, complete verification, consume the checkpoint, and allow the pool to spend one nullifier and perform payout atomically. This can expose controller mistakes without pretending to model the cryptographic protocol.

## Decision

1. Keep a machine-readable, source-pinned inventory of all six requested surfaces for frozen v0.3 and current research.
2. Do not choose or formalize a next-generation relation until a finalist and its interfaces are frozen.
3. Retain an exhaustive finite-state checker over a documented equality-class abstraction. Call it **semi-formal**, never a formal verification or protocol proof.
4. Require mutation cases for missing consumer, statement, and global-data bindings; retained checkpoints; spent-nullifier reuse; non-atomic failure; checkpoint overwrite; and skipped second-half verification.
5. Generate a deterministic JSON result with input hashes and counterexample witnesses. Verification must byte-compare a fresh result with the retained file.
6. Map Lean, Coq, and Isabelle as alternative homes for narrow targets; choose one based on the finalist, libraries, extraction needs, and reviewer expertise.
7. Express next-build cost only as integer engineer-week **PROJECTION** planning ranges with prerequisites and exclusions. Keep external cryptographic acceptance open and unsummed.

## Why this boundary

The finite model is small enough to exhaust to a reachable fixed point and strong enough to make plausible transition mutations observable. It gives immediately reproducible negative evidence and makes atomicity and binding assumptions explicit. Extending it with proof bytes, cryptography, EVM semantics, or arbitrary concurrency without a checked refinement would add apparent detail rather than justified assurance.

Finalist-specific AIR/R1CS, codec, arithmetic, and theorem-prover work would otherwise be built against interfaces that may be discarded. Mapping amenability and costs now preserves useful planning information without inventing completion.

## Consequences

- A `PASS` result means only that the reference abstract transitions satisfy the listed invariants and all declared mutants violate their expected invariant.
- The model cannot establish Solidity equivalence, EVM revert behavior, parser safety, arithmetic equivalence, cryptographic soundness, privacy, gas feasibility, liveness, or deployment safety.
- Frozen v0.3 remains evidence rather than a selected next-generation design.
- The next build must freeze a finalist before spending the estimated 52–88 engineer-weeks.
- External cryptographic review, protocol theorems, audits, remediation, H2/H3 evaluation, and live-chain evidence remain outside the estimate and unresolved.

## Rejected alternatives

- **Call the checker formal verification:** rejected because no refinement connects it to source, bytecode, or protocol semantics.
- **Treat test vectors as arithmetic proofs:** rejected because finite examples do not quantify over all field and encoding values.
- **Treat mutation coverage as constraint completeness:** rejected because the mutation classes are finite and manually selected.
- **Pick a proof assistant immediately:** rejected because target/library/team fit cannot be assessed against a nonexistent finalist.
- **Formalize all three assistants:** rejected as redundant scope; the estimate covers one narrow checked development.
- **Assign zero cost to external acceptance:** rejected; it remains `OPEN_UNCOSTED`, not included or implicitly free.
