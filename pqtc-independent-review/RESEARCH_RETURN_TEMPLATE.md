# PQTornadoCash — Targeted Research Return

**Return version:**  
**Public review commit:**  
**Experiment source commits:**  
**Evidence freeze commit:**  
**Environment IDs:**  
**External cryptographic review status:**  
**No deployment authorized by this document.**

## 1. Decision and what changed

Choose one decision from the follow-up plan. Explain which new measurements changed the decision relative to `e51a5c5…`.

State separately:

- what is physically executable;
- what meets the product targets;
- what remains cryptographically unqualified;
- what was not implemented;
- whether a new full engineering specification is warranted.

## 2. Required experiment completion matrix

| Package | Required executable result | Completed stage | Evidence path | Stop reason class | Reviewer |
|---|---|---|---|---|---|
| R2-00 | clean baseline, ledgers, deployment | | | | |
| R2-01 | formula/objective/object mapping | | | | |
| R2-02 | complete roles and matched kernels | | | | |
| R2-03 | actual vertical H0 hiding proof | | | | |
| R2-04 | complete compression relation comparison | | | | |
| R2-05 | integrated transcript/verifier | | | | |
| R2-06 | calibrated parameter analysis | | | | |
| R2-07 | same-relation hiding backend or minimal barrier | | | | |
| R2-08 | complete local transaction(s) | | | | |
| R2-09 | only conditionally entered branches | | | | |

Do not put PASS solely because the status file exists. A not-executed dependency stop remains not executed.

## 3. Provenance and reproduction

List the five handoff checks and distinguish metadata success from clean builds and fresh cryptographic execution. Include exact commands, exit statuses, logs, tools, environment, and hashes.

Explain relationships between public, report, source, and artifact commits. List any source or artifact missing from a fresh public checkout.

## 4. Baseline distribution and byte ledger

Present the original 60 retained runs separately from new clean-environment runs. Include strata, sample counts, quantile definitions, cap-exceedance counts, and uncertainty.

Provide exact proof sections that sum to raw bytes and ABI bytes. Attribute repeated A/B data and shared multiproof data. Link all run-level ledgers.

## 5. Baseline gas and deployment

Separate internal gasleft, modeled totals, capped top-level local transactions, and any separately authorized public receipts. Include constructor hashing, storage initialization, initcode, and runtime-code deposit.

List the actual target hardfork and current/prospective calldata rules. Do not add calldata floor to execution.

## 6. Security-model results

### 6.1 Pinned-equivalent versus alternative analysis

| Profile | Model/version | Selected m | Objective | UDR result | Conditional LDR result | Aggregate rule | Conditions/omissions |
|---|---|---:|---|---:|---:|---|---|
| q32 | | | | | | | |
| q48 | | | | | | | |
| q64 | | | | | | | |
| selected candidate | | | | | | | |

Reproduce and discuss the independent m=23 sensitivity. Do not adopt it as a system security claim without reviewing applicability.

### 6.2 Actual batching-object mapping

Explain distinct committed polynomials, extension coefficients, masks, rotations, quotient chunks, and reduction terms. Derive the calculator count from the actual PCS inventory. Do not assert that any one of 210, 330, or 524 is automatically correct.

### 6.3 Threat games and lifetime

Present separate games for note theft, useful collisions, membership forgery, proof forgery, continuation substitution, and witness hiding. State where quantum work models and random-oracle reductions apply. Record accepted and unresolved assumptions.

## 7. Exact hash modes and structural review

For each tested mode, provide field, width, constants, rounds, matrices, full input-lane layouts, feed-forward, output extraction, scope, role/domain controls, and security target.

| Mode | Exact roles complete? | Constants parity | Rust/TS/Solidity vectors | Misuse tests | Attack applicability | Concrete cost estimate | Reviewer status |
|---|---|---|---:|---|---|---|---|
| H0 control | | | | | | | |
| H5-like | | | | | | | |
| optional mode | | | | | | | |

An applicable attack with uncomputed cost is not labeled a demonstrated break.

## 8. Matched implementation-tier results

