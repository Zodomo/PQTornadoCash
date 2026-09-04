# benchctl

Use the executable dispatcher from the repository root:

```sh
research/harness/benchctl/benchctl gas --calldata proof-calldata.bin --execution-gas 500000
research/harness/benchctl/benchctl ledger --raw-proof proof.bin --abi-calldata calldata.bin --sections sections.json
research/harness/benchctl/benchctl detect --evm-revision cancun
research/harness/benchctl/benchctl validate-run research/runs/run.json
research/harness/benchctl/benchctl manifest research/runs --output research/final/evidence-manifest.json
research/harness/benchctl/benchctl verify-manifest research/final/evidence-manifest.json
research/harness/benchctl/benchctl summary research/runs --output research/summaries/all-runs.csv --candidate-output research/summaries/candidate-summary.csv
research/harness/benchctl/benchctl keccak-self-test
```

All successful responses and failures are JSON. Invalid results return a nonzero status without discarding detailed validation, reconciliation, or digest failures.
