# Section 19 economic and throughput model

This package implements the deterministic operational-sensitivity model required by section 19 of `PQTC_NEXT_GENERATION_RESEARCH_PLAN.md`.

## Decision status

- `finalist_count = 0`; no finalist rows exist.
- The every-finalist obligation is therefore vacuous and the finalist gate is `NOT_APPLICABLE_NO_FINALIST`.
- `C00/v03-baseline` is retained only as `NON_FINALIST_CONTEXT`. It is not security-qualified, its gate is `FAIL`, and it receives `NOT_COMPUTED_NON_FINALIST` rather than a passing weighted result.
- External cryptographic acceptance remains `OPEN`. This package does not change a cryptographic gate.

## Canonical result

`outputs/results.json` is generated from 60 exact committed v0.3 run records, 120 calldata artifacts verified against the SHA-256 values embedded in those records, the baseline distribution, aggregation output, L2 output, prover-operations output, and gas-rule evidence. `source-hashes.json` pins all 70 source records. The model validates the pins and cross-checks the CSV against each run before producing output.

All arithmetic uses Python `Decimal` and `Fraction`; binary floating-point is not used. Finite values are emitted as exact decimal strings. Repeating values retain an exact reduced fraction plus an explicitly labeled rounded decimal.

The baseline's active-schedule linear-interpolated p50 gas is:

| Path | Gas | ETH at 0.1 gwei | ETH at 50 gwei |
|---|---:|---:|---:|
| Part A | 16,664,641.5 | 0.00166646415 | 0.833232075 |
| Part B | 13,959,759.5 | 0.00139597595 | 0.697987975 |
| complete two-call withdrawal | 30,621,386.5 | 0.00306213865 | 1.531069325 |

The output includes every required effective-gas-price point: 0.1, 0.5, 1, 5, 10, and 50 gwei. These are offline parameters, not observed base fees. Priority fees are included only if the caller treats the configured effective gas price that way.

## Gas schedules and block packing

For each exact Part A and Part B calldata payload, the generator recomputes the floor and checks the retained run result:

- active EIP-7623: $21{,}000 + 10z + 40n$;
- standalone EIP-7976 sensitivity: $21{,}000 + 64(z+n)$;
- standalone draft EIP-8311 sensitivity: $21{,}000 + 96(z+n)$.

The 64/64 schedule is scheduled but unactivated and the 96/96 schedule is an unscheduled draft as of the snapshot. Neither is labeled active, and neither is presented as the complete Amsterdam composition. No alternate floor binds in the 60 retained calls, so observed gas is unchanged across the three sensitivities.

Block limits of 30,000,000, 36,000,000, and 60,000,000 gas are explicit synthetic inputs, not live-chain observations. A completed withdrawal is modeled as both ordered calls in the same block. For each schedule and block limit the output reports:

1. exact p50 block share;
2. best-case maximum completed withdrawals found among transaction-cap-eligible records and its witness run;
3. calldata for that packing;
4. maximum calldata over all eligible observed packings; and
5. a capacity bound conservative only over the eligible observed sample.

At 30,000,000 gas the p50 pair consumes 102.071288333333% (rounded from the retained exact fraction), although the best eligible observed pair fits once. At 60,000,000 gas the best eligible observed pair fits twice. These are arithmetic packings, not live receipts, scheduler tests, or throughput claims. Nine of 60 Part A records exceed the active $2^{24}$ transaction gas-limit cap; all schedules retain `FAIL_OBSERVED_PART_A_EXCEEDS_CAP`.

## Prover throughput

Only H1 has measurements: 60 warm sequential Apple M4 Max runs. Summed wall time yields exactly `2000000000000000000/1207472823400166819` proofs/s, or 1.656351978480 proofs/s rounded to 12 decimal places. The reciprocal of median wall time is separately reported. Neither figure is a concurrent load test.

H1 cold timing and explicit NEON-path execution are `NOT_EVALUATED`. H2 and H3 are `NOT_EVALUATED_NO_COMMITTED_MEASUREMENTS`; no projection substitutes for those missing measurements.

## USD and relayer fees

No pinned ETH/USD price artifact exists, so canonical USD examples are `NOT_EVALUATED_NO_PINNED_PRICE_SOURCE`. To run a separate offline scenario, copy `assumptions.json`, populate all five `usd_example` fields, and provide a local source artifact whose SHA-256 matches `source_sha256`:

```sh
python3 research/economic-throughput/run.py \
  --config /path/to/offline-assumptions.json \
  --output-dir /tmp/pqtc-section19
```

The generated USD row is timestamped and source-pinned. It remains operational sensitivity and never enters a cryptographic gate.

The relayer model records:

```text
network_cost_wei = gas_used * effective_gas_price_wei + l2_fee_wei
full_break_even_wei = network_cost_wei
                    + non_gas_cost_wei
                    + capital_and_risk_cost_wei
                    + prover_cost_wei
fee_fraction = full_break_even_wei / withdrawal_denomination_wei
```

The canonical table supplies only the deterministic gas-only lower-bound sensitivity. Full break-even remains `NOT_EVALUATED_MISSING_OPERATIONAL_FEE_INPUTS` because L2/data fees, non-gas costs, capital/risk costs, withdrawal denomination, machine price, and pinned price conversion are absent. The lower bound is not a fee quote.

## Reproduction

```sh
python3 research/economic-throughput/run.py
```

The command fails on any source-pin, embedded calldata hash/length, gas-rule recomputation, distribution, candidate disposition, or finalist invariant mismatch. Intentional source changes require explicit pin regeneration:

```sh
python3 research/economic-throughput/run.py --refresh-source-hashes
```

Generated artifacts are `outputs/results.json`, `outputs/cost-sensitivity.csv`, and `status.json`. `result.schema.json` fixes the no-finalist and non-finalist-control invariants.
