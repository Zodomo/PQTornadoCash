# Ethereum gas-rule research report

Authoritative snapshot: **2026-09-04**. This package records protocol rules; it is not a PQTC performance measurement. `rules.json` is the calculator-facing record and `sources.json` pins every cited official source to an exact repository commit.

Pinned source revisions:

- Ethereum/EIPs `9207c6011f526bd40abd79649484a1a342585bd4`
- ethereum/execution-specs `903b48f152c932f6e47a615f0f7f009c56f1d92b` (`tests@v20.0.2-39-g903b48f`)
- ethereum/go-ethereum `8a6b06fef836a84850711dfa3799851c4d331fdf`

Bracketed source IDs below resolve to immutable official URLs in `sources.json`.

## Calculator defaults

The default profile is active **Osaka** mainnet behavior:

| Field | Default |
|---|---:|
| Maximum returned/deployed runtime code | 24,576 bytes |
| Maximum initcode | 49,152 bytes |
| Calldata floor rate, zero/non-zero byte | 10/40 gas |
| Maximum specified transaction gas limit | $2^{24}=16,777,216$ gas |

[sources: `eip-170-spec`, `eip-3860-spec`, `eip-7623-spec`, `eip-7825-spec`, `eels-osaka-validation`, `geth-protocol-params-size`]

The only non-default calldata-floor scenarios are **64/64** (EIP-7976 standalone, scheduled but unactivated) and **96/96** (EIP-8311 standalone, Draft and unscheduled). Neither may be labeled active. The scheduled EIP-7954 limits are recorded as protocol research, not substituted into the defaults. [sources: `eip-7976-spec`, `eip-8311-spec`, `eip-7954-spec`, `eip-7773-glamsterdam`, `eip-7773-no-activation`, `eels-amsterdam-unscheduled`]

## Variables and byte equations

For transaction data, let:

- $z$ be the zero-byte count, $n$ the non-zero-byte count, and $L=z+n$;
- $T=z+4n$ be the active EIP-7623 calldata-token count;
- $W=\lceil L/32\rceil$;
- $c=1$ for top-level contract creation and $0$ otherwise;
- $E$ be EVM execution gas used after refund. For creation, $E$ includes constructor execution and code-deposit work, but excludes the separately displayed fixed creation and initcode-word charges.

The active EIP-7623 floor is

$$G_{floor}=21{,}000+10T=21{,}000+10z+40n.$$

For the EIP's displayed base transaction shape,

$$tx.gasUsed=21{,}000+\max(4T+E+c(32{,}000+2W),10T).$$

Universally, gas used after refund is raised to the floor, and validity requires `tx.gasLimit >= max(G_intrinsic, G_floor)`. Prague EELS computes the refund first and then applies the floor. Access-list and EIP-7702 authorization charges affect regular intrinsic/execution cost, not the Prague floor. [sources: `eip-7623-spec`, `eels-prague-intrinsic`, `eels-prague-settlement`, `eip-7600-pectra`]

## Rule cross-check

### EIP-170 — active

EIP-170 is Final and has been active since Spurious Dragon, mainnet block `2,675,000` on 2016-11-22. `MAX_CODE_SIZE = 0x6000 = 24,576`; exactly 24,576 returned runtime-code bytes are allowed, while more causes creation to fail out of gas. This is a runtime-code limit, not an initcode limit. [sources: `eip-170-spec`, `eels-spurious-dragon-activation`]

### EIP-3860 — active

EIP-3860 is Final and has been active since Shanghai, mainnet timestamp `1681338455` (2023-04-12 22:27:35 UTC). `MAX_INITCODE_SIZE = 49,152`, and initcode costs $2\lceil L/32\rceil$ gas. A plain top-level creation's base/data/initcode intrinsic cost is $21{,}000+32{,}000+4z+16n+2W$, before applicable typed-transaction additions. Oversized top-level initcode is transaction-invalid; oversized `CREATE`/`CREATE2` exceptionally aborts out of gas. `CREATE` adds $2W$ to existing base and memory costs; `CREATE2` adds $2W$ to its existing $6W$ hash cost, hence $8W$ before memory. [sources: `eip-3860-spec`, `eels-shanghai-activation`, `eels-initcode-word-cost`]

