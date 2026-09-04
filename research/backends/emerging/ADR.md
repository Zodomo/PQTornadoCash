# ADR — Retain only labeled upstream controls for C50, C60, and C70

Research cutoff: **2026-09-04**.

## Decision

Package exact-pin upstream source checks and reproduction commands without integrating any emerging backend. The frozen v0.3/H0 relation remains the only faithful relation control.

- C50 native full-ZK Spartan-WHIR is `PASS` only for upstream implementation maturity. Pinned standalone-WHIR Solidity build/tests pass, but the exact gas script is `UNEXECUTABLE_UPSTREAM_HARNESS_AT_PIN` and gas is `NOT_EVALUATED`. The exact PQTC relation is absent, licensing blocks vendoring, and full EVM Spartan is `DEFERRED`.
- C60 recursion is `DEFERRED`. Only the true `recursive_fibonacci --zk` upstream architecture smoke is retained; toy Fibonacci is never PQTC.
- C70 Flock is `STOP`. Its exact historical Keccak command is `UNEXECUTABLE_AT_PIN/FAIL`: the pin has no Ligerito `m21_fast` security config, so no batch-44 number was produced. VEIL over Flock is `DEFERRED` because the inspected PoC adapter does not match Flock.

## Reproducibility boundary

Runners clone exact commits into an external workspace, verify `HEAD`, reject tracked changes, hash inspected source files, and preserve command logs and a machine-readable result. They do not vendor upstream source, alter the frozen relation/corpus, design a hiding construction, prove a transcript theorem, port Plonky3 versions, create a VEIL/Flock adapter, or implement an EVM verifier.

Upstream claims and historical harness semantics cannot qualify a candidate. Upstream-only baselines carry `UPSTREAM_BASELINE_NOT_PQTC`; failed local command records distinguish their origin and disposition from unexecuted upstream claims.
