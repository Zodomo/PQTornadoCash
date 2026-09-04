# ADR: SP-71 ordinary L2 admission sweep and fee-model evidence

## Context

SP-71 asks whether OP Mainnet Karst, Arbitrum One ArbOS61/Nitro v3.11.3, or Scroll Mainnet Feynman can carry deterministic 80–210 KiB PQTC-shaped calldata through the ordinary sequencer path. The experiment must be offline and reproducible. Network prices and oracle scalars are dynamic state, while admission is defined on the exact signed serialized transaction rather than a nominal calldata size. An EIP-7623 floor or a no-op calldata calculation is not verifier execution, and only a receipt from the exact verifier may be called a PQTC measurement.

## Decision

The package-specific `admission_sweep_gate` **fails**. Retain this as a source-proven negative result:

- OP ordinary pools cap the signed transaction at 131,072 bytes.
- Arbitrum's ordinary sequencer default caps it at 95,000 bytes.
- Scroll's regular mining rule caps it at 116,736 bytes.
- Every generated 210 KiB payload necessarily produces a signed transaction above all three limits. No full-node launch is required to prove those rejections.
- The generated 80 KiB transactions are below every selected byte cap, but that is an admission projection. Faithful local tx-pool errors/receipts remain an independent reproduction task.

The separate SP-71 product gate asks whether user cost improves by at least 90% while application semantics remain supported. Its result is **`NOT_EVALUATED_NOT_PASSED`**: this offline package has no exact selected-L2 verifier receipts, no live cost ratio, and no application-semantics evidence. Required Ethereum local/testnet, OP-family testnet, and Arbitrum-family testnet measurements are also absent, so package status is `INCOMPLETE_REQUIRED_NETWORK_MEASUREMENTS`. No live acquisition is attempted without the exact verifier. The admission-sweep failure must not be relabeled as the SP-71 product-gate result.

Do not select an unchunked ordinary direct-sequencer design for the full range. Chunking, delayed/enforced messages, or a bridge-mediated design changes the protocol/product and needs a separate decision plus end-to-end local reproduction.

## Fee decision

Use only exact estimators traceable to the immutable pins. The retained source-equivalent FastLZ size port supports OP Fjord/Jovian projections. Do not substitute a generic Brotli library for Nitro's canonical level-1 path or the workstation `zstd` for Scroll codec-v8's standard-zstd-0.13 experimental path. Those two totals remain `NOT_EVALUATED` with null values. Every numeric fee is a `PROJECTION` over explicit synthetic fields in `scenarios.json`; none is live.

## Gas and verifier decision

Apply active EIP-7623 exactly: `tokens = zero + 4*nonzero` and `floor = 21000 + 10*tokens`. Keep four evidence classes separate:

1. signed-byte admission projection;
2. byte-derived no-op calldata gas;
3. baseline verifier-gas feasibility projected against a selected cap; and
4. an actual selected-client PQTC receipt, which is absent.

The H1 Apple M4 Max distribution is retained as source measurement input. H2 CI 8-core/32 GiB and H3 commodity 16-core/64 GiB are unavailable and remain blockers/`NOT_EVALUATED`; these hardware names are unrelated to the H1/H2/H3 hash candidates.

## Consequences

The package closes the offline formula and admission experiment with a negative admission-sweep result. The SP-71 product gate remains `NOT_EVALUATED_NOT_PASSED`, while the package deliberately makes no local inclusion, live-price/cost-ratio, application-semantics, proof-latency, withdrawal-latency, deployment-fit, or PQTC-receipt claim. A later admission reproduction may launch the pinned clients, but it cannot reverse a byte-limit rejection for the existing 210 KiB ordinary transaction shape.
