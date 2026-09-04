# Assumptions and evidence classes

## Frozen geometry

The study treats the v0.3 production shape as fixed by source: 32 transcript queries split in order into two 16-query halves; proof degree bits 9; log blowup 4; height-13 input MMCS trees; three input batches with `(matrix count, row width)` equal to `(1, 8)`, `(1, 194)`, and `(16, 8)`; nine binary FRI rounds of heights 12 through 4; four random codewords; eight salt fields per opened matrix row; and 64-byte MMCS digests.

A query position may collide with another position. Frontier calculations operate on the set of distinct indices exactly as `BTreeMap`/`BTreeSet` do in `query.rs`; duplicate positions still retain their opened-row, salt, sibling-value, and index bytes.

## Evidence labels

| Label | Meaning in this package |
|---|---|
| `MEASURED` | A retained byte artifact, byte distribution, trace-log gas value, or frozen baseline summary value was read directly. |
| `EXACT_DERIVED` | A value follows from the frozen codec/query algorithms and was checked against every parsed artifact or by exhaustive tree dynamic programming. |
| `PROJECTION` | A proposed 64/96-gas-per-byte schedule or a byte-only theoretical-extreme floor; it is not active-network or measured execution evidence. |
| `NOT_EVALUATED` | Required evidence is absent and no surrogate is substituted. |

## Gas assumptions

For full retained ABI calldata, `z` and `n` are counted from the exact files. Standard intrinsic is `21000 + 4z + 16n`; the active EIP-7623 floor is `21000 + 10z + 40n`; uniform scenarios are `21000 + 64(z+n)` and `21000 + 96(z+n)`. Access lists and authorizations are absent from these ordinary-call fixtures.

The trace-log execution value is combined only with the same retained call's standard intrinsic, then compared with its active floor. No observed execution value is attached to a synthetic minimum or maximum frontier. For theoretical byte extrema, standard and active floors are therefore bounded by all-zero/all-nonzero calldata intervals; uniform 64/96 floors are exact byte-only projections.

The engineering-report directory retains the canonical raw proof parts but not their full ABI calldata. Its reported execution, intrinsic, and total values are preserved as report measurements and are not reconstructed from raw proof bytes.

## Bound domain

The exact extrema range over every query-index sequence the v0.3 transcript can encode: 16 positions per half, each in `[0, 8192)`, with collisions permitted. The full checkpoint has at most 32 unique indices. The result is a proof-codec/MMCS size bound, not a soundness, security, deployment, or production qualification.
