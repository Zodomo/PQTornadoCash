# H5: Width-32 d=12 unified research hypothesis

**Status: `BENCHMARK_ONLY`. Custody/deployment eligibility: none.**

## Definition

Trunc_12(Poseidon2_BabyBear_32(x)+x), first twelve lanes

## Application decision

The primitive/layout microbenchmark places 24 generic payload lanes, four controls, and four fixed zero lanes. Its note and nullifier labels do not make the payloads protocol-complete: scope and frozen semantic secret/trapdoor widths are absent.

Layout exercise: lanes 0..23 generic payload; 24 role; 25 version; 26 shape=24; 27 level; 28..31 fixed zero.

## Decision

Highest-priority research hypothesis; never security-qualified by this package. The Stage A result is `PASS_STAGE_A_BENCHMARK_ONLY`. Exact blockers are retained in `security/manifest.json`; benchmark speed cannot remove them.

## Commands

Use the common one-command entry points: `python3 research/candidates/hash-compression-common/run.py vectors-parity` and `python3 research/candidates/hash-compression-common/run.py benchmark --samples 1000`.
