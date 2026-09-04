# ADR — Keep STIR as a non-hiding lower bound

## Decision

Compile pinned Plonky3 `TwoAdicStirPcs` and execute one complete commit/open/verify lifecycle on the same public polynomial geometry used by C20: BabyBear, quartic extension, 4,096 values, width one, and one opening point. Assert through the compiled `Pcs` API that `ZK` is `false`. Record proof bytes, phase wall times, and process peak RSS.

The result is `BENCHMARK_ONLY` and must always carry `UPSTREAM_BASELINE_NOT_PQTC`. It cannot be a privacy finalist.

## Relation boundary

No compression candidate passed SP-10, so frozen v0.3/H0 is the only faithful control. That control includes the complete fixed-denomination withdrawal semantics, binary depth-20 P2BB512-v1 tree, 16-field digest, 256×190 degree-seven AIR, and binding of scope, root, nullifier, recipient, relayer, and fee. The polynomial-opening proxy implements none of these requirements and does not use the frozen common corpus.

## Rejected alternatives

- Inferring zero knowledge from nondeterministic proof bytes: rejected; the compiled API says `ZK=false`.
- Adding local blinding or adapting HVZK techniques: rejected; that would invent a hiding construction outside the authoritative source landscape.
- Calling the proxy a PQTC measurement: rejected; its only valid interpretation is a non-hiding upstream lower bound.
