# H6: Width-32 d=14 conservative comparator

**Status: `BENCHMARK_ONLY`. Custody/deployment eligibility: none.**

## Definition

Trunc_14(Poseidon2_BabyBear_32(x)+x), first fourteen lanes

## Application decision

The primitive/layout microbenchmark places 28 generic payload lanes followed by four controls. Its note and nullifier labels do not make the payloads protocol-complete: scope and frozen semantic secret/trapdoor widths are absent.

Layout exercise: lanes 0..27 generic payload; 28 role; 29 version; 30 shape=28; 31 level.

## Decision

Use d=14 as the conservative-output comparator; d=15 is rejected because controls do not fit. The Stage A result is `NOT_EVALUATED_FULL_SOLIDITY_PARITY_AND_MISUSE`. Exact blockers are retained in `security/manifest.json`; benchmark speed cannot remove them.

## Commands

Use the common one-command entry points: `python3 research/candidates/hash-compression-common/run.py vectors-parity` and `python3 research/candidates/hash-compression-common/run.py benchmark --samples 1000`.