Show generic and optimized implementations under the same envelope. Explain the H0 generic-versus-production discrepancy using measured opcode categories. Do not multiply an unoptimized primitive by twenty and present it as a complete deposit.

| Mode/tier | Permutation gas | Node gas | Complete deposit gas | Deployment gas | Runtime bytes | Native cost | Measurement class |
|---|---:|---:|---:|---:|---:|---:|---|
| H0 reference | | | | | | | |
| H0 optimized | | | | | | | |
| H5 reference | | | | | | | |
| H5 optimized | | | | | | | |

## 9. Causal AIR comparison

| Pipeline | Rows | Masked rows | Main/aux widths | Constraint degree | Quotient chunks | Actual batch objects | Proof/ABI bytes | Native prove | EVM verify |
|---|---:|---:|---|---:|---:|---|---|---|---|
| H0 horizontal | | | | | | | | | |
| H0 vertical | | | | | | | | | |
| compression horizontal | | | | | | | | | |
| compression vertical | | | | | | | | | |

Provide fixed-parameter and security-normalized tables. Explain interaction effects rather than attributing all improvement to one change.

## 10. Transcript, codec, and verifier integration

Include phase state machine, exact frames, early-sampling rejection, cross-language challenges, full-width continuation tests, and an actual complete proof.

For each optimization, show isolated results, integrated results, and cases where savings failed to compose. List code/byte changes and security assumptions.

## 11. Calibrated FRI/Pareto analysis

State which values are exact, measured, calibrated, or outside the model. Plot/tabulate prediction residuals at real anchors. Account for fold arity, sibling values, cap/frontier overlap, and actual openings.

Do not map null complete gas to a physical failure. List measured and projected frontiers separately. Preserve assumption labels in security-normalized comparisons.

## 12. Same-relation alternative backend

State exact lowering/adapter, constraint closure, hiding mechanism, transcript, parameters, source pin, license status, and complete relation evidence.

If blocked, provide the minimal reproducer and bounded repair result. Explain why the blocker is architectural or merely engineering. Synthetic upstream smokes remain a separate table.

## 13. Complete local operational results

| Pipeline | Security/privacy status | Direct ABI | Direct gas | A ABI/gas | B ABI/gas | Deposit | Constructor | Worst-case bound | Current physical gate | Product gate |
|---|---|---:|---:|---|---|---:|---:|---|---|---|
| | | | | | | | | | | |

Include recipient/relayer balance changes, nullifier state, replay rejection, failed payout rollback, cross-session mixing rejection, invalid proof rejection, and state-lifecycle tests.

A local research harness is not a production pool. An actual verifier is required; a mock cannot satisfy this table.

## 14. State, privacy, and availability

Explain checkpoint occupancy, expiry, cleanup, replacement, consumer binding, stale roots, and malicious accepted prefixes. Part A is not a complete proof of knowledge. Demonstrate that a storage bound does not create indefinite withdrawal censorship.

State witness data available to every actor. Include note backup/indexer/relayer assumptions only to the extent tested. Describe native verifier panic containment and malformed-object coverage.

## 15. Conditional branches

For recursion, Flock, STIR/Circle, aggregation, L2, and hardware: list whether the entry gate was reached, what actually ran, exact metrics, and why the branch stopped. Do not expand the report with repeated empty candidate templates.

## 16. Negative results and rejected hypotheses

For each negative result: exact candidate, falsifier, result class, confounders, attempted repair, and reopening condition. Missing external review is distinct from a demonstrated below-target attack or measured gas failure.

## 17. Remaining questions

Each question has an owner, a reviewer, a smallest decisive experiment, a decision affected, dependencies, and work that can proceed independently.

## 18. Proposed next action

Explain the smallest next engineering-spec scope supported by the evidence, or the one additional experiment needed. Do not request another broad research reset unless the concrete lineage has been falsified.

## 19. Evidence validation record

Record ledger sums, hash checks, schema checks, source/bytecode binding, null/status checks, and reproduction results. Independent reviewers must confirm that conclusions follow from experiments, not just that the document has all headings.
