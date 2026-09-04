# ADR — Separate native full-ZK Spartan-WHIR from standalone Solidity WHIR

Research cutoff: **2026-09-04**.

## Decision

Record a `PASS` only for the implementation maturity of native full-ZK Spartan-WHIR at `f525cddea38bb605304d3a8e6394dda10ac64b4a`. The upstream DirectSparse and Spark APIs expose full-ZK setup, prove, and verify with cryptographically secure proving randomness. The prepared end-to-end command runs the upstream README relation, not the frozen v0.3/H0 relation, so it is **not PQTC evidence**.

Keep full EVM Spartan `DEFERRED`. At `b381a9091568d1a4a52b50d0b27488a767051faf`, `sol-spartan-whir` verifies a real standalone plain-WHIR proof nested in placeholder Spartan fields. Every build, test, gas value, and calldata value from that track is **standalone WHIR — not Spartan and not PQTC**.

## Rationale

The native repository demonstrates a complete full-ZK R1CS implementation, but it does not supply the exact frozen PQTC relation, its public-input semantics, a matching Solidity verifier, or an implementation-specific QROM argument. The standalone exporter at `ec7c24f451f208debf86144d45bb3441e9d85cc4` explicitly severs the dependency on current native Spartan-WHIR and identifies its Spartan artifacts as schema placeholders.

The pinned Solidity tree ignores `lib/` and does not retain dependency gitlinks. For a reproducible build, the runner uses the archived plain-WHIR landscape pin `privacy-ethereum/sol-whir@b719b97b5961ac1c1679383b31e55439a26682f9` as the dependency control: its gitlinks select `forge-std@035de35f5e366c8d6ed142aec4ccb57fe2dd87d4` and `solady@513f581675374706dbe947284d6b12d19ce35a2a`. Those dependencies and any nested submodules are checked out recursively, their imported source bytes are verified, and their exact state is recorded with each Solidity result.

With those exact dependencies, `forge build` and `forge test` completed successfully. This is a `PASS` only for the pinned standalone-WHIR project's build/tests. The exact upstream transaction-gas script did not reach Anvil or a gas measurement: under `set -u`, line 95 expands an unbound `target_contract[@]` array and exits. The harness is `UNEXECUTABLE_UPSTREAM_HARNESS_AT_PIN`; gas is `NOT_EVALUATED`. Patching the upstream script would no longer reproduce the exact pin and is not authorized.

## License gate

The inspected native and Solidity repositories have no complete LICENSE file or adequate explicit grant. The README's trailing `MIT` text is not sufficient. This package vendors no upstream source; the runner clones exact pins into an external workspace. Copying or redistribution remains blocked until an explicit grant is obtained.

## Consequences

- Native full-ZK Spartan-WHIR: `PASS_IMPLEMENTATION_MATURITY_ONLY`.
- Native exact PQTC relation: not implemented and not claimed.
- Full EVM Spartan: `DEFERRED`.
- Standalone Solidity WHIR build/tests: `PASS`, still not Spartan and not PQTC.
- Standalone Solidity WHIR gas: `UNEXECUTABLE_UPSTREAM_HARNESS_AT_PIN`; `NOT_EVALUATED`, with no local gas number.
- No privacy finalist or integration is selected.
