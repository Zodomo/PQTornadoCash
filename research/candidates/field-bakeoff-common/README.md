# SP-40 field bakeoff harness

This directory is research-only. It does not change the frozen v0.3 prover, verifier, proof codec, or deployed contracts. Every report emitted by the runners sets `benchmarkOnly: true` and `completeProofClaimed: false`.

## Native command

From the repository root:

```sh
cargo run --release --locked --manifest-path research/candidates/field-bakeoff-common/native/Cargo.toml -- --iterations 64 --rows 256 --columns 190 --out research/candidates/field-bakeoff-common/outputs/native-latest.json
```

`--rows` and `--columns` are the parameterized relation geometry inputs. The defaults reproduce the frozen 256-row, 190-column v0.3 geometry. An SP-20-selected geometry may be supplied explicitly; the runner does not label any geometry “best” on its own.

The emitted native timings are classified `DIAGNOSTIC_NOT_COMMON_PROTOCOL`. The run has zero warmup iterations, uses the local deterministic mixer rather than the common-protocol corpus distribution, and includes scalar samples at timer-overhead scale. It proves that the kernels execute; it MUST NOT be used for project-comparable performance ranking, nondominance, or a field-selection gate.

## Solidity command

From the repository root:

```sh
python3 research/candidates/field-bakeoff-common/solidity/run_bench.py --out research/candidates/field-bakeoff-common/outputs/solidity-latest.json
```

The wrapper runs the isolated Foundry test with solc 0.8.30, Prague, optimizer 200, and via-IR, verifies that all 162 expected measurements were emitted, and writes machine-readable gas evidence. Gas deltas include deterministic input construction and the external kernel call. They exclude transaction intrinsic gas and calldata pricing.

## Relation projections

Regenerate the frozen 190-column encoding floors:

```sh
python3 research/candidates/field-bakeoff-common/project.py
```

For the selected SP-20 geometry, pass numeric overrides, for example `--geometry-key bestSp20GeometryInput --rows 512 --columns 128 --opened-rows 64 96`. The numbers in that example are inputs, not a claimed SP-20 winner. Arithmetic projection remains symbolic until an alternate-field relation port supplies exact operation counts; reusing BabyBear implementation counts would fabricate a result.

## Deterministic vectors

Regenerate all candidate vectors without randomness:

```sh
python3 research/candidates/field-bakeoff-common/generate_vectors.py
```

The Rust and Solidity runners use the same wrapping-u64 input mixer and the same coefficient order. `vectors/all.json` and each `F*/vectors.json` are generated artifacts, not timing claims.

## Scope boundaries

The native runner exercises identical base/extension arithmetic, extension-by-base, dot products, base and extension batch inversion, Horner evaluation, and a binary FRI fold for F0–F5. It also invokes pinned Plonky3 FFT/LDE and default Poseidon2 constructors where those exact APIs exist. F4 uses the pinned complex FFT path. These are diagnostic smoke measurements, not common-protocol benchmarks. PCS commit/open/verify is deliberately not instantiated: the pinned PCS APIs are generic and SP-40 does not freeze a hash/MMCS/transcript/PCS parameter tuple. Selecting one here would be a protocol change rather than a field microbenchmark. The report records process-wide peak RSS and 1/2/4-thread dot-product scaling; thread creation is included, and neither value is represented as a complete prover resource measurement.

The Solidity kernels use `addmod`/`mulmod`, canonical coefficient inputs, big-endian fixed-width raw encoding, and ordinary ABI dynamic-array encoding. They are intentionally isolated from production sources.
