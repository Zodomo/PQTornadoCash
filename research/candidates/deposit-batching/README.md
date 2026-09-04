# SP-12 permissionless deposit batching

Run the deterministic state-machine experiment from the repository root:

```sh
python3 research/candidates/deposit-batching/run.py
```

The command prints one machine JSON document and retains it at `outputs/results.json`. It executes every batch size (8/16/32/64/256), all named safety mutations, both timeout escapes, arbitrary-caller finalization, custody conservation, arrival-rate latency, and source hashing.

Queue enqueue gas is intentionally isolated:

```sh
cd research/candidates/deposit-batching/solidity
./run-gas.sh
```

The parser requires exactly 256 successful indexed samples before labeling the user path an exact measurement. It does not measure or invent batch-finalizer gas because no trustless proof verifier exists.

`ModelProofBackend` is not a PCS, STARK, or cryptographic proof. It is an executable oracle for the public transition interface. Production finalization with `NoProofBackend` always rejects. The candidate remains `DEFERRED/STOP` regardless of enqueue gas until a real trustless backend and complete amortized break-even both pass. There is no trusted or always-online operator.
