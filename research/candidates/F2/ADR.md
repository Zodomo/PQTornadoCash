# ADR: F2 remains research-only

## Context

SP-40 reopens the field stack without changing the frozen v0.3 custody protocol. Pinned p3-field exports QuinticTrinomialExtensionField and pinned p3-koala-bear implements x^5+x^2-1 arithmetic, Frobenius data, and a two-adic extension generator; generic FRI traits can use it after a complete configuration is selected. The application permutation remains the pinned KoalaBear base-field Poseidon2; no separate extension permutation is required by this microbench.

## Decision

Retain F2 as `BENCHMARK_ONLY`. Run the shared native and Solidity kernels and compare the resulting evidence, but do not integrate this field into the prover, proof codec, verifier, or contracts. `vectors.json` is deterministic arithmetic evidence, not a proof measurement.

## Gate

The candidate advances only if it is nondominated across complete proof bytes, total EVM execution gas, prover time, soundness ceiling, and implementation maturity. Those dimensions are not all available in SP-40, so the gate is not passed and Pareto rank is unassigned. No complete-proof result is claimed.

## Consequences

- Canonical encoding and 64/96-row floors can be compared now.
- A later relation/backend spike must port and prove the selected geometry before any total-cost claim.
- Unsupported PCS or parameter paths stop with the source-backed reasons in `source-evidence.json`; no local constants are invented.
