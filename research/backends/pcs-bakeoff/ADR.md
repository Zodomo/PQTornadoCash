# ADR — Aggregate controls without ranking candidates

## Decision

Validate and summarize the retained C20, C30, and C40 focused results, but do not rank proof bytes, time, or RSS as PQTC results. Require the exact shared Plonky3 pin, C20 hiding/two-proof verification, C30 compiled non-hiding verification, C40 no-code source-watch disposition, and false `pqtc_measurement` flags.

## Comparability boundary

C20 and C30 deliberately share BabyBear/quartic, 4,096 public polynomial elements, and one opening point. This is sufficient to identify their upstream smoke geometry, not to claim a security-matched benchmark or complete relation comparison. C40 cannot share that geometry through pinned `CirclePcs` without a new field/relation translation.

Frozen v0.3/H0 remains the sole relation control after SP-10 accepted no compression candidate. None of the candidate outputs implements its fixed-denomination withdrawal semantics, binary depth-20 P2BB512-v1 tree, 256×190 AIR, full statement binding, or common corpus.

## Disposition

The bakeoff produces no privacy finalist and no candidate eligible for PQTC ranking. C20 is `DEFERRED`, C30 is `BENCHMARK_ONLY`, and C40 is `DEFERRED` with `NO_CODE`.
