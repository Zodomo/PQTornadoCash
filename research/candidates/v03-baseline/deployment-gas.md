# C00 deployment gas

**Measured component status: FAIL for the pool's internal EIP-7825 comparison; top-level deployment remains NOT_EVALUATED.** Source: retained `gas/deployment-profile.log`, Solc 0.8.30 / Foundry 1.7.1.

| Contract | Initcode bytes | Runtime bytes | Exact code-deposit gas | Observed internal `new` gas | EIP-170 | EIP-3860 | Margin vs 2^24 |
|---|---:|---:|---:|---:|---|---|---:|
| `PQTCAirStageVerifier` | 17,853 | 17,827 | 3,565,400 | 3,606,627 | PASS | PASS | 13,170,589 |
| `PQTCQueryVerifier` | 13,015 | 12,989 | 2,597,800 | 2,637,194 | PASS | PASS | 14,140,022 |
| `PQTCVerificationRegistry` | 13,644 | 13,122 | 2,624,400 | 2,665,881 | PASS | PASS | 14,111,335 |
| `PQTCClassicPool` | 12,867 | 7,494 | 1,498,800 | 18,873,630 | PASS | PASS | -2,096,414 |

All four runtimes are at most 24,576 bytes (EIP-170) and all four initcodes are at most 49,152 bytes (EIP-3860). Code-deposit gas is exact at 200 gas/runtime byte. EIP-3860 word metering is retained in `gas/measured-summary.json`. Constructor execution gas is not separately observable in this harness.

The pool's observed internal Solidity `new` expression used 18,873,630 gas, 2,096,414 above 16,777,216. This is a real local internal-CREATE measurement and a deployment blocker. It is **not** a mined creation receipt or an exact top-level creation-transaction total: initcode zero/nonzero byte counts, top-level intrinsic gas, and a receipt are absent. Those top-level fields remain `NOT_EVALUATED`, rather than being inferred.
