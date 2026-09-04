# SP-11 accumulator shape decision

## Decision

Retain the frozen binary depth-20 H0 accumulator as the only custody-compatible shape. Arity 4 at depth 10 preserves exactly $2^{20}$ leaves; arity 8 at depth 7 provides $2^{21}$ leaves. Both higher-arity shapes stop at the security gate because no arity-specific compressor passed SP-10 security review. H3/H5/H6 numbers are lower engineering evidence only.

Compare unbounded root membership with a 64-root ring, and constructor-computed storage zeros with precomputed storage and packed code-blob concepts. The latter two cannot preserve frozen H0 universally: `emptyLeaf(scope)` makes every zero deployment-specific. They remain negative design results rather than fake implementations.

## Executable evidence

`model.py` implements generalized incremental frontiers and an independent padded-tree recomputation. `run.py` checks 1,000 frozen corpus records for identity/order/digest integrity, runs 256 commitment-derived inserts at arities 2/4/8, compares every incremental root with independent recomputation, and emits exact logical transitions for 0..255 and every $2^k-1,2^k$ boundary through $k=20$.

The SHA-512 model compressor is explicitly not H0. The canonical Foundry parity test recomputes all 1,000 frozen roots and, only after every assertion passes, retains `outputs/foundry-parity.json` with the compiler profile, case count, PASS status, and SHA-256 corpus identity. The main generator reports parity PASS only after strict artifact validation; a missing artifact is `NOT_EVALUATED`. `solidity/test/AccumulatorGas.t.sol` separately records isolated gas-left deltas for binary bounded/unbounded calls, internal `new` expressions, and synthetic boundaries. Those diagnostics omit transaction intrinsic gas, calldata gas, the EIP-7623 floor, and receipts; synthetic loading also makes no root-provenance claim.

## Measurement labels

SP-10 H0/H3/H5/H6 values are copied as `EXACT_RETAINED_SP10_FOUNDRY`. Frontier writes, capacity, witness bytes, and relation hashes are `EXACT_LOGICAL_MODEL`. Retained SP-11 gas-left values are `ISOLATED_CALL_GASLEFT_DIAGNOSTIC_NOT_TRANSACTION_GAS`; complete insertion and deployment transactions remain `NOT_EVALUATED`. The main generator validates and preserves any retained Foundry artifact, so rerunning it cannot silently erase diagnostics while leaving a passing status.

## Consequences

Unbounded history preserves all historical withdrawal roots but grows one membership slot per insert. A bounded ring caps state but can expire a user's withdrawal root, so it is not a default without a separately accepted liveness policy. Binary witnesses are 1,280 bytes and require 20 H0 node relations. Higher arity does not reduce a binary-fold relation and increases sibling bytes. The default therefore stays the frozen unbounded binary depth-20 design.
