# ADR: F1 remains research-only

## Context

SP-40 reopens the field stack without changing the frozen v0.3 custody protocol. Pinned p3-koala-bear implements the degree-four binomial extension and the generic p3-dft/p3-fri multiplicative-domain interfaces. Pinned default KoalaBear Poseidon2 width 16/24/32 constructors and known-answer tests are present.

## Decision

Retain F1 as `BENCHMARK_ONLY`. Run the shared native and Solidity kernels and compare the resulting evidence, but do not integrate this field into the prover, proof codec, verifier, or contracts. `vectors.json` is deterministic arithmetic evidence, not a proof measurement.

## Gate

The candidate advances only if it is nondominated across complete proof bytes, total EVM execution gas, prover time, soundness ceiling, and implementation maturity. Those dimensions are not all available in SP-40, so the gate is not passed and Pareto rank is unassigned. No complete-proof result is claimed.

## Consequences

- Canonical encoding and 64/96-row floors can be compared now.
- A later relation/backend spike must port and prove the selected geometry before any total-cost claim.
- Unsupported PCS or parameter paths stop with the source-backed reasons in `source-evidence.json`; no local constants are invented.
