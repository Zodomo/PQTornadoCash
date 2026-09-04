# SP-72: bounded two-call continuation state

## Status

Research harness accepted for state-machine study; gas candidate rejected by retained projections; integrated full path NOT_EVALUATED.

## Context

The frozen v0.3 continuation is keyed by randomized Part A material, has no expiry, and does not provide the bounded one-nullifier lifecycle required by SP-72. A safer fallback must preserve exactly two consumer transactions, prevent state multiplication for one note, pin bounded-history roots, and make proof completion inseparable from nullifier consumption and payment.

## Decision

Key one checkpoint by a domain-separated hash of both nullifier limbs. Bind the registry to one immutable consumer. Store one packed metadata word and six full-width, two-slot digests: statement, global data, checkpoint, proof, continuation, and root. The continuation is fixed-size; no proof bytes, witness, dynamic array, reusable fact, or success mapping exists.

An identical live A is idempotent, which makes an exact A front-run harmless. A different live A reverts even when independently valid. At expiry, the consumer may atomically replace the checkpoint, and any address may clean it. Each stored checkpoint increments a root pin; complete, cleanup, and replacement decrement exactly once. The pool reconstructs a two-limb statement over chain, pool, nullifier, root, recipient, and amount.

B checks every stored limb and the immutable split, invokes the binding verifier, deletes the checkpoint, marks the nullifier, and transfers in one EVM transaction. Payment failure rolls all three effects back. The consumer is non-reentrant. Events are receipts, not reusable verification facts.

The split is immutable per deployment and configurable from 8 through 16 Part A queries. The retained v0.3 profile is swept at 8/24, 10/22, 12/20, 13/19, 14/18, 15/17, and 16/16 with both AIR placements. No verifier or proof is regenerated.

## Gas and storage accounting

The checkpoint struct occupies 13 storage slots. A distinct pinned root adds at most one incremental live slot, so worst-case live state is 14 slots (448 logical bytes) per distinct active nullifier. The global active count is shared and excluded from per-checkpoint live growth.

Under the explicit Prague access-order assumptions in `outputs/results.json`, Part A storage writes cost 329,400 gas, matched B deletion costs 79,200 gross gas, and permissionless cleanup deletion costs 100,200 gross gas. In the unique-root/final-active case, clearing 15 nonzero words accrues 72,000 refund gas; shared root/count words may instead be reset without refunds. Refunds are reported separately and never credited to transaction-cap decisions. These are exact opcode-schedule terms, not full function measurements.

Optional Foundry output measures the harness plus its deterministic binding mock. It is retained separately from the V9 verifier projections. The two are not added: the replaced v0.3 state overhead has not been isolated, and such a sum could double count.

## Consequences

One note cannot create unbounded concurrent checkpoints, abandoned state is permissionlessly recoverable, and an active root cannot age out. Recovery takes exactly the configured TTL in blocks; the canonical model uses 256 blocks and labels 3,072 seconds as a projection based on 12 seconds per block.

The best retained minimum-margin row is still above the robust limits, and every row exceeds the 20M two-call total. Therefore projection arithmetic is FAIL. Because no complete frozen verifier is integrated with this state machine, exact full-path binding and gas remain NOT_EVALUATED. This ADR does not security-qualify a candidate or alter frozen v0.3.
