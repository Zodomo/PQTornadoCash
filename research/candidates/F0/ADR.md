# ADR: F0 remains research-only

## Context

SP-40 reopens the field stack without changing the frozen v0.3 custody protocol. Pinned p3-baby-bear implements the degree-four binomial extension and multiplicative two-adic DFT/FRI path used by the frozen UniSTARK baseline. Pinned default BabyBear Poseidon2 width 16/24/32 constructors and known-answer tests are present.

## Decision

Retain F0 as `BENCHMARK_ONLY`. The native output is classified `DIAGNOSTIC_NOT_COMMON_PROTOCOL`: it has no common-protocol corpus distribution or warmup phase, and scalar samples can be timer-overhead-scale. It may prove executability only; cross-candidate ranking and nondominance use are prohibited. The isolated Solidity gas output is likewise not a complete verifier result. Do not integrate this field into the prover, proof codec, verifier, or contracts.

## Protocol-layer disposition

`manifest.json.protocolLayerMatrix` explicitly lists every frozen or investigated layer. No unlisted layer is silently inherited or changed. Only the candidate field arithmetic is measured in isolation; even that alternative is not integrated.

## Gate

The candidate advances only if it is nondominated across common-protocol complete proof bytes, total EVM execution gas, prover time, soundness ceiling, and implementation maturity. Those dimensions are not available here, so the gate is not passed and Pareto rank is unassigned. No complete-proof result is claimed.

## Consequences

- Deterministic arithmetic vectors and 64/96-row encoding floors remain valid non-timing evidence.
- A later common-protocol run must define distributions, warmup, repetition policy, and a ported relation/backend before timing comparison.
- Unsupported PCS or parameter paths stop with source-backed reasons in `source-evidence.json`; no local constants are invented.
