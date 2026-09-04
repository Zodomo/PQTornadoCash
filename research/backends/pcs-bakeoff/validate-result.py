#!/usr/bin/env python3
import json
import sys
from pathlib import Path

result = json.loads(Path(sys.argv[1]).read_text())
assert result["schema_version"] == 1
assert result["package"] == "pcs-bakeoff"
assert result["status"] == "COMPLETE_NON_PQTC_CONTROLS"
assert result["evidence_class"] == "UPSTREAM_BASELINE_NOT_PQTC_AND_SOURCE_WATCH"
assert result["upstream_pin"] == "3152b14a89067c83775a8076cc262ffc48a1fd7c"
assert result["relation_control"] == "frozen-v0.3/H0"
assert result["accepted_sp10_relation_available"] is False
assert result["comparability"] == {
    "c20_c30_matched_opened_points": 1,
    "c20_c30_matched_public_polynomial_elements": 4096,
    "same_complete_pqtc_relation": False,
    "security_models_matched": False,
    "timing_benchmark_claimed": False,
}
assert result["candidates"]["C20"]["status"] == "DEFERRED"
assert result["candidates"]["C20"]["verified_runs"] == [True, True]
assert result["candidates"]["C20"]["repeat_proofs_differ"] is True
assert result["candidates"]["C20"]["zk"] is True
assert result["candidates"]["C30"]["status"] == "BENCHMARK_ONLY"
assert result["candidates"]["C30"]["verified"] is True
assert result["candidates"]["C30"]["zk"] is False
assert result["candidates"]["C40"] == {
    "implementation_action": "NO_CODE",
    "pqtc_measurement": False,
    "status": "DEFERRED",
    "zk": False,
}
assert result["privacy_finalists"] == []
assert result["eligible_for_pqtc_ranking"] == []
assert result["pqtc_measurement"] is False
