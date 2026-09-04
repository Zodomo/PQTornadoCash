# SP-71 offline L2 admission and fee-model experiment

Snapshot: **2026-09-04**. This package is offline: it queried no public RPC, sent no testnet/mainnet transaction, used no production key, and reports no live price. `sources.json` pins the official inputs; `matrix.json` is the machine-readable rule matrix.

## Admission sweep and SP-71 product gate

The package-specific **`admission_sweep_gate=FAIL`** for an unchunked ordinary-sequencer design spanning 80–210 KiB. All selected networks are projected byte-admissible at 80 KiB. None admits the generated 210 KiB signed transaction on its ordinary sequencer path:

| Network / active rules | Chain ID | Exact ordinary signed-tx boundary | Per-tx gas rule | 80 KiB | 210 KiB |
|---|---:|---:|---:|---|---|
| OP Mainnet Karst | 10 | 131,072 bytes | 16,777,216 | projected size-admissible | source-proven size rejection |
| Arbitrum One ArbOS61 / Nitro v3.11.3 | 42,161 | 95,000 bytes | 32,000,000 | projected size-admissible | source-proven size rejection |
| Scroll Mainnet Feynman | 534,352 | 116,736 bytes | current header state; 10,000,000 explicit scenario | projected size-admissible | source-proven size rejection |

The comparison is against the **complete serialized signed EIP-1559 transaction**, not calldata alone. Deposit, delayed, enforced, and L1-message routes are distinct and are not inferred from ordinary-path behavior. A full-node launch is unnecessary after the 210 KiB source-proven size rejection; faithful local admission errors/receipts for below-limit cases remain an independent reproduction task.

This is not the SP-71 product-gate result. The separate `SP71_product_gate`, which requires at least 90% user-cost improvement plus preserved application semantics, is **`NOT_EVALUATED_NOT_PASSED`**. Exact selected-L2 verifier receipts, a live cost ratio, and application-semantics evidence are absent by design. Required Ethereum local/testnet, OP-family testnet, and Arbitrum-family testnet measurements are also missing; package completion status is therefore `INCOMPLETE_REQUIRED_NETWORK_MEASUREMENTS`. No live acquisition is attempted without the exact verifier.

## Deterministic transaction corpus

`generate.py` creates both `seeded-incompressible` and `repeated` calldata at 80, 90, 110, 116, 120, 128, 160, and 210 KiB for all three chain IDs. Each type-2 transaction fixes:

- the public Anvil/Hardhat account-0 research key (never suitable for assets or production);
- nonce 7, value 0, fee cap 30 gwei, priority cap 1 gwei;
- destination `0x1111111111111111111111111111111111111111`, empty access list; and
- the network-specific chain ID and modeled maximum transaction gas field.

Signing is deterministic RFC-6979 secp256k1 with low-`s` normalization. `results/transactions.csv` records payload SHA-256/Keccak-256, exact zero/nonzero counts, exact signed length and transaction hash, and admission/gas projections. Raw multi-megabyte binaries are regenerated rather than retained.

## Gas evidence boundaries

Active EIP-7623 is evaluated exactly:

```text
tokens = calldataZeroBytes + 4 * calldataNonzeroBytes
floor  = 21,000 + 10 * tokens
regularIntrinsic = 21,000 + 4 * zero + 16 * nonzero
noOpCalldataGas = max(floor, regularIntrinsic)
```

The no-op value assumes no verifier code executes. It is not a receipt. `results/baseline-feasibility.csv` separately projects both measured v0.3 EVM A/B total-gas columns against each selected gas cap. The baseline calldata alone exceeds every selected ordinary signed-byte boundary, so every baseline row is rejected on size irrespective of its gas result. No row is labeled a selected-L2 PQTC measurement because no exact verifier receipt was captured.

Active deployment bounds are 24,576 bytes of returned runtime code and 49,152 bytes of initcode on all selected ordinary Solidity/EVM routes. No exact verifier bytecode was supplied, so artifact-specific deployment fit is `NOT_EVALUATED`, not guessed. Scroll additionally disables RIPEMD-160/BLAKE2F, limits MODEXP component lengths to 32 bytes, and lacks blob opcodes/EIP-4788; OP Karst also changes crypto-sensitive precompiles. Verifier opcode/precompile suitability therefore requires the actual artifact.

## Fee formulas and scenarios

