#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
raw_path = HERE / "outputs/foundry-gas.json"
result_path = HERE / "outputs/results.json"
raw = json.loads(raw_path.read_text())
result = json.loads(result_path.read_text())
if raw.get("schema") != "sp11-foundry-gas-v1":
    raise SystemExit("unexpected Foundry result schema")
indices = raw["indices_0_255"]
if indices != list(range(256)):
    raise SystemExit("Foundry sweep is not exactly 0..255")
boundaries = raw["boundary_indices"]
expected = [x for k in range(21) for x in ((1 << k) - 1, 1 << k)]
if boundaries != expected:
    raise SystemExit("Foundry power-of-two boundary set is incomplete")
accepted = raw["boundary_insert_accepted"]
if accepted != [True] * 41 + [False]:
    raise SystemExit("capacity boundary behavior mismatch")
for variant, key in ((result["variants"][0], "unbounded_insert_gas_0_255"), (result["variants"][1], "bounded_insert_gas_0_255")):
    values = raw[key]
    if len(values) != 256 or any(not isinstance(value, int) or value <= 0 for value in values):
        raise SystemExit("invalid gas sweep")
    variant["foundry_gas"] = {
        "status": "PASS_EXACT_FOUNDRY_GASLEFT_DELTA",
        "measurement_class": "EXACT_MEASUREMENT",
        "samples": values,
        "best": min(values),
        "worst": max(values),
    }
result["foundry_harness"]["status"] = "PASS_EXACT_MEASUREMENT"
result["foundry_harness"]["retained_output"] = "outputs/foundry-gas.json"
status_path = HERE / "status.json"
status = json.loads(status_path.read_text())
status["gas_sweep"] = "PASS_EXACT_FOUNDRY_GASLEFT_DELTA"
status_path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n")
result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
print(json.dumps(result, sort_keys=True))
