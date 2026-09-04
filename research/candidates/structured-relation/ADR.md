# ADR: Preserve the repeated-block design, but perform no conversion

## Status

`STOPPED_BY_DEPENDENCY`. The intended schema is recorded for review; it is not code and no AIR, R1CS, CCS, or Boolean conversion was attempted.

## Context

SP-21 requires the SP-10 finalist. Every H0–H7 status has `gateComparison.airDisposition = STOPPED` and `allPass = false`, so no application-compression primitive may enter relation work.

The frozen v0.3 reference nevertheless identifies the semantic shape to preserve: one nullifier application hash, one note-commitment application hash, and twenty level-bound Merkle-node application hashes. This is 22 application invocations joined by twenty path-order selections, leaf-index/path consistency, nullifier equality, root equality, and public-statement binding. In the current rate-four Poseidon2 sponge those invocations expand to 240 permutation rows; that expansion is baseline evidence, not a proposed repeated-block implementation.

Backend source research does not fill the dependency gap. The pinned generic Spartan-WHIR surface accepts ordinary R1CS shape/matrices and exposes no PQTC repeated-block API or metadata contract. Current Flock removed its application Keccak encoder and proof-benchmark consumers at the pinned removal commit; a residual low-level Keccak benchmark file is not an end-to-end relation API. Neither source justifies claiming that PQTC repetition survives compilation.

## Decision

1. Encode only the intended reusable block `F`, 22 instance descriptors, glue relation `G`, and public/private partition.
2. Mark AIR, R1CS, CCS, and Boolean conversions `NOT_ATTEMPTED_BY_GATE`; publish no variable, constraint, nonzero, glue, memory-offset, proof, time, RSS, or gas counts.
3. Require a backend API to preserve shared-`F` identity, explicit instance metadata, instance I/O, glue, and public/private labels through setup, proving, verification, and serialization.
4. Stop on flatten-only APIs, lost repetition metadata, missing structured-versus-expanded counts, unbounded expansion, missing corpus equivalence, or failure to mutate both repeated-block and glue witnesses.
5. Do not revive historical Flock Keccak as a current API and do not describe generic Spartan/WHIR R1CS support as structured PQTC support.

## Consequences

No relation implementation or backend adapter exists in this package. `check.py` validates the honest stopped state and exact dependency evidence. `check.py --require-eligible` exits with code 3 until an upstream SP-10 status explicitly becomes eligible, preventing an automated conversion from starting from H0 or a stopped H candidate.
