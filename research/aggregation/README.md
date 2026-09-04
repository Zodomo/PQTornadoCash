# SP-70 proof-only aggregation research

This package evaluates the SP-70 state, privacy, batching, and accounting interfaces. It does not contain an accepted hiding proof, recursive verifier, flat outer verifier, or folding scheme.

## Deterministic runner

From the repository root:

```sh
python3 research/aggregation/run.py
```

The command executes all N = 1/2/4/8/16/32/64 model cases for same-user and unrelated-user submissions; checks recursive-tree, flat-outer, and folding result rows; exercises fixed-window, threshold, and multiple-permissionless-aggregator policies; rejects statement mutations, replay, duplicate nullifiers, noncanonical order, bad proofs, and unfilled thresholds; checks rebatching, front-running invariance, pull-claim recovery, conservation, and proof-only API boundaries; validates the retained result; and writes:

- `outputs/results.json` — deterministic model, complete matrix, null metrics, policies, and gate;
- `source-hashes.json` — SHA-256 hashes of package sources and frozen inputs.

The runner also attempts to insert a numeric total into a row with missing proof metrics. Its validator must reject that counterfeit total before the run can pass.

## Focused Foundry component command

Run the model first so the retained result exists, then:

```sh
cd research/aggregation/solidity
./run-gas.sh
```

The script uses canonical Solidity settings: solc 0.8.30, Prague, optimizer enabled with 200 runs, and via-IR. It runs only `testMeasureSettlementComponentsOnly`, retains `outputs/foundry-components.json`, and ingests the seven-size grid into `outputs/results.json`.

The measurements are exact for these isolated surfaces:

- 512-bit nullifier check/write component;
- pull-credit payout component for unrelated recipients/relayers;
- pull-credit payout component for repeated same-user recipient/relayer;
- one successful pull claim;
- ABI bytes and zero/nonzero byte counts for `settle(withdrawals, bytes(""))`;
- active EIP-7623 10/40 and uniform 64/96 calldata floors for that empty-proof call.

They are **not** a full aggregation benchmark. The test registry accepts model roots and the test verifier checks only a preloaded batch identifier. Empty outer-proof calldata excludes the missing proof and its padding. Component calls have their own overhead and must not be added together as a settlement transaction.

Additional focused safety-shell tests are retained in `SettlementGas.t.sol`, but `run-gas.sh` intentionally measures only the named component experiment.

## Privacy and settlement architecture

```text
user locally generates hiding individual proof
        |
        v
permissionless aggregator receives proof + public statement only
        |
        v
future accepted outer proof binds canonical ordered statements
        |
        v
one atomic transaction consumes N nullifiers and creates pull credits
        |
        v
recipient and relayer claim independently
```

The aggregator interface has no note-witness input. It must never receive note secrets, trapdoors, Merkle paths, or raw witnesses. The same restriction applies to same-user batches. A centralized raw-witness prover fails this package.

Each statement binds chain, settlement contract, denomination, known root, 512-bit nullifier, recipient, relayer, and fee. Strict statement-hash ordering gives a canonical batch identifier. Duplicate nullifiers are checked before credits. The caller cannot redirect payouts, so front-running the same valid batch only settles the same recipients. Pull payments prevent one rejecting receiver from reverting other users' settlement; a failed claim leaves that credit available to retry.

Proof submissions are noncustodial and nonexclusive. A malformed individual proof is excluded without consuming other proofs. After censorship, an unfilled threshold, a failed outer proof, or a spent-nullifier race, users can submit the same public-proof package to another aggregator or use the required individual path. There is no aggregator allowlist or exclusive queue.

## Honest result and gate

No accepted hiding individual proof exists in current evidence. Consequently every recursive-tree, flat-outer, and folding row retains the following as `null` with `NOT_EVALUATED` status: outer proof bytes, proving time/RSS, verifier time/gas, full proof-bearing calldata, complete settlement execution, active/64/96 total gas, gas per withdrawal, failure-recovery gas, and minimum economical N. Missing metrics are never encoded as zero.

The gate is `STOP_BY_DEPENDENCY`. Aggregation has not shown a transaction at or below 14M or at most 1M gas per withdrawal at N >= 16 / at least 70% improvement. The active $2^{24}$ transaction cap is recorded but cannot be evaluated from component-only evidence. External cryptographic acceptance remains open, and aggregation cannot replace a functional individual-withdrawal path.
