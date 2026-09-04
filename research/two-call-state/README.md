# SP-72 robust two-call state study

This research-only package implements a bounded Solidity A/B checkpoint lifecycle and an independent deterministic model. It preserves frozen v0.3 and does not contain a new proof verifier. The Solidity `BindingVerifier` and Python `ModelVerifier` are binding oracles for attack execution only; they provide no cryptographic evidence.

## Reproduce

From the repository root:

```sh
python3 research/two-call-state/run.py
```

The command executes all ten attack models, verifies the pinned retained-profile hash, sweeps all required split/AIR-placement rows, and rewrites:

- `outputs/results.json`: state, attacks, storage/gas schedule, live-growth budgets, split totals, recovery latency, and gates;
- `source-hashes.json`: package and dependency hashes.

The focused Solidity suite is configured canonically for solc 0.8.30, Prague, optimizer 200, and via-IR:

```sh
cd research/two-call-state/solidity
forge test
```

`testMeasureRetainedHarnessOverhead` writes `outputs/harness-gas.json`. Re-run `run.py` afterward to ingest it. Those gasleft deltas cover the state harness plus deterministic binding mock and exclude the v0.3 verifier.

## State design

`RobustTwoCallState` has one mapping entry per full-width nullifier key and one immutable consumer. Its checkpoint has one packed metadata slot and six two-slot digests: statement, global data, checkpoint, proof, continuation, and root. It stores no proof bytes or witness and publishes no reusable fact. A deployment selects an immutable Part A split from 8 through 16.

`AtomicTwoCallPool` demonstrates the consumer boundary. It reconstructs the statement over chain, pool, both nullifier limbs, both root limbs, recipient, and amount. B verifies, deletes continuation state, marks the nullifier, and transfers value in one transaction. A payment failure reverts all effects, and the consumer lock blocks payment reentrancy.

Expiry is `block.number >= expiresAt`. Identical live A submissions are idempotent; different submissions for the same nullifier reject. After expiry, a valid A replaces the old checkpoint, while anyone may clean it. Root pin counts prevent root-history aging while checkpoint state remains.

Machine-readable semantics are in `transitions.json` and `invariants.json`; the exact ten-to-ten test/model mapping is in `attacks.json`.

## Measurements and classifications

- Checkpoint struct: 13 slots.
- Worst incremental live state: 14 slots/448 logical bytes per distinct active nullifier, including one distinct-root pin slot.
- Prague schedule under explicit assumptions: 329,400 Part A storage gas; 79,200 matched-B gross deletion gas; 100,200 cleanup gross deletion gas; up to 72,000 clear-refund accrual reported but never used for caps.
- Canonical recovery: 256 blocks exactly; 3,072 seconds is a 12-second-block projection.
- Live growth: reported for 1/10/100 ETH at 10/20/50 gwei and for the 2^24 block cap. An attacker still needs distinct unspent nullifiers and valid Part A proofs.
- A/B totals: retained V9 component-model PROJECTION for active/uniform64/uniform96, never relabeled as SP-72 measurements.

Every retained row misses the robust 12M-per-call and 20M-total gate. The projection gate is **FAIL**. Exact full-path binding/gas is **NOT_EVALUATED**, external cryptographic acceptance is **OPEN**, and promotion is **DO_NOT_PROMOTE**.