For top-level creation, the initcode is `tx.data`, so all its bytes contribute to the EIP-7623 floor. The $32{,}000+2W$ creation charges occur only in the regular arm, but the independent intrinsic-validity check must still cover them. [sources: `eip-7623-spec`, `eels-prague-intrinsic`]

### EIP-7825 — active Osaka rule

EIP-7825 is Final and has been active since Fusaka/Osaka, mainnet timestamp `1764798551` (2025-12-03 21:49:11 UTC). It validates the transaction's **specified** gas limit: `tx.gasLimit <= 16,777,216`. A transaction specifying 16,777,217 is invalid. This does not lower the block gas limit, cap an independently measured receipt value, or impose a separate cap on every internal `CALL`/`CREATE`. It applies to transaction/block validation, including creation transactions. [sources: `eip-7825-spec`, `eels-osaka-max-gas`, `eels-osaka-validation`, `eip-7607-fusaka`, `geth-osaka-gas-cap`]

### EIP-7976 — scheduled, not active

EIP-7976 is Review and Scheduled for Inclusion in Glamsterdam, but no mainnet activation is set and EELS marks Amsterdam Unscheduled. It retains ordinary cost $4T$ but defines floor tokens $U=4L$, producing the standalone floor

$$G_{floor,7976}=21{,}000+16U=21{,}000+64L.$$

Thus 64/64 applies only when the floor binds; ordinary execution-heavy transactions retain standard 4/16 calldata pricing. The proposal changed from the stale 15/60 draft to uniform 64/64 on 2026-02-15. [sources: `eip-7976-spec`, `eip-7976-64-change`, `eip-7773-glamsterdam`, `eip-7773-no-activation`, `eels-amsterdam-unscheduled`]

### EIP-8311 — Draft scenario, not scheduled

EIP-8311 is Draft, names no activation fork, is absent from Glamsterdam's Scheduled for Inclusion list, and has no integrated implementation in the pinned EELS/Geth snapshots. It changes only EIP-7976's floor cost per token from 16 to 24:

$$G_{floor,8311}=21{,}000+24(4L)=21{,}000+96L.$$

The 96/96 rate is only a standalone calldata scenario. It must not be extended to access-list bytes because the EIP does not specify such composed-fork behavior. [sources: `eip-8311-spec`, `eip-7773-glamsterdam`, `eels-amsterdam-eips`]

### EIP-7954 — scheduled, not active

EIP-7954 is Review and Scheduled for Inclusion in Glamsterdam, but unactivated. It proposes `0x10000 = 65,536` runtime-code bytes and `0x20000 = 131,072` initcode bytes, while retaining EIP-3860's $2W$ metering. The current EELS/Geth values are fork-gated behind Amsterdam; pre-Amsterdam limits remain 24,576/49,152. On 2026-05-21 the proposal changed from stale 32 KiB/64 KiB values to 64 KiB/128 KiB. [sources: `eip-7954-spec`, `eip-7954-64k-change`, `eip-7773-glamsterdam`, `eels-amsterdam-unscheduled`, `geth-protocol-params-size`]

## EIP-7825 versus scheduled EIP-8037

Do not project the current EIP-7825 field cap unchanged into Amsterdam. The active Osaka rule rejects `tx.gasLimit > 2^24`. The scheduled but unactivated Amsterdam design permits `tx.gas` above $2^{24}$, requires $\max(intrinsic\_gas,calldata\_floor)\leq2^{24}$, caps execution gas at $2^{24}$, and assigns overflow to a state-gas reservoir:

