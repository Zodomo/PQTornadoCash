#!/usr/bin/env python3
import json
import sys
from pathlib import Path

PIN = "3152b14a89067c83775a8076cc262ffc48a1fd7c"
result = json.loads(Path(sys.argv[1]).read_text())
assert result["schema_version"] == 1
assert result["candidate_id"] == "C20"
assert result["status"] == "DEFERRED"
assert result["evidence_class"] == result["measurement_label"] == "UPSTREAM_BASELINE_NOT_PQTC"
assert result["upstream"]["commit"] == PIN
assert result["upstream"]["source_hashes_verified_by_runner"] is True
assert result["compiled_api_checks"]["hiding_whir_pcs"] is True
assert result["compiled_api_checks"]["rng_trait_gate"] == "CryptoRng + Send + Sync"
assert result["compiled_api_checks"]["fresh_os_seed_per_proof"] is True
assert result["compiled_api_checks"]["zk"] is True
assert result["proxy_geometry"]["polynomial_elements"] == 4096
assert result["proxy_geometry"]["implements_frozen_pqtc_relation"] is False
assert len(result["runs"]) == 2
assert all(run["verified"] and run["proof_bytes"] > 0 for run in result["runs"])
assert result["runs"][0]["proof_sha256"] != result["runs"][1]["proof_sha256"]
assert result["repeat_proofs_differ"] is True
assert result["peak_rss_bytes"] > 0
assert result["security_report_scope"] == "UPSTREAM_DIAGNOSTIC_HIDING_BASE_CASE_ONLY_NOT_END_TO_END"
assert result["relation_gate"] == {
    "accepted_sp10_relation_available": False,
    "control_relation": "frozen-v0.3/H0",
    "upstream_smoke_implements_relation": False,
}
assert result["integration_gates"] == {
    "sp02_native_malformed_proof_panic": "FAIL",
    "sp10_accepted_relation": "MISSING",
    "matching_evm_verifier": "MISSING",
    "exact_transcript_qrom_reduction": "MISSING",
    "external_cryptographic_review": "NOT_PERFORMED",
}
assert result["pqtc_measurement"] is False
