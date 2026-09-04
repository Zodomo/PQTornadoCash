# H4: Width-24 d=11 primitive with documented layout failure

**Status: `BENCHMARK_ONLY`. Custody/deployment eligibility: none.**

## Definition

Trunc_11(Poseidon2_BabyBear_24(x)+x), first eleven lanes

## Application decision

Stopped: two children require 22 lanes and four controls require 26 > 24.

Layout: Primitive only. There is no application layout.

## Decision

Execute the valid primitive benchmark; retain the one-call node failure. The Stage A result is `PRIMITIVE_ONLY_LAYOUT_FAIL`. Exact blockers are retained in `security/manifest.json`; benchmark speed cannot remove them.

## Commands

Use the common one-command entry points: `python3 research/candidates/hash-compression-common/run.py vectors-parity` and `python3 research/candidates/hash-compression-common/run.py benchmark --samples 1000`.
