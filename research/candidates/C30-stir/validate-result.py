#!/usr/bin/env python3
import json
import sys
from pathlib import Path

PIN = "3152b14a89067c83775a8076cc262ffc48a1fd7c"
result = json.loads(Path(sys.argv[1]).read_text())
assert result["schema_version"] == 1
assert result["candidate_id"] == "C30"
assert result["spike_id"] == "SP-52"
assert result["status"] == "BENCHMARK_ONLY"
assert result["evidence_class"] == result["measurement_label"] == "UPSTREAM_BASELINE_NOT_PQTC"
assert result["upstream"]["commit"] == PIN
assert result["upstream"]["api"] == "TwoAdicStirPcs"
assert result["upstream"]["source_hashes_verified_by_runner"] is True
assert result["compiled_api_checks"] == {
    "two_adic_stir_pcs": True,
    "zk": False,
    "hiding": False,
}
assert result["proxy_geometry"]["log_degree"] == 12
assert result["proxy_geometry"]["polynomial_elements"] == 4096
assert result["proxy_geometry"]["matrix_width"] == 1
assert result["proxy_geometry"]["matched_with_candidate"] == "C20"
assert result["proxy_geometry"]["implements_frozen_pqtc_relation"] is False
assert result["verified"] is True
assert result["proof_bytes"] > 0
assert len(result["proof_sha256"]) == 64
assert result["commit_time_ns"] > 0
assert result["open_time_ns"] > 0
assert result["native_verify_time_ns"] > 0
assert result["peak_rss_bytes"] > 0
assert result["relation_gate"] == {
    "accepted_sp10_relation_available": False,
    "control_relation": "frozen-v0.3/H0",
    "upstream_smoke_implements_relation": False,
}
assert result["privacy_finalist"] is False
assert result["pqtc_measurement"] is False
