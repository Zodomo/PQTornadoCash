#!/usr/bin/env python3
from __future__ import annotations

import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
raw = json.loads((HERE / "outputs/foundry-gas.json").read_text())
result_path = HERE / "outputs/results.json"
result = json.loads(result_path.read_text())
if raw.get("schema") != "sp12-foundry-queue-gas-v1":
    raise SystemExit("unexpected queue gas schema")
if raw.get("indices") != list(range(256)):
    raise SystemExit("queue gas sweep must contain exactly indices 0..255")
samples = raw.get("enqueue_gas")
if not isinstance(samples, list) or len(samples) != 256 or any(not isinstance(value, int) or value <= 0 for value in samples):
    raise SystemExit("invalid queue enqueue gas samples")
result["costs"]["queue_user_deposit_gas"] = {
    "value": int(statistics.median(samples)),
    "p50": int(statistics.median(samples)),
    "best": min(samples),
    "worst": max(samples),
    "samples": samples,
    "status": "PASS_EXACT_FOUNDRY_GASLEFT_DELTA",
    "measurement_class": "EXACT_MEASUREMENT",
    "call_accounting": "ABI encoding precedes gasleft delta; low-level call and return-data copying included",
}
result["foundry_harness"]["status"] = "PASS_EXACT_QUEUE_ENQUEUE_MEASUREMENT"
result["foundry_harness"]["retained_output"] = "outputs/foundry-gas.json"
# A queue-only number cannot establish amortized break-even without a real backend.
for row in result["economics"].values():
    row["queue_enqueue_gas_p50"] = int(statistics.median(samples))
    row["break_even_vs_direct"] = "NOT_EVALUATED"
status_path = HERE / "status.json"
status = json.loads(status_path.read_text())
status["queue_user_deposit_gas"] = "PASS_EXACT_FOUNDRY_GASLEFT_DELTA"
status_path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n")
result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
print(json.dumps(result, sort_keys=True))
