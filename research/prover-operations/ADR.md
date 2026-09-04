# ADR: Bound SP-73 to committed operational evidence

## Status

Accepted for this research checkpoint. The SP-73 gate is `FAIL`.

## Context

SP-73 requires complete H1, H2, and H3 measurement plus a practical CLI workflow. Its platform matrix includes Apple ARM64/NEON, commodity x86-64/AVX2, high-end x86-64/AVX-512, a scalar/portable build, and optional WASM. Its workflow matrix includes cold and warm proof generation, setup/precomputation, cancellation, progress, memory pressure, disk, crash recovery, and serialization/upload.

The available evidence is narrower: 60 schema-valid frozen v0.3 baseline records, all marked `WARM`, and one H1 continuity hardware profile. The records contain wall/proof/native-verification time, peak RSS, proof/calldata bytes, and eight retained artifacts apiece. The profile marks H2 and H3 unavailable. No candidate is a finalist or security-qualified.

## Decision

1. Treat the 60 records as an H1 warm distribution only. A first item in a batch is not relabeled cold: every source says `WARM`.
2. Match the run hardware to the H1 profile only on recorded architecture, CPU model, core counts, and RAM. The differing hardware identifiers are retained. The profile proves NEON hardware capability, but the empty run-level CPU feature lists do not prove that a NEON-specific code path executed.
3. Validate every input against `benchmark-run.schema.json`, require the exact 30 corpus plus 30 fixed run IDs and baseline commit, validate byte-accounting invariants, and verify the size and SHA-256 of all 480 declared artifacts.
4. Report exact source decimal spellings. Use nearest-rank p90/p95/p99. Compute mean and population standard deviation with decimal arithmetic, rounding half-even to 12 decimal places. This avoids binary-float-dependent output.
5. Treat the sum of verified retained artifacts as measured retained disk usage, not peak workspace usage. Temporary files, build/precomputation caches, and peak free-space requirements remain `NOT_EVALUATED`.
6. Treat raw A+B proof bytes and A+B ABI calldata bytes as measured serialization/upload payload sizes. Serialization time, upload time, transport, retries, and network behavior remain `NOT_EVALUATED`.
7. Record `trusted_setup=false` without converting it into zero setup or precomputation time.
8. Publish an end-user CLI contract as `SPECIFICATION_ONLY_NOT_IMPLEMENTED`. The existing batch research generator is not credited as a practical product workflow.
9. Keep H2, H3, scalar, AVX2, AVX-512, WASM, cancellation, progress, memory-pressure behavior, and crash recovery explicitly `NOT_EVALUATED`.
10. Keep service isolation, attestation, and production local fallback open. A cross-user aggregator may receive proofs and public statements only, never witnesses.

## Consequences

The retained analyzer is deterministic and fails on missing/extra run IDs, schema drift, source pin drift, artifact mutation, accounting inconsistency, output drift, or a result that no longer says `FAIL`. It does not run a prover and cannot turn incomplete evidence into platform or workflow claims.

The package supplies an exact next-measurement procedure and a CLI/privacy contract, but neither earns gate credit until implementations and measurements are retained. H2/H3 completeness and the practical CLI are hard blockers. External cryptographic acceptance remains open, and this operational study does not select or qualify a candidate.
