#!/usr/bin/env python3
import json
import sys
from pathlib import Path

result = json.loads(Path(sys.argv[1]).read_text())
assert result["schema_version"] == 1
assert result["candidate_id"] == "C40"
assert result["spike_id"] == "SP-53"
assert result["status"] == "DEFERRED"
assert result["evidence_class"] == "SOURCE_WATCH_NOT_MEASUREMENT"
assert result["upstream"]["commit"] == "3152b14a89067c83775a8076cc262ffc48a1fd7c"
assert result["upstream"]["source_sha256"] == "51e2140ab4f0840362a30f5a37fbac9ba598e7c31ddc2de01a7932b170dd7aff"
assert result["upstream"]["source_pin_verified"] is True
assert result["source_api_checks"] == {
    "circle_pcs_implements_pcs": True,
    "value_field_requires_complex_extendable": True,
    "zk": False,
    "hiding": False,
    "hiding_circle_pcs_exposed": False,
}
assert result["promotion_checks"]["documented_noninteractive_hiding_construction"] is False
assert result["promotion_checks"]["compatible_frozen_h0_field_relation"] is False
assert result["promotion_checks"]["credible_matching_evm_verifier"] is False
assert result["promotion_checks"]["comparable_non_hiding_lower_bound_without_relation_translation"] is False
assert result["implementation_action"] == "NO_CODE"
assert result["native_proof_executed"] is False
assert result["relation_gate"] == {
    "accepted_sp10_relation_available": False,
    "control_relation": "frozen-v0.3/H0",
    "upstream_smoke_implements_relation": False,
}
assert result["privacy_finalist"] is False
assert result["pqtc_measurement"] is False
