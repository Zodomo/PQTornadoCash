# SP-70 proof-only aggregation decision

## Decision

Stop SP-70 by dependency. Retain a proof-only, permissionless batching interface and pull-payment settlement shell, but do not select recursion, a flat outer proof, or folding. No accepted hiding individual proof exists to aggregate. Therefore proof bytes, proving time/RSS, verifier time/gas, full calldata, active/64/96 totals, gas per withdrawal, recovery gas, and minimum economical N remain `NOT_EVALUATED` rather than zero.

Aggregation is additive product research. It cannot replace at least one functional individual-withdrawal path.

## Required privacy boundary

A user proves locally and gives an aggregator only an opaque individual proof plus the public root, nullifier, recipient, relayer, and fee statement. `Aggregator.submit` has no witness parameter. Note secrets, trapdoors, Merkle paths, and raw trace witnesses never cross that boundary. Same-user aggregation does not weaken this rule. A centralized witness collector is a different trusted system and is rejected.

The model SHA-256 tokens and Foundry `ModelBindingVerifier` are conspicuously non-cryptographic oracles. They exercise interfaces and state transitions only. They are not evidence of hiding, recursion, folding, soundness, or post-quantum security.

## Compared designs and operating modes

The complete N grid is 1/2/4/8/16/32/64. Every N retains rows for recursive binary proof trees, flat outer verification, and PQ-oriented hiding folding, crossed with same-user multi-note and unrelated-user proofs. All three cryptographic designs stop at the same missing prerequisite without fabricated metrics.

Threshold-triggered and fixed-window scheduling are noncustodial off-chain policies. A threshold aggregator publishes as soon as N valid proofs exist. A fixed-window aggregator publishes the canonical subset available at its deadline, using a supported N, and leaves the rest reusable. Multiple aggregators are permissionless: no registration, owner, or exclusive proof reservation exists. A proof can be sent to another aggregator or used through the individual path.

## Canonical statement, ordering, and front-running

Each public statement binds chain, settlement contract, denomination, root, 512-bit nullifier, recipient, relayer, and fee. Statements are strictly ordered by unique domain-separated statement hash. The batch identifier is a domain-separated hash chain over N and those keys. Solidity additionally consults the integrating pool's known-root registry. Any field mutation changes the identifier and must fail the accepted outer verifier. Duplicate statement keys, intra-batch nullifiers, previously spent nullifiers, unsupported N, unknown roots, zero recipients, invalid fees, and noncanonical ordering reject.

The transaction sender is not a payout destination. A front-run caller can only submit the same bound batch and cause the same credits. Replay then fails on spent nullifiers. This makes settlement permissionless without giving an aggregator payment-redirection authority.

## Atomicity, payout policy, and recovery

All root, statement, ordering, duplicate, spent-nullifier, funding, and proof checks precede state effects. A successful transaction atomically spends all N nullifiers and creates denomination-conserving pull credits. It performs no recipient-controlled external call. Recipient and relayer claims are isolated. If a receiver rejects a claim, EVM rollback retains that receiver's credit and does not affect other users.

A bad individual proof is rejected before batch construction while good proofs remain available. A failed outer proof or a race with an individually spent nullifier atomically reverts; aggregators rebuild without the bad or spent entry. An unfilled or censored batch holds no funds, note witness, nullifier reservation, or exclusive right. Users resubmit the same proof package elsewhere or take the individual route. These recovery transitions are executable model results, not gas measurements.

## Cost accounting and gate

The Foundry harness isolates exact gas-left deltas for 512-bit nullifier checks/writes, unrelated-user and same-user pull-credit updates, and a successful pull claim. It also retains exact ABI byte/zero/nonzero counts and active EIP-7623 plus uniform-64/96 calldata floors for a settlement call with an empty outer proof. Those values are components only. The mock registry and binding verifier do not make a complete aggregate verifier.

A complete total requires a real outer proof, complete proof-bearing calldata, and complete settlement execution through an accepted verifier. `result.schema.json` separates incomplete rows (null totals plus the fixed reason) from complete rows (all prerequisite metrics and integer totals). `run.py` deliberately injects a counterfeit total and requires validation to reject it.

The active transaction cap is $2^{24}=16,777,216$. Product relevance additionally requires total settlement gas at most 14M and either at most 1M gas per withdrawal for N at least 16 or at least 70% improvement over the best individual route, plus the proof-only privacy and permissionless fallback requirements. Missing inputs force `STOP_BY_DEPENDENCY`; isolated components cannot pass either economic gate.
