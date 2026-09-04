# Report generator

The standard-library report tool validates run records against the repository root schema, generates and verifies deterministic evidence manifests, and emits traceable CSV summaries.

```sh
python3 research/harness/report-generator/report_generator.py validate-run research/runs/run.json
python3 research/harness/report-generator/report_generator.py manifest research/runs --output research/final/evidence-manifest.json
python3 research/harness/report-generator/report_generator.py verify-manifest research/final/evidence-manifest.json
python3 research/harness/report-generator/report_generator.py summary research/runs \
  --output research/summaries/all-runs.csv \
  --candidate-output research/summaries/candidate-summary.csv
python3 research/harness/report-generator/report_generator.py keccak-self-test
```

Manifest hashing uses Ethereum Keccak-256 (`0xc5d246…a470` for empty input), not NIST SHA3-256. The manifest explicitly excludes its own path because a file cannot contain stable hashes of itself.
