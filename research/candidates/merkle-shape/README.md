# SP-11 Merkle shape research package

Run the deterministic package from the repository root:

```sh
python3 research/candidates/merkle-shape/run.py
```

The command prints one JSON document and retains the same document at `outputs/results.json`. It does not compile contracts or benchmark gas. It validates the frozen v0.3 corpus envelope, exercises generalized accumulator semantics, checks incremental/full-tree parity, and emits the complete insertion and boundary transition sweep.

The separate isolated gas-diagnostic command is:

```sh
cd research/candidates/merkle-shape/solidity
./run-gas.sh
```

That command executes hundreds of expensive H0 calls. It writes `outputs/foundry-gas.json`; the main generator validates and preserves the artifact on every rerun. Gas-left samples and internal `new` deltas are diagnostics only, not complete transaction gas: intrinsic gas, calldata gas, EIP-7623 floor effects, and receipts are omitted.

Exact recomputation of all 1,000 frozen H0 corpus roots runs as
`cd research/candidates/merkle-shape/solidity && ./run-parity.sh`. A successful
test retains `outputs/foundry-parity.json`; the generator validates its profile,
case count, PASS status, and corpus SHA-256 before reporting parity PASS. Missing
or malformed evidence is never inferred from console output.

Security interpretation is fixed: binary depth 20 remains the custody design. Higher arity is executable shape research only; no SP-10 replacement is security-qualified. Packed/precomputed universal H0 zero constants are infeasible because the zero leaf is scope-bound.
