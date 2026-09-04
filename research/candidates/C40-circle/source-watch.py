#!/usr/bin/env python3
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

PIN = "3152b14a89067c83775a8076cc262ffc48a1fd7c"
PCS_SHA256 = "51e2140ab4f0840362a30f5a37fbac9ba598e7c31ddc2de01a7932b170dd7aff"
REPOSITORY = "https://github.com/Plonky3/Plonky3"

parser = argparse.ArgumentParser()
parser.add_argument("--work", required=True)
args = parser.parse_args()
work = Path(args.work)
source = work / "source"
build = work / "build"
build.mkdir(parents=True, exist_ok=False)
subprocess.run(["git", "clone", "--quiet", "--filter=blob:none", REPOSITORY, str(source)], check=True)
subprocess.run(["git", "-C", str(source), "checkout", "--quiet", "--detach", PIN], check=True)
head = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
assert head == PIN

pcs_path = source / "circle/src/pcs.rs"
pcs_bytes = pcs_path.read_bytes()
pcs_hash = hashlib.sha256(pcs_bytes).hexdigest()
assert pcs_hash == PCS_SHA256
pcs = pcs_bytes.decode()

impl_match = re.search(
    r"impl<Val, InputMmcs, FriMmcs, Challenge, Challenger>\s+Pcs<Challenge, Challenger>\s+for CirclePcs<Val, InputMmcs, FriMmcs>(?P<body>.*?)\n}\n",
    pcs,
    re.S,
)
assert impl_match, "pinned CirclePcs Pcs implementation not found"
body = impl_match.group("body")
zk_false = re.search(r"\bconst\s+ZK:\s*bool\s*=\s*false\s*;", body) is not None
complex_extendable = re.search(r"\bVal:\s*ComplexExtendable\b", body) is not None
hiding_adapter_exposed = re.search(r"\bHidingCirclePcs\b", pcs) is not None
assert zk_false
assert complex_extendable
assert not hiding_adapter_exposed

result = {
    "schema_version": 1,
    "candidate_id": "C40",
    "spike_id": "SP-53",
    "status": "DEFERRED",
    "evidence_class": "SOURCE_WATCH_NOT_MEASUREMENT",
    "upstream": {
        "repository": REPOSITORY,
        "commit": PIN,
        "package": "p3-circle",
        "api": "CirclePcs",
        "source_path": "circle/src/pcs.rs",
        "source_sha256": pcs_hash,
        "source_pin_verified": True,
    },
    "source_api_checks": {
        "circle_pcs_implements_pcs": True,
        "value_field_requires_complex_extendable": complex_extendable,
        "zk": False,
        "hiding": False,
        "hiding_circle_pcs_exposed": hiding_adapter_exposed,
    },
    "promotion_checks": {
        "public_source": True,
        "precise_security_paper": True,
        "working_native_prover_verifier_in_upstream": True,
        "documented_noninteractive_hiding_construction": False,
        "compatible_frozen_h0_field_relation": False,
        "credible_matching_evm_verifier": False,
        "comparable_non_hiding_lower_bound_without_relation_translation": False,
    },
    "implementation_action": "NO_CODE",
    "native_proof_executed": False,
    "reason": "Pinned CirclePcs is non-hiding and requires ComplexExtendable values; frozen H0 uses BabyBear/two-adic geometry, so a matched lower bound would require an unaccepted relation/field translation.",
    "relation_gate": {
        "accepted_sp10_relation_available": False,
        "control_relation": "frozen-v0.3/H0",
        "upstream_smoke_implements_relation": False,
    },
    "privacy_finalist": False,
    "pqtc_measurement": False,
}
print(json.dumps(result, indent=2, sort_keys=True))
