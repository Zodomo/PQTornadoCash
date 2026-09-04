# ADR: deterministic section-19 sensitivity with no finalists

## Status

Accepted for the research snapshot. Operational model only; no deployment or cryptographic acceptance decision.

## Context

Section 19 requires economic and throughput calculations for every finalist, but the committed program state has zero finalists and no security-qualified candidate. The repository nevertheless contains useful frozen v0.3 baseline distributions, exact two-call calldata, gas-schedule results, H1 warm prover measurements, aggregation dependency failures, and synthetic L2 studies. Reporting those measurements as a finalist would bypass mandatory gates. Mixing a live price or synthetic fee assumption into cryptographic scoring would also be incorrect.

## Decision

1. Emit `finalist_count: 0`, an empty `finalists` array, `VACUOUS_NO_FINALIST_ROWS_EXIST`, and `NOT_APPLICABLE_NO_FINALIST`.
2. Include exactly one baseline/control row labeled `NON_FINALIST_CONTEXT`. Preserve `security_qualified: false`, `gate_status: FAIL`, and `NOT_COMPUTED_NON_FINALIST`; prohibit a passing weighted result.
3. Recompute active 10/40, scheduled-unactivated standalone 64/64, and unscheduled-draft standalone 96/96 calldata floors from exact Part A and Part B bytes. Retain each schedule's lifecycle label and never call 64/64 or 96/96 active.
4. Treat a complete baseline withdrawal as the ordered Part A plus Part B pair. Report p50 block share and exact observed-sample packing witnesses at synthetic 30M, 36M, and 60M block limits. Do not present arithmetic packing as a receipt, scheduler benchmark, or live-chain capacity.
5. Calculate wei and ETH sensitivity at the six required effective-gas-price points using exact rational/decimal arithmetic. Do not fetch prices. Emit USD only when an offline configuration supplies a timestamped local price artifact and matching SHA-256.
6. Derive only sequential warm H1 rates from measured wall times. Leave H1 cold/NEON, H2, H3, and concurrent capacity unevaluated.
7. Publish the relayer formula and gas-only lower bound, but retain full break-even as `NOT_EVALUATED` until all operational fee, denomination, risk/capital, machine-price, and conversion inputs are supplied.
8. Pin every source record and validate exact calldata hashes, CSV/run agreement, gas formulas, and finalist invariants before output.

## Consequences

The result is reproducible and useful for sensitivity comparisons without promoting the failed baseline. A p50 two-call baseline exceeds a synthetic 30M block, while one low-gas observed eligible pair does fit; the output retains both facts rather than collapsing them into a single capacity claim. Nine Part A records remain invalid under the active $2^{24}$ transaction cap. Alternate standalone calldata floors do not bind any retained call and therefore do not change the measured gas distribution.

The package intentionally has no USD example, full relayer fee, live-chain fee, L2 verifier receipt, aggregation performance, H2/H3 throughput, or security acceptance result. A future finalist must receive its own measured row rather than inheriting this control row.
