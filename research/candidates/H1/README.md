# H1: Width-16 d=7 feed-forward negative control

**Status: `BENCHMARK_ONLY`. Custody/deployment eligibility: none.**

## Definition

Trunc_7(Poseidon2_BabyBear_16(x)+x), first seven lanes

## Application decision

Stopped: two children require 14 lanes and four separate controls require 18 > 16.

Layout: Primitive vectors reserve the final four lanes for role/version/shape/level experiments. No application encoding is defined.

## Decision

Measure as a negative control; it cannot pass the mixer gate. The Stage A result is `FAIL`. Exact blockers are retained in `security/manifest.json`; benchmark speed cannot remove them.

## Commands

Use the common one-command entry points: `python3 research/candidates/hash-compression-common/run.py vectors-parity` and `python3 research/candidates/hash-compression-common/run.py benchmark --samples 1000`.