Every fee output is labeled **`PROJECTION`** and **`SYNTHETIC_OFFLINE_INPUT_NOT_LIVE`**. `scenarios.json` supplies the full cross-product `l1BaseFee={1,10,30,100} gwei` and `l1BlobBaseFee={1,10,100} wei/blob-gas`, plus explicit L2 base fee and every scalar/oracle field. These values are experiment inputs, not network observations.

### OP Fjord/Jovian

For FastLZ size `f` of the complete signed transaction:

```text
S = max(100,000,000, -42,585,600 + 836,500*f)
F = 16*l1BaseFeeScalar*l1BaseFee + l1BlobFeeScalar*l1BlobBaseFee
l1Fee = floor(S*F / 10^12)
daFootprint = max(100, floor((-42,585,600 + 836,500*f)/10^6)) * daFootprintGasScalar
operatorFee = gasUsed*operatorFeeScalar*100 + operatorFeeConstant
```

`l2_model.py` ports the pinned `fastlz1_compress` path exactly for compressed size; focused vectors were checked against FastLZ commit `344eb4025f9ae866ebf7a2ec48850f7113a97a42`. OP totals in `fee-projections.csv` use no-op gas and are projections, not actual batch marginal size or receipts.

### Arbitrum Nitro

The pinned formula Brotli-compresses the signed binary at level 1, sets `units=16*compressedBytes`, `posterCostWei=PricePerUnit*units`, and converts poster cost to gas with the synthetic L2 base fee. `PricePerUnit` is adaptive chain state. The repository does not retain the exact pinned Nitro compressor executable, so compression, poster gas, L1 cost, and total are `NOT_EVALUATED`; a generic Brotli substitute is intentionally refused.

### Scroll Feynman

Feynman computes codec-v8 zstd ratio on `tx.data`, clamps the ratio to at least `10^9`, selects a binary penalty, and charges:

```text
feePerByte = execScalar*l1BaseFee + blobScalar*l1BlobBaseFee
l1DataFee = floor(feePerByte * len(signedTx) * penalty / 10^18)
```

Mainnet `GalileoTime=nil`, so Galileo's compressed-signed-transaction formula is not active. The exact codec-v8 standard-zstd-0.13 experimental executable is not retained; the workstation zstd is not substituted. Scroll ratio, penalty, L1 fee, and total remain `NOT_EVALUATED`.

## Finality, withdrawal, and security assumptions

- **OP:** sequencer inclusion is provisional; safe/finalized follows Ethereum L1. Canonical withdrawal is approximately seven days. Fault-proof security requires an honest challenger to answer invalid claims before game clocks expire; the respected Karst game is CANNON_KONA type 8.
- **Arbitrum:** sequencer-trusting soft finality is sub-second; parent-chain data finality is roughly 12–15 minutes. BoLD settlement waits 45,818 L1 blocks (about 6.4 days), then withdrawal is claimed. At least one validator must check/challenge; force inclusion is 5,760 L1 blocks/about 24 hours.
- **Scroll:** Confirmed is sequencer inclusion, Committed is an L1-finalized batch commit, and Finalized is an L1-finalized validity proof. Withdrawal follows validity finalization with a Merkle proof and has no fixed seven-day fraud window; actual prover/batcher/L1 latency is external. Euclid provides enforced inclusion/emergency batch submission, while upgrades remain under a 9-of-12 Security Council.

These are protocol assumptions, not measured latency samples.

## Hardware profiles

H1 is the measured local Apple M4 Max source distribution in `research/summaries/v03-distribution.csv`. H2 (CI 8-core/32 GiB) and H3 (commodity 16-core/64 GiB) were unavailable and are explicit blockers/`NOT_EVALUATED`. These hardware labels do not refer to the repository's hash candidates named H1/H2/H3.

## Reproduction

From this directory:

```sh
python3 generate.py
python3 generate.py --check
python3 -m unittest -v test_l2_economics.py
python3 calculator.py --network op-mainnet --family repeated --kib 80 --scenario-id l1-10gwei-blob-10wei
```

`--check` regenerates all result content in memory and fails unless the retained CSV/JSON files match byte-for-byte. The focused tests cover deterministic signing, upstream FastLZ reference sizes, EIP-7623 endpoints, exact ordinary byte boundaries, the 80/210 KiB verdict, fee labels, absence of false PQTC claims, and retained artifact reproducibility.