```text
evm_gas             = tx.gas - intrinsic_gas
execution_budget    = 2^24 - intrinsic_gas
gas_left            = min(execution_budget, evm_gas)
state_gas_reservoir = evm_gas - gas_left
```

[sources: `eip-8037-cap-rule`, `eip-8037-reservoir`, `geth-osaka-gas-cap`, `geth-amsterdam-gas-cap`, `eels-amsterdam-unscheduled`]

## Composed Glamsterdam caveat

The literal EIP-7976 formula is not a complete future Glamsterdam calculator. The pinned Amsterdam implementation also composes:

- EIP-2780 floor bases: 12,000 for self-transfer, 15,000 for a distinct zero-value call, 21,000 for a distinct value transfer, and 24,000 for creation;
- EIP-7981 access-list bytes, yielding `floor_base + 64 * (L + 20*A + 32*K)` for $A$ addresses and $K$ storage keys;
- EIP-8037's execution/state-gas split described above.

These composed rules must not be applied to current mainnet. EIP-8311's 96 rate must not be silently applied to access lists. [sources: `geth-floor-composition`, `eip-8037-cap-rule`, `eip-8037-reservoir`, `eip-7773-no-activation`, `eels-amsterdam-unscheduled`]

## Research plan/report corrections

The following assumptions were stale by this report's snapshot and are explicitly rejected:

1. **“EIP-7825 is merely proposed.”** It is Final and active under Osaka; today's rule is the hard `tx.gasLimit <= 16,777,216` check. [sources: `eip-7825-spec`, `eip-7607-fusaka`, `eels-osaka-validation`]
2. **“EIP-7976 is 15/60.”** It changed to uniform 64/64 on 2026-02-15; it is Review and scheduled, but unactivated. [sources: `eip-7976-64-change`, `eip-7976-spec`, `eip-7773-no-activation`]
3. **“EIP-8311's 96/96 floor is active or in Glamsterdam.”** It is a later Draft scenario with no activation and is absent from the scheduled list. [sources: `eip-8311-spec`, `eip-7773-glamsterdam`]
4. **“EIP-7954 proposes 32 KiB/64 KiB” or a discussion title's “48kb” is normative.** The current specification is 65,536/131,072 bytes. [sources: `eip-7954-spec`, `eip-7954-64k-change`]
5. **“EIP-7825 always caps the `gasLimit` field forever.”** Scheduled EIP-8037 changes its Amsterdam meaning to an execution-dimension cap with a state-gas reservoir. That is future, not active Osaka behavior. [sources: `eip-8037-cap-rule`, `eip-8037-reservoir`, `geth-amsterdam-gas-cap`]
6. **“Scheduled rules should become calculator defaults.”** Until Glamsterdam activates, defaults remain 24,576/49,152, 10/40, and $2^{24}$. [sources: `eip-7773-no-activation`, `eels-amsterdam-unscheduled`, `geth-protocol-params-basic`, `geth-protocol-params-floor`, `geth-protocol-params-size`]

## Deterministic fields versus client-measured fields

Exact bytes determine $z,n,L,T,W$, each listed floor, the EIP-3860 word charge, the EIP-7825 signed-transaction gas-limit check, initcode-size compliance from creation input, and runtime-code compliance when the exact deployed-runtime artifact is supplied. [sources: `eip-170-spec`, `eip-3860-spec`, `eip-7623-spec`, `eip-7825-spec`, `eip-7976-spec`, `eip-8311-spec`]

Pinned-state client execution or an actual receipt is required for $E$, total `tx.gasUsed`, constructor control flow, dynamic memory/storage/account-access costs, refunds, reverts, dynamically returned runtime code, and deciding which arm binds when execution is state-dependent. Formula-derived gas and client gas calculations are not PQTC timing or throughput measurements. [sources: `eip-7623-spec`, `eels-prague-intrinsic`, `eels-prague-settlement`]
