# PQ Tornado Classic — Next-Generation Research Report

**Report status:** `[DRAFT | INTERNAL REVIEW | INDEPENDENTLY REPRODUCED | FINAL]`  
**Research-plan version/hash:**  
**Repository:**  
**Baseline tag:** `pqtc-v0.3-research-baseline`  
**Report commit:**  
**Evidence-manifest SHA-256:**  
**Evidence-manifest Keccak-256:**  
**Freeze date:**  
**Recommendation:** `[RECOMMEND_FULL_ENGINEERING_PLAN | RECOMMEND_ADDITIONAL_TARGETED_RESEARCH | RECOMMEND_ROBUST_TWO_TX_BUILD | RECOMMEND_AGGREGATION_OR_L2_STRATEGY | RECOMMEND_STOPPING_CURRENT_LINEAGE]`

> This document reports research evidence. It is not an audit, deployment authorization, or production security claim.

---

## 1. Executive conclusion

### 1.1 Decision

State whether a one-transaction, post-quantum-oriented, witness-hiding Tornado Classic withdrawal is supported by the evidence.

### 1.2 Best measured candidate

| Metric | Result | Gate | Status |
|---|---:|---:|---|
| Candidate ID | | | |
| Accepted security | | ≥100 bits | |
| Lowest security term | | | |
| Raw proof bytes | | | |
| Exact ABI calldata | | ≤80 KiB | |
| Current-schedule tx gas | | ≤14.0M | |
| 64/64-scenario tx gas | | ≤14.0M | |
| 96/96-scenario tx gas | | ≤14.0M | |
| Deposit gas | | ≤4.0M | |
| Largest runtime | | ≤22,000 B | |
| Largest deployment tx | | ≤14.0M | |
| Prover p50, H2 | | ≤120 s | |
| Prover p95, H2 | | ≤180 s | |
| Peak RSS, H2 | | ≤8 GiB | |
| ZK status | | required | |
| External cryptographic review | | required for qualification | |

### 1.3 Three largest unresolved risks

1. 
2. 
3. 

### 1.4 Recommended next action

Explain whether to draft a full engineering specification and what architecture it should use. Do not include the full specification here.

---

## 2. Scope and evidence boundary

Describe:

- what was implemented;
- what was only projected;
- what was reproduced independently;
- what was externally reviewed;
- what was not tested;
- and which conclusions are conditional.

---

## 3. Reproducibility manifest

### 3.1 Source commits

| Component | Repository | Commit/tag | Dirty? | License |
|---|---|---|---|---|

### 3.2 Toolchains

| Tool | Version | Installation hash/source |
|---|---|---|

### 3.3 Hardware

| Hardware ID | CPU | Cores | RAM | OS | Features | Purpose |
|---|---|---:|---:|---|---|---|

### 3.4 Execution clients

| Client | Commit/version | Fork config | Role |
|---|---|---|---|

### 3.5 Artifact manifest

Link every result to `evidence-manifest.json` and describe verification commands.

---

## 4. Baseline chronology

### 4.1 v0.1

Document the Keccak AIR, 2,633-column width, staged proof-data/fact route, 818-transaction result, and lessons.

### 4.2 v0.2

Document P2BB512, 230-column AIR, q48, and over-cap A/B gas.

### 4.3 v0.3

Document 190-column AIR, q32, proof bytes, gas, soundness figures, and blockers.

### 4.4 Baseline reproduction

| Metric | Engineering report | Reproduced p50 | Reproduced range | Delta | Explanation |
|---|---:|---:|---:|---:|---|

Include deployment gas, which the original report did not establish.

---

## 5. Security model and corrected v0.3 interpretation

### 5.1 Required claim

State the exact application-level PQ claim and Ethereum boundary.

### 5.2 Independent soundness calculator

Document formulas, implementation, review, and cross-checks.

### 5.3 v0.3 term-by-term table

| Term | Model | Bits | Proven/conjectural | Batch term? | Multi-target? | Notes |
|---|---|---:|---|---|---|---|

### 5.4 Conjectural batch-term omission

Explicitly explain whether and how `num_batched_functions` enters each model.

### 5.5 Continuation-binding security

Analyze statement/global/checkpoint/proof IDs and the required hash property.

### 5.6 QROM and zero-knowledge status

Separate theorem, assumption, implementation evidence, and open questions.

---

## 6. Common benchmark corpus

Describe semantic cases, candidate derivation, invalid mutations, proof count, and artifact paths.

| Corpus class | Cases | Candidate coverage | Notes |
|---|---:|---:|---|

---

## 7. Application hash and compression experiments

### 7.1 Candidate definitions

| Candidate | Field | Width | Mode | Digest fields | Node permutations | Note permutations | Security status |
|---|---|---:|---|---:|---:|---:|---|

### 7.2 Cross-language correctness

### 7.3 Solidity and native performance

| Candidate | Perm gas | Node gas | 20-level compute | Full deposit | Constructor | Rust hashes/s |
|---|---:|---:|---:|---:|---:|---:|

### 7.4 Security/cryptanalysis

| Candidate | Generic quantum collision | Structural attack floor | Mode review | Reviewer | Result |
|---|---:|---:|---|---|---|

### 7.5 Gate results and selection

Include all rejected candidates.

---

## 8. Merkle and deposit experiments

Cover tree arity, depth/capacity, digest width, zero-tree initialization, root history, direct insertion, and batched root transitions.

