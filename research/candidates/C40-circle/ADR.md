# ADR — Keep pinned CirclePcs on a no-code watch

## Decision

At the pinned Plonky3 commit, verify from an exact-hash clean checkout that `CirclePcs` implements `Pcs`, requires `Val: ComplexExtendable`, sets `ZK = false`, and exposes no `HidingCirclePcs` adapter. Emit a machine-readable source-watch result and write no native adapter.

## Why no lower-bound run

A non-hiding lower bound is permissible only when comparable without inventing relation glue. C20 and C30 use the same BabyBear/quartic 4,096-element proxy. Pinned CirclePcs cannot use that BabyBear/two-adic geometry because its value field must be `ComplexExtendable`. No SP-10 relation was accepted, so translating frozen H0 into a Circle-field relation would be unauthorized new relation work rather than a matched backend observation.

## Promotion gate

C40 remains `DEFERRED` until public pinned code simultaneously supplies a working hiding native prover/verifier, a documented noninteractive hiding construction and exact transcript argument, a compatible accepted application relation, and a credible matching EVM path. The current source watch clears none of the missing privacy or integration requirements and produces no measurement.
