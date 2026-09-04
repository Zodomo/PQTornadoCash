# SP-11 Merkle shape research package

Run the deterministic package from the repository root:

```sh
python3 research/candidates/merkle-shape/run.py
```

The command prints one JSON document and retains the same document at `outputs/results.json`. It does not compile contracts or benchmark gas. It validates the frozen v0.3 corpus envelope, exercises generalized accumulator semantics, checks incremental/full-tree parity, and emits the complete insertion and boundary transition sweep.

The separate exact gas command is:

```sh
cd research/candidates/merkle-shape/solidity
./run-gas.sh
```

That command is intentionally separate because it executes hundreds of expensive H0 calls. It writes `outputs/foundry-gas.json`, rejects an incomplete sweep, then updates only the two implemented H0 variant gas fields. The model result keeps every unrun gas field `NOT_EVALUATED`.

Exact recomputation of all 1,000 frozen H0 corpus roots is prepared separately as
`cd research/candidates/merkle-shape/solidity && ./run-parity.sh`. The Python model
does not relabel its SHA-512 shape checks as H0 parity.

Security interpretation is fixed: binary depth 20 remains the custody design. Higher arity is executable shape research only; no SP-10 replacement is security-qualified. Packed/precomputed universal H0 zero constants are infeasible because the zero leaf is scope-bound.
