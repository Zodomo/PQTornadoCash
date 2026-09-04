# SP-12 deposit batching decision

## Decision

Keep SP-12 research-only and `DEFERRED/STOP`. The queue has no owner or finalizer allowlist. Any account may submit a proof for the exact current prefix, and any account may trigger the expired-head escape. Promotion requires both measured positive amortized gas versus direct v0.3 deposits and a real trustless transition-proof backend.

## Canonical relation

An enqueue receives exactly one denomination and fixes commitment, depositor, refund address, timestamp, and monotonic sequence. The canonical prefix commitment includes those values in sequence order. The public transition statement binds old root, new root, prefix commitment, accumulator start index, batch count, and queue epoch. Finalization accepts only counts 8/16/32/64/256 and advances state atomically.

`model.py` implements that relation with a conspicuously named model oracle. It rejects omission, reorder, substitution, duplicate, altered prefix, altered root, bad proof, unsupported count, and absent-backend cases. This proves interface/state-machine semantics only. It does not fake a PCS proof or establish cryptographic soundness.

## Liveness and griefing

The Solidity research queue implements permissionless refund of only the expired head. Head-only escape preserves a unique remaining order. The executable model also covers forced-single progress after timeout, which is viable only when a qualified accumulator transition is directly available. Neither path assumes a trusted or always-online operator. Flooding remains possible at the cost of denomination capital plus transactions.

## Costs and labels

The frozen v0.3 direct deposit measurement is exactly 13,991,021 gas. The isolated Foundry harness measures 256 queue enqueue calls; until run, the queue field is `NOT_EVALUATED`. Finalizer gas, proof bytes, proving/verification time, and RSS remain `NOT_EVALUATED` until a real backend exists. Analytic Poisson fill latency is labeled a model, not a timing measurement. No amortized break-even is produced from missing inputs.
