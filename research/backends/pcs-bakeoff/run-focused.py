#!/usr/bin/env python3
import argparse
import json
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--repo-root", required=True)
parser.add_argument("--work", required=True)
args = parser.parse_args()
root = Path(args.repo_root).resolve()
work = Path(args.work).resolve()
(work / "source").mkdir(parents=True, exist_ok=False)
(work / "build").mkdir(parents=True, exist_ok=False)

packages = {
    "C20": root / "research/candidates/C20-hvzk-whir",
    "C30": root / "research/candidates/C30-stir",
    "C40": root / "research/candidates/C40-circle",
}
results = {}
for candidate, package in packages.items():
    path = package / "outputs/latest.json"
    if not path.is_file():
        raise SystemExit(f"missing {candidate} result: run {package / 'run-focused.sh'} first")
    subprocess.run(["python3", str(package / "validate-result.py"), str(path)], check=True)
    results[candidate] = json.loads(path.read_text())

assert results["C20"]["proxy_geometry"]["polynomial_elements"] == 4096
assert results["C30"]["proxy_geometry"]["polynomial_elements"] == 4096
assert results["C20"]["proxy_geometry"]["opened_points"] == 1
assert results["C30"]["proxy_geometry"]["opened_points"] == 1
assert results["C20"]["compiled_api_checks"]["zk"] is True
assert results["C30"]["compiled_api_checks"]["zk"] is False
assert results["C40"]["source_api_checks"]["zk"] is False
assert all(result["pqtc_measurement"] is False for result in results.values())

summary = {
    "schema_version": 1,
    "package": "pcs-bakeoff",
    "status": "COMPLETE_NON_PQTC_CONTROLS",
    "evidence_class": "UPSTREAM_BASELINE_NOT_PQTC_AND_SOURCE_WATCH",
    "upstream_pin": "3152b14a89067c83775a8076cc262ffc48a1fd7c",
    "relation_control": "frozen-v0.3/H0",
    "accepted_sp10_relation_available": False,
    "comparability": {
        "c20_c30_matched_public_polynomial_elements": 4096,
        "c20_c30_matched_opened_points": 1,
        "same_complete_pqtc_relation": False,
        "security_models_matched": False,
        "timing_benchmark_claimed": False,
    },
    "candidates": {
        "C20": {
            "status": results["C20"]["status"],
            "verified_runs": [run["verified"] for run in results["C20"]["runs"]],
            "repeat_proofs_differ": results["C20"]["repeat_proofs_differ"],
            "zk": results["C20"]["compiled_api_checks"]["zk"],
            "pqtc_measurement": False,
        },
        "C30": {
            "status": results["C30"]["status"],
            "verified": results["C30"]["verified"],
            "zk": results["C30"]["compiled_api_checks"]["zk"],
            "pqtc_measurement": False,
        },
        "C40": {
            "status": results["C40"]["status"],
            "implementation_action": results["C40"]["implementation_action"],
            "zk": results["C40"]["source_api_checks"]["zk"],
            "pqtc_measurement": False,
        },
    },
    "privacy_finalists": [],
    "eligible_for_pqtc_ranking": [],
    "pqtc_measurement": False,
}
print(json.dumps(summary, indent=2, sort_keys=True))
