# Proof ledger

Create a JSON object whose keys are proof section names and whose values are exact byte counts, then run:

```sh
python3 research/harness/proof-ledger/proof_ledger.py \
  --raw-proof proof.bin --abi-calldata calldata.bin --sections sections.json
```

The command fails unless section bytes equal the raw proof length and reports exact ABI zero, nonzero, and overhead byte counts.