---

## 9. AIR geometry experiments

### 9.1 Geometries

| AIR ID | Rows | Width | Max degree | Quotient chunks | Batched functions | Active perms | Proof bytes | AIR/DEEP gas |
|---|---:|---:|---:|---:|---:|---:|---:|---:|

### 9.2 Lane-parallelism sweep

### 9.3 Constraint coverage and mutation results

### 9.4 Selected relation

---

## 10. Transcript, continuation, verifier, and codec experiments

### 10.1 Challenge-boundary graph

### 10.2 Transcript candidates

| ID | Keccak calls | Bytes hashed | Transcript gas | Full-path delta | Binding width | Result |
|---|---:|---:|---:|---:|---:|---|

### 10.3 Verifier optimization deltas

| Optimization | Exec delta | Calldata delta | 64/96 effect | Code delta | Assumption | Keep? |
|---|---:|---:|---:|---:|---|---|

### 10.4 Worst-case frontier analysis

---

## 11. Field and extension bakeoff

| Field stack | Base B | Ext B | Challenge bits | Arithmetic gas | Proof B | Prover p50 | EVM total | Security ceiling | Result |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|

---

## 12. Hiding FRI Pareto sweep

### 12.1 Filtered parameter space

### 12.2 Security frontier

### 12.3 Performance frontier

| Profile | q | Blowup | Fold schedule | Final size | Grinding | Security | Proof B | Prove p50 | Tx gas |
|---|---:|---:|---|---:|---|---:|---:|---:|---:|

### 12.4 One-/two-transaction conclusion

---

## 13. HVZK-WHIR

Document upstream commit, ZK implementation mapping, simulator tests, parameters, proof bytes, prover, EVM verifier, code size, and gate result.

---

## 14. STIR and Circle readiness

Keep non-hiding results clearly marked `BENCHMARK_ONLY`.

---

## 15. Structured Spartan-WHIR

### 15.1 External reference reproduction

### 15.2 PQTC relation

### 15.3 Hiding path

### 15.4 EVM result

---

## 16. Recursive proof compression

| Inner | Outer | Layers | Outer proof B | Prove p50 | RSS | Tx gas | Security | ZK argument | Result |
|---|---|---:|---:|---:|---:|---:|---:|---|---|

---

## 17. Flock and lightweight ZK compilation

Include batch-size 44 results, complete glue size, ZK status, VEIL/other overhead, EVM route, and stop/pass result.

---

## 18. Aggregation and batch withdrawals

| N | Aggregate proof B | Settlement gas | Gas/withdrawal | Prove latency | Batch latency | Privacy model | Result |
|---:|---:|---:|---:|---:|---:|---|---|

---

## 19. Robust two-transaction state machine

Cover one-active-checkpoint keying, expiry, cleanup, root pinning, full-width bindings, split sweep, and attack tests.

| Split | A current | B current | A 96 | B 96 | Total | Min margin | Result |
|---|---:|---:|---:|---:|---:|---:|---|

---

## 20. L2 and economic results

Distinguish application cryptography from rollup/bridge/sequencer assumptions.

---

## 21. Prover UX and portability

| Candidate | Hardware | Threads | Cold p50 | Warm p50 | p95 | RSS | Native verify | Notes |
|---|---|---:|---:|---:|---:|---:|---:|---|

---

## 22. Advisory applicability matrix

| Advisory | Upstream affected path | Pinned status | Custom path | Regression test | Result | Residual risk |
|---|---|---|---|---|---|---|

---

## 23. Candidate master table

| Candidate | Hash | Relation | PCS | ZK | Accepted security | Proof B | Tx current | Tx 64 | Tx 96 | Deposit | Prove H2 p50 | RSS | Max runtime | Gate |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|

---

## 24. Pareto frontiers and sensitivity

Include plots and machine-readable data. Discuss dominated candidates and weight sensitivity.

---

## 25. One-transaction feasibility conclusion

State one of:

- demonstrated;
- credible but one narrow blocker remains;
- not demonstrated under current candidates;
- or ruled out for the tested lineage.

Justify with complete transaction and security evidence.

---

## 26. Robust two-transaction conclusion

---

## 27. Recommended next-build architecture

Only include this section when recommendation is `RECOMMEND_FULL_ENGINEERING_PLAN` or `RECOMMEND_ROBUST_TWO_TX_BUILD`.

State:

- selected application hash and exact mode;
- digest and tree;
- relation geometry;
- field;
- proof backend;
- transcript;
- verifier shape;
- transaction lifecycle;
- target profile;
- expected metrics;
- and unresolved decisions that the engineering plan must close.

Do not silently make choices unsupported by the spikes.

---

## 28. Rejected and deferred candidates

| Candidate | Last stage | Failure class | Evidence | Revival condition |
|---|---|---|---|---|

---

## 29. Unresolved questions

Number each question and assign an owner or external dependency.

---

## 30. Raw evidence index

List every run directory, proof corpus, gas trace, source hash, external baseline reproduction, and review artifact.

---

## 31. Reproduction commands

Provide clean-machine commands and expected hashes/results.

---

## 32. Sign-off

| Role | Name/identity | Scope | Commit reviewed | Date | Result |
|---|---|---|---|---|---|
| Research lead | | | | | |
| Cryptography reviewer | | | | | |
| AIR/relation reviewer | | | | | |
| Solidity reviewer | | | | | |
| Independent reproducer | | | | | |

