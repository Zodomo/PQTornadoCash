# C00 deployment gas

**Status: NOT_EVALUATED.** The engineering report supplies runtime sizes but did not establish deployment gas, and this package does not relabel estimates as measurements.

Run `research/candidates/v03-baseline/scripts/measure-deployment.sh`. The isolated Foundry profile emits, for each frozen deployable contract:

- creation/initcode bytes including constructor arguments;
- deployed runtime bytes;
- exact EVM code-deposit charge at 200 gas per runtime byte;
- total gas observed around the Solidity `new` expression in the Foundry execution.

Constructor execution gas is not separately observable from the high-level `new` expression in this harness and is emitted as `NOT_SEPARATELY_OBSERVABLE`, not inferred by subtracting potentially fork-dependent creation overhead. A client receipt route is required before any total creation-transaction or EIP-7825 fit claim.

Historic report runtime sizes (reference only, not a fresh measurement) are 17,805 bytes for `PQTCAirStageVerifier`, 12,956 for `PQTCQueryVerifier`, 13,123 for `PQTCVerificationRegistry`, and 7,548 for `PQTCClassicPool`.
