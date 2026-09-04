# Gas schedules

Calculate the active EIP-7623 floor and the 64/64 and 96/96 scenario floors:

```sh
python3 research/harness/gas-schedules/gas_schedules.py \
  --byte-counts --zero-bytes 100 --nonzero-bytes 500 \
  --execution-gas 1000000
```

Pass `--contract-creation` when calldata is initcode; the calculator then includes the 32,000 creation charge and EIP-3860 word metering in the standard branch. Binary input may be supplied with `--calldata`, or exact bytes with `--calldata-hex`.
