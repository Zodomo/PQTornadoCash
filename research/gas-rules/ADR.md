# ADR: Gas-rule activation labels and calculator profiles

- **Status:** Accepted
- **Decision date:** 2026-09-04
- **Applies to:** `research/gas-rules/rules.json`

Source IDs refer to immutable official entries in `sources.json`.

## Context

EIP lifecycle status, fork-meta scheduling, client implementation, and mainnet activation are different facts. On the snapshot date:

- EIP-170, EIP-3860, EIP-7623, and EIP-7825 are active mainnet rules. [sources: `eels-spurious-dragon-activation`, `eels-shanghai-activation`, `eip-7600-pectra`, `eip-7607-fusaka`]
- EIP-7976 and EIP-7954 are Review and Scheduled for Inclusion in Glamsterdam, but the fork has no activation time and Amsterdam is `Unscheduled` in EELS. [sources: `eip-7976-spec`, `eip-7954-spec`, `eip-7773-glamsterdam`, `eip-7773-no-activation`, `eels-amsterdam-unscheduled`]
- EIP-8311 is Draft, names no activation, is absent from the Glamsterdam scheduled list, and is not implemented in the pinned Amsterdam EELS list. [sources: `eip-8311-spec`, `eip-7773-glamsterdam`, `eels-amsterdam-eips`]
- Scheduled EIP-8037 changes the future Amsterdam interpretation of EIP-7825; it does not change the active Osaka rule today. [sources: `eip-8037-cap-rule`, `eip-8037-reservoir`, `geth-osaka-gas-cap`, `geth-amsterdam-gas-cap`]

Without an explicit policy, scheduled or Draft values can be mislabeled as active and silently replace mainnet calculator defaults.

## Decision

### Activation vocabulary

Every profile or rule MUST use exactly one of these network classifications:

1. `active` or `active_mainnet`: activated on mainnet at or before the snapshot, with an official activation block/timestamp source.
2. `scheduled_for_glamsterdam_but_unactivated` or `scheduled_but_unactivated`: present in the fork meta's Scheduled for Inclusion list, but lacking an activation block/timestamp.
3. `unscheduled_scenario` or `unscheduled_draft`: neither activated nor scheduled for inclusion.

`Final`, `Review`, and `Draft` are lifecycle statuses only. They MUST NOT establish network activation. Client code behind an unscheduled fork gate MUST NOT establish network activation.

A scheduled or unscheduled profile MUST set `may_be_labeled_active` to `false` where that field exists. Reports MUST say “scheduled but unactivated” for EIP-7976/EIP-7954 and “Draft, unscheduled scenario” for EIP-8311; they MUST NOT abbreviate either state to “active,” “current,” or “mainnet.” [sources: `eip-7773-glamsterdam`, `eip-7773-no-activation`, `eels-amsterdam-unscheduled`]

### Calculator profile

The default profile MUST be `osaka-active` and MUST use:

- runtime/initcode limits `24,576 / 49,152` bytes;
- calldata-floor zero/non-zero rates `10 / 40` gas;
- maximum specified transaction gas limit $2^{24}=16,777,216$.

[sources: `eip-170-spec`, `eip-3860-spec`, `eip-7623-spec`, `eip-7825-spec`, `geth-protocol-params-basic`, `geth-protocol-params-floor`, `geth-protocol-params-size`]

The only non-default calldata-floor pairs are:

- `64 / 64`, labeled `eip-7976-standalone-64-64` and `scheduled_unactivated`;
- `96 / 96`, labeled `eip-8311-standalone-96-96` and `unscheduled_draft`.

No 15/60 floor scenario is retained. [sources: `eip-7976-spec`, `eip-7976-64-change`, `eip-8311-spec`]

EIP-7954's `65,536 / 131,072` limits MUST remain proposed rule data and MUST NOT replace defaults before an official activation is recorded. [sources: `eip-7954-spec`, `eip-7773-no-activation`, `eels-amsterdam-unscheduled`, `geth-protocol-params-size`]

### Formula boundaries

The EIP-7976 and EIP-8311 equations in `rules.json` are standalone scenarios. They MUST NOT be presented as a complete Glamsterdam calculation. The current reference composition changes the floor base via EIP-2780 and includes access-list bytes via EIP-7981. EIP-8311 changes only EIP-7976's calldata parameter, so its 96 rate MUST NOT be applied to access-list bytes without a future integrated specification. [sources: `eip-7976-spec`, `eip-8311-spec`, `geth-floor-composition`]

Active Osaka validation MUST be described as `tx.gasLimit <= 2^24`. The future EIP-8037 form MUST be separately labeled scheduled Amsterdam behavior: `tx.gas` may exceed $2^{24}$, but `max(intrinsic_gas, calldata_floor) <= 2^24`, execution is capped, and excess becomes a state-gas reservoir. [sources: `eip-7825-spec`, `eels-osaka-validation`, `eip-8037-cap-rule`, `eip-8037-reservoir`]

### Evidence labels

Byte-derived values MUST be labeled `deterministic_from_exact_bytes`. Values involving execution state, refunds, dynamic returned code, or final gas used MUST be labeled `requires_pinned_state_client_execution_or_receipt`. Neither protocol equations nor client gas simulations may be described as PQTC timing or throughput measurements. [sources: `eip-3860-spec`, `eip-7623-spec`, `eels-prague-intrinsic`, `eels-prague-settlement`]

## Stale plan/report assumptions rejected

The research plan and report now reject these prior assumptions:

- EIP-7825 is only proposed;
- EIP-7976 still specifies 15/60;
- EIP-8311's 96/96 scenario is active or scheduled in Glamsterdam;
- EIP-7954 still specifies 32 KiB/64 KiB (or a discussion title's “48kb” is normative);
- EIP-7825's field cap can be projected unchanged through scheduled EIP-8037;
- scheduled 64/64 floor and 65,536/131,072 size rules should be current defaults.

The corrected facts and source mapping are recorded in `README.md` and `rules.json`. [sources: `eip-7607-fusaka`, `eip-7976-64-change`, `eip-8311-spec`, `eip-7954-64k-change`, `eip-8037-cap-rule`, `eip-7773-no-activation`]

## Consequences

- Mainnet calculator output remains reproducible against the active Osaka protocol.
- Future sensitivity analyses remain explicit and cannot be mistaken for deployment claims.
- A future default-profile change requires a new official activation block/timestamp source and an update to this decision; a proposal status change or client fork gate alone is insufficient.
