# H2: Width-16 wide-output construction stop

**Status: `DEFERRED`. Custody/deployment eligibility: none.**

## Definition

No executable primitive: no published/reviewed multi-permutation width-16 Poseidon2 wide-output mode was found.

## Application decision

All roles stopped.

Layout: None. Absence of a layout is the required result.

## Decision

No code. Do not concatenate truncations, repeat permutations, chain states, or invent feed-forward. The Stage A result is `STOPPED_NO_REVIEWED_MODE`. Exact blockers are retained in `security/manifest.json`; benchmark speed cannot remove them.

## Commands

Use the common one-command entry points: `python3 research/candidates/hash-compression-common/run.py vectors-parity` and `python3 research/candidates/hash-compression-common/run.py benchmark --samples 1000`.
