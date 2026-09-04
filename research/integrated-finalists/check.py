#!/usr/bin/env python3
"""Deterministic, fail-closed SP-80 bundle eligibility checker."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "research" / "integrated-finalists"
MANIFEST_PATH = PACKAGE / "manifest.json"
RESULT_PATH = PACKAGE / "outputs" / "results.json"
STATUS_PATH = PACKAGE / "status.json"
GATES = ("semantic", "hiding", "security", "native", "evm", "calldata", "gas", "source_binding")
DECISION = "CURRENT_RESEARCH_FRONTIER_NO_VIABLE_NEXT_BUILD"
MISSING = object()

# Rules deliberately live in executable code rather than in the mutable evidence
# manifest. Updating a source hash cannot turn a blocked value into a passing value.
# A rule passes only on exact equality; absent/null evidence fails closed.
COMPONENT_RULES: dict[str, dict[str, Any]] = {
    "fixed_compression": {
        "name": "SP-10 fixed-length application compression",
        "rules": {
            "semantic": ("status", "/verdict", "AIR_CANDIDATE"),
            "hiding": ("status", "/securityQualified", True),
            "security": ("status", "/securityQualified", True),
            "native": ("status", "/verdict", "AIR_CANDIDATE"),
            "evm": ("status", "/verificationCoverage/solidityParity/fullBundleCovered", True),
            "calldata": ("status", "/integratedCalldataGate", "PASS"),
            "gas": ("status", "/integratedGasGate", "PASS"),
            "source_binding": ("status", "/candidatePromotionAuthorized", True),
        },
    },
    "air_geometry": {
        "name": "SP-20 narrow low-degree AIR geometry",
        "rules": {
            "semantic": ("status", "/status", "PASS"),
            "hiding": ("status", "/productionReady", True),
            "security": ("status", "/productionReady", True),
            "native": ("status", "/proofResult", "PASS"),
            "evm": ("status", "/pcsIntegration", "PASS"),
            "calldata": ("status", "/calldataResult", "PASS"),
            "gas": ("status", "/gasResult", "PASS"),
            "source_binding": ("status", "/productionReady", True),
        },
    },
    "transcript": {
        "name": "SP-30 batched Keccak transcript",
        "rules": {
            "semantic": ("status", "/gate/result", "PASS"),
            "hiding": ("status", "/hidingGate", "PASS"),
            "security": ("status", "/gate/integrationBlocked", False),
            "native": ("status", "/classification", "FINALIST"),
            "evm": ("status", "/fullPathEvmGasDelta", "PASS"),
            "calldata": ("status", "/canonicalIntegratedCodec", "PASS"),
            "gas": ("status", "/fullPathEvmGasDelta", "PASS"),
            "source_binding": ("status", "/custodyIntegration", True),
        },
    },
    "hiding_fri": {
        "name": "SP-50 hiding FRI Pareto profile",
        "rules": {
            "semantic": ("status", "/winnerStatus", "PASS"),
            "hiding": ("status", "/securityQualified", True),
            "security": ("status", "/securityQualified", True),
            "native": ("status", "/winnerStatus", "PASS"),
            "evm": ("status", "/evmVerification", "PASS"),
            "calldata": ("status", "/exactAbiCalldata", "PASS"),
            "gas": ("status", "/winnerStatus", "PASS"),
            "source_binding": ("status", "/productionChange", True),
        },
    },
    "hvzk_whir": {
        "name": "SP-51 HVZK-WHIR",
        "rules": {
            "semantic": ("status", "/blockers/sp10AcceptedRelation", "PASS"),
            "hiding": ("status", "/privacyFinalist", True),
            "security": ("status", "/integrationAllowed", True),
            "native": ("status", "/pqtcMeasurement", True),
            "evm": ("status", "/blockers/matchingEvmVerifier", "PASS"),
            "calldata": ("status", "/exactAbiCalldata", "PASS"),
            "gas": ("status", "/exactEvmGas", "PASS"),
            "source_binding": ("status", "/integrationAllowed", True),
        },
    },
    "structured_relation": {
        "name": "SP-21 repeated structured R1CS/CCS relation",
        "rules": {
            "semantic": ("status", "/schema/relationImplementation", True),
            "hiding": ("status", "/productionReady", True),
            "security": ("status", "/productionReady", True),
            "native": ("status", "/proofResult", "PASS"),
            "evm": ("status", "/backendIntegrations/spartanWhir", "PASS"),
            "calldata": ("status", "/calldataResult", "PASS"),
            "gas": ("status", "/gasResult", "PASS"),
            "source_binding": ("status", "/productionReady", True),
        },
    },
    "spartan_whir": {
        "name": "SP-60 Spartan-WHIR/HVZK backend",
        "rules": {
            "semantic": ("status", "/native_exact_pqtc_relation", "PASS"),
            "hiding": ("status", "/privacy_finalist", True),
            "security": ("status", "/overall", "PASS"),
            "native": ("status", "/native_end_to_end_reproduction", "PASS"),
            "evm": ("status", "/full_evm_spartan", "PASS"),
            "calldata": ("status", "/exact_abi_calldata", "PASS"),
            "gas": ("status", "/standalone_solidity_whir_gas_measurement", "PASS"),
            "source_binding": ("status", "/license_clear_for_vendoring", True),
        },
    },
    "recursion": {
        "name": "SP-61 transparent recursion",
        "rules": {
            "semantic": ("status", "/recursive_keccak_zk", True),
            "hiding": ("status", "/hiding_whir_adapter_in_circuit", True),
            "security": ("status", "/mandated_dependency_compatible", True),
            "native": ("status", "/integrated", True),
            "evm": ("status", "/evm_verifier", True),
            "calldata": ("status", "/exact_abi_calldata", "PASS"),
            "gas": ("status", "/exact_evm_gas", "PASS"),
            "source_binding": ("status", "/privacy_finalist", True),
        },
    },
    "flock_veil": {
        "name": "SP-62 Keccak relation plus Flock/VEIL",
        "rules": {
            "semantic": ("status", "/flock_current_keccak", True),
            "hiding": ("status", "/flock_zero_knowledge", True),
            "security": ("status", "/privacy_finalist", True),
            "native": ("status", "/historical_batch_44_result", "PASS"),
            "evm": ("status", "/flock_evm_verifier", True),
            "calldata": ("status", "/exact_abi_calldata", "PASS"),
            "gas": ("status", "/historical_batch_44_published_measurement", True),
            "source_binding": ("status", "/integrated", True),
        },
    },
    "two_call_state": {
        "name": "SP-72 robust two-call state handling",
        "rules": {
            "semantic": ("status", "/full_path_binding", "PASS"),
            "hiding": ("status", "/security_qualified", True),
            "security": ("status", "/external_cryptographic_acceptance", "PASS"),
            "native": ("status", "/full_path_binding", "PASS"),
            "evm": ("status", "/full_path_binding", "PASS"),
            "calldata": ("status", "/full_path_binding", "PASS"),
            "gas": ("status", "/gas_gate", "PASS"),
            "source_binding": ("status", "/promotion", "PASS"),
        },
    },
    "runtime_binding": {
        "name": "Two-layer proof/deployment source binding",
        "rules": {gate: ("status", "/deploymentReady", True) for gate in GATES},
    },
    "public_statement": {
        "name": "Pool public-statement reconstruction",
        "rules": {gate: ("status", "/minimalSafe/productionReady", True) for gate in GATES},
    },
    "digest_width": {
        "name": "Security-qualified proof commitment/digest width",
        "rules": {gate: ("status", "/security/external_cryptographic_acceptance", "PASS") for gate in GATES},
    },
    "cryptanalysis_review": {
        "name": "Independent cryptographic review",
        "rules": {gate: ("status", "/integration_authorized", True) for gate in GATES},
    },
}

CHECKLIST = (
    "note generation",
    "commitment/nullifier derivation",
    "depth-20 tree/path",
    "full witness construction",
    "hiding proof generation",
    "native verification",
    "canonical proof codec",
    "Solidity proof verification",
    "pool statement reconstruction",
    "nullifier consumption",
    "recipient/relayer payout in a harness",
    "exact ABI transaction measurement",
    "source-bound parameter manifest",
)

COMMON = ("runtime_binding", "public_statement", "digest_width", "cryptanalysis_review")
BUNDLES: dict[str, dict[str, Any]] = {
    "A": {
        "name": "optimized Poseidon2 compression + vertical AIR + hiding FRI",
        "components": ("fixed_compression", "air_geometry", "transcript", "hiding_fri") + COMMON,
        "alternatives": (),
        "last": "SP-10 Stage-A benchmark package; no compression candidate passed promotion to AIR",
        "lastEvidence": ("fixed_compression", "result"),
        "revive": [
            "SP-10 promotes one fixed compression after complete three-language parity, misuse tests, and independent cryptanalysis.",
            "SP-20 then produces a frozen vertical AIR for that exact relation.",
            "SP-30 and SP-50 close transcript/QROM/MMCS/advisory gates and a direct Solidity verifier passes exact ABI gas/calldata gates.",
            "A non-empty deployment-ready two-layer source-binding manifest is measured for the integrated path.",
        ],
    },
    "B": {
        "name": "optimized compression/AIR + HVZK-WHIR",
        "components": ("fixed_compression", "air_geometry", "transcript", "hvzk_whir") + COMMON,
        "alternatives": (),
        "last": "upstream HidingWhirPcs native smoke only; no accepted PQTC relation or matching EVM verifier",
        "lastEvidence": ("hvzk_whir", "result"),
        "revive": [
            "SP-10 and SP-20 deliver an accepted exact PQTC relation and AIR geometry.",
            "HVZK-WHIR is integrated on that relation with an exact transcript reduction and independent review.",
            "A matching modular Solidity verifier, canonical codec, exact calldata, and full transaction gas are measured.",
            "Malformed-proof panic containment and deployment source binding pass.",
        ],
    },
    "C": {
        "name": "structured relation + Spartan-WHIR/HVZK",
        "components": ("fixed_compression", "structured_relation", "transcript", "spartan_whir") + COMMON,
        "alternatives": (),
        "last": "upstream native full-ZK maturity and standalone plain-WHIR build controls only; exact PQTC relation absent",
        "lastEvidence": ("spartan_whir", "result"),
        "revive": [
            "SP-10 promotes fixed compression and SP-21 implements/freeze-tests the repeated R1CS/CCS relation.",
            "Spartan-WHIR reproduces end to end on that exact relation with hiding and security review.",
            "Full Spartan plus hiding-WHIR EVM verification, codec, calldata, and gas gates pass at license-clear pins.",
            "Integrated statement and deployment source binding pass.",
        ],
    },
    "D": {
        "name": "optimized inner proof + transparent recursion",
        "components": ("recursion", "transcript") + COMMON,
        "alternatives": (("hiding_fri", "hvzk_whir", "spartan_whir"),),
        "last": "upstream recursive Fibonacci architecture smoke only; no PQTC hiding-inner adapter or EVM verifier",
        "lastEvidence": ("recursion", "result"),
        "revive": [
            "At least one exact-PQTC hiding inner proof passes all eight component gates.",
            "The recursive relation verifies that exact proof with mandated dependency pins and preserves hiding.",
            "A transparent outer proof and one-transaction Solidity verifier pass canonical codec, calldata, and gas gates.",
            "Recursion-specific cryptanalysis and two-layer source binding pass.",
        ],
    },
    "E": {
        "name": "Keccak relation + Flock + ZK/outer compression",
        "components": ("structured_relation", "transcript", "flock_veil") + COMMON,
        "alternatives": (),
        "last": "source check and experimental non-PQTC VEIL PoCs; historical Flock batch-44 run failed at the pin",
        "lastEvidence": ("flock_veil", "result"),
        "revive": [
            "SP-62 passes with a current Keccak relation, zero knowledge, and reproducible security-qualified capacity measurements.",
            "A reviewed Flock-to-VEIL or transparent outer-compression adapter is implemented on the exact PQTC relation.",
            "A complete EVM verifier, canonical codec, exact calldata, and full transaction gas pass.",
            "Integrated statement and deployment source binding pass.",
        ],
    },
    "F": {
        "name": "robust two-call fallback",
        "components": ("two_call_state", "transcript") + COMMON,
        "alternatives": (("hiding_fri", "hvzk_whir", "spartan_whir", "recursion", "flock_veil"),),
        "last": "SP-72 research state harness passed 10 attack-model checks, but exact proof binding is untested and projected gas fails",
        "lastEvidence": ("two_call_state", "result"),
        "revive": [
            "One strongest security-qualified exact-PQTC proof is measured and shown unable to fit one call for intrinsic, attributable reasons.",
            "That exact proof is bound into SP-72 state transitions and all state/codec/malformed-input security gates pass.",
            "Both exact ABI transactions pass gas and calldata limits on the canonical EVM profile.",
            "Integrated statement, payout, nullifier, and deployment source binding pass.",
        ],
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def pointer(document: Any, value: str) -> Any:
    current = document
    if value == "":
        return current
    for token in value.removeprefix("/").split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or token not in current:
            return MISSING
        current = current[token]
    return current


def printable(value: Any) -> Any:
    return None if value is MISSING else value


def load_and_verify_manifest() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    manifest = load_json(MANIFEST_PATH)
    if manifest.get("schema") != "pqtc.sp80.eligibility-manifest.v1":
        raise ValueError("unexpected SP-80 manifest schema")
    if set(manifest.get("components", {})) != set(COMPONENT_RULES):
        raise ValueError("manifest component set does not match executable rules")
    documents: dict[str, dict[str, Any]] = {}
    for component_id, component in manifest["components"].items():
        records = component.get("records")
        if not isinstance(records, dict) or set(records) != {"status", "manifest", "result"}:
            raise ValueError(f"{component_id}: status/manifest/result records are required")
        documents[component_id] = {}
        for role, record in records.items():
            relative = record.get("path")
            expected_hash = record.get("sha256")
            if not isinstance(relative, str) or not isinstance(expected_hash, str):
                raise ValueError(f"{component_id}/{role}: path and sha256 are required")
            path = ROOT / relative
            if not path.is_file():
                raise ValueError(f"{component_id}/{role}: missing evidence {relative}")
            actual_hash = sha256(path)
            if actual_hash != expected_hash:
                raise ValueError(f"{component_id}/{role}: hash mismatch for {relative}")
            if role in {"status", "manifest"}:
                documents[component_id][role] = load_json(path)
    return manifest, documents


def evaluate_components(manifest: dict[str, Any], documents: dict[str, dict[str, Any]]) -> dict[str, Any]:
    evaluated: dict[str, Any] = {}
    for component_id, spec in COMPONENT_RULES.items():
        gates: dict[str, Any] = {}
        for gate in GATES:
            role, json_pointer, expected = spec["rules"][gate]
            actual = pointer(documents[component_id][role], json_pointer)
            state = "PASS" if actual is not MISSING and actual is not None and actual == expected else (
                "MISSING" if actual is MISSING or actual is None else "BLOCKED"
            )
            evidence_record = manifest["components"][component_id]["records"][role]
            gates[gate] = {
                "state": state,
                "required": expected,
                "observed": printable(actual),
                "jsonPointer": json_pointer,
                "evidence": {"path": evidence_record["path"], "sha256": evidence_record["sha256"]},
            }
        evaluated[component_id] = {
            "name": spec["name"],
            "eligible": all(item["state"] == "PASS" for item in gates.values()),
            "records": manifest["components"][component_id]["records"],
            "gates": gates,
        }
    return evaluated


def omitted_checklist(bundle_id: str) -> list[dict[str, Any]]:
    return [
        {
            "requirement": requirement,
            "implemented": False,
            "evidencePath": None,
            "reason": f"Bundle {bundle_id} failed prerequisite gates before prototype authorization; no partial implementation was permitted.",
        }
        for requirement in CHECKLIST
    ]


def evaluate_bundles(manifest: dict[str, Any], components: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for bundle_id, bundle in BUNDLES.items():
        direct = list(bundle["components"])
        alternative_groups = [list(group) for group in bundle["alternatives"]]
        blockers: list[dict[str, Any]] = []
        for component_id in direct:
            for gate, record in components[component_id]["gates"].items():
                if record["state"] != "PASS":
                    blockers.append({"component": component_id, "gate": gate, **record})
        alternatives_output: list[dict[str, Any]] = []
        for group in alternative_groups:
            passing = [component_id for component_id in group if components[component_id]["eligible"]]
            alternatives_output.append({"anyOf": group, "passing": passing, "state": "PASS" if passing else "BLOCKED"})
            if not passing:
                blockers.append({
                    "component": "anyOf(" + ",".join(group) + ")",
                    "gate": "all-eight-gates",
                    "state": "BLOCKED",
                    "required": "at least one component PASS for all eight gates",
                    "observed": "zero qualifying alternatives",
                    "jsonPointer": None,
                    "evidence": None,
                })
        eligible = not blockers
        evidence_component, evidence_role = bundle["lastEvidence"]
        last_evidence = manifest["components"][evidence_component]["records"][evidence_role]
        rows.append({
            "bundleId": bundle_id,
            "name": bundle["name"],
            "eligible": eligible,
            "finalist": False,
            "prototypeImplemented": False,
            "requiredComponents": direct,
            "alternativeGroups": alternatives_output,
            "lastCompletedStage": bundle["last"],
            "lastCompletedStageEvidence": last_evidence,
            "blockingGates": blockers,
            "omittedPrototypeRequirements": omitted_checklist(bundle_id),
            "revivalConditions": bundle["revive"],
        })
    return rows


def _assert_shape(result: dict[str, Any]) -> None:
    if result.get("schema") != "pqtc.sp80.eligibility-result.v1":
        raise ValueError("unexpected result schema")
    rows = result.get("bundles")
    if not isinstance(rows, list) or [row.get("bundleId") for row in rows] != list(BUNDLES):
        raise ValueError("result must contain bundles A-F exactly once and in order")
    if result.get("summary") != {"bundleCount": 6, "eligibleCount": 0, "finalistCount": 0, "prototypeCount": 0}:
        raise ValueError("result summary is not the required zero-finalist conclusion")
    if result.get("decision") != DECISION:
        raise ValueError("result decision changed")
    for row in rows:
        if row.get("eligible") or row.get("finalist") or row.get("prototypeImplemented"):
            raise ValueError(f"bundle {row.get('bundleId')} illegally claims passage or a prototype")
        checklist = row.get("omittedPrototypeRequirements")
        if not isinstance(checklist, list) or [item.get("requirement") for item in checklist] != list(CHECKLIST):
            raise ValueError(f"bundle {row.get('bundleId')} has an incomplete prototype checklist")
        if any(item.get("implemented") or item.get("evidencePath") is not None for item in checklist):
            raise ValueError(f"bundle {row.get('bundleId')} claims an unbuilt prototype item")
        if not row.get("blockingGates"):
            raise ValueError(f"bundle {row.get('bundleId')} lacks a blocking gate")


def build_result() -> dict[str, Any]:
    manifest, documents = load_and_verify_manifest()
    components = evaluate_components(manifest, documents)
    bundles = evaluate_bundles(manifest, components)
    result: dict[str, Any] = {
        "schema": "pqtc.sp80.eligibility-result.v1",
        "spike": "SP-80",
        "eligibilityPolicy": {
            "requiredGates": list(GATES),
            "rule": "Every direct required component must PASS every gate; each alternative group needs at least one component that PASSes every gate. Missing and null observations are non-passing.",
        },
        "components": components,
        "bundles": bundles,
        "summary": {
            "bundleCount": len(bundles),
            "eligibleCount": sum(row["eligible"] for row in bundles),
            "finalistCount": sum(row["finalist"] for row in bundles),
            "prototypeCount": sum(row["prototypeImplemented"] for row in bundles),
        },
        "decision": DECISION,
        "metricClaims": [],
        "prototypeClaims": [],
        "mutationDefense": {
            "mutation": "set the first blocked component gate state in a valid result to PASS",
            "expected": "REJECT",
            "status": "PASS",
        },
    }
    _assert_shape(result)
    return result


def validate_result(candidate: dict[str, Any]) -> None:
    _assert_shape(candidate)
    expected = build_result()
    if candidate != expected:
        raise ValueError("result differs from deterministic evidence-derived evaluation")


def mutation_self_test() -> None:
    result = build_result()
    mutated = copy.deepcopy(result)
    changed = False
    for component in mutated["components"].values():
        for gate in component["gates"].values():
            if gate["state"] != "PASS":
                gate["state"] = "PASS"
                changed = True
                break
        if changed:
            break
    if not changed:
        raise ValueError("self-test could not find a blocked component gate")
    try:
        validate_result(mutated)
    except ValueError:
        return
    raise ValueError("blocked-component PASS mutation was accepted")


def refresh_source_hashes() -> None:
    """Refresh only the hashes of the manifest's fixed, already-known paths."""
    manifest = load_json(MANIFEST_PATH)
    if manifest.get("schema") != "pqtc.sp80.eligibility-manifest.v1":
        raise ValueError("unexpected SP-80 manifest schema")
    if set(manifest.get("components", {})) != set(COMPONENT_RULES):
        raise ValueError("manifest component set does not match executable rules")
    for component_id, component in manifest["components"].items():
        records = component.get("records")
        if not isinstance(records, dict) or set(records) != {"status", "manifest", "result"}:
            raise ValueError(f"{component_id}: refusing to refresh anything but the fixed status/manifest/result set")
        for role, record in records.items():
            relative = record.get("path")
            if not isinstance(relative, str):
                raise ValueError(f"{component_id}/{role}: fixed path is required")
            path = ROOT / relative
            if not path.is_file():
                raise ValueError(f"{component_id}/{role}: missing evidence {relative}")
            record["sha256"] = sha256(path)
    plan = manifest.get("plan")
    if not isinstance(plan, dict) or plan.get("path") != "PQTC_NEXT_GENERATION_RESEARCH_PLAN.md":
        raise ValueError("refusing to refresh an unexpected plan path")
    plan["sha256"] = sha256(ROOT / plan["path"])
    checker = manifest.get("eligibilityChecker")
    expected_checker_path = "research/integrated-finalists/check.py"
    if not isinstance(checker, dict) or checker.get("path") != expected_checker_path:
        raise ValueError("refusing to refresh an unexpected checker path")
    checker["sha256"] = sha256(ROOT / expected_checker_path)
    package_inputs = manifest.get("packageInputs")
    if not isinstance(package_inputs, list):
        raise ValueError("packageInputs must be a fixed list")
    for record in package_inputs:
        relative = record.get("path") if isinstance(record, dict) else None
        if not isinstance(relative, str):
            raise ValueError("package input path is required")
        path = ROOT / relative
        if not path.is_file():
            raise ValueError(f"missing package input {relative}")
        record["sha256"] = sha256(path)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_outputs() -> None:
    result = build_result()
    mutation_self_test()
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_hash = sha256(MANIFEST_PATH)
    schema_hash = sha256(PACKAGE / "result.schema.json")
    result_hash = sha256(RESULT_PATH)
    status = {
        "schema": "pqtc.sp80.status.v1",
        "spike": "SP-80",
        "status": DECISION,
        "bundleCount": 6,
        "eligibleCount": 0,
        "finalistCount": 0,
        "prototypeCount": 0,
        "prototypeImplementationAuthorized": False,
        "checker": "research/integrated-finalists/check.py",
        "checkCommand": "python3 research/integrated-finalists/check.py --check",
        "refreshCommand": "python3 research/integrated-finalists/check.py --refresh-source-hashes",
        "mutationCommand": "python3 research/integrated-finalists/check.py --self-test",
        "mutationResult": "PASS_REJECTED_BLOCKED_COMPONENT_PASS",
        "manifest": {"path": "research/integrated-finalists/manifest.json", "sha256": manifest_hash},
        "resultSchema": {"path": "research/integrated-finalists/result.schema.json", "sha256": schema_hash},
        "result": {"path": "research/integrated-finalists/outputs/results.json", "sha256": result_hash},
        "metricsMeasuredBySp80": [],
        "prototypeClaims": [],
    }
    STATUS_PATH.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def check_outputs() -> None:
    candidate = load_json(RESULT_PATH)
    validate_result(candidate)
    mutation_self_test()
    status = load_json(STATUS_PATH)
    if status.get("status") != DECISION:
        raise ValueError("status conclusion changed")
    if status.get("result", {}).get("sha256") != sha256(RESULT_PATH):
        raise ValueError("status result hash mismatch")
    if status.get("manifest", {}).get("sha256") != sha256(MANIFEST_PATH):
        raise ValueError("status manifest hash mismatch")
    if status.get("resultSchema", {}).get("sha256") != sha256(PACKAGE / "result.schema.json"):
        raise ValueError("status schema hash mismatch")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="write deterministic result and status using pinned evidence")
    mode.add_argument("--refresh-source-hashes", action="store_true", help="refresh fixed evidence pins, then write results")
    mode.add_argument("--check", action="store_true", help="check committed result and status (default)")
    mode.add_argument("--self-test", action="store_true", help="prove a blocked-gate PASS mutation is rejected")
    args = parser.parse_args()
    try:
        if args.refresh_source_hashes:
            refresh_source_hashes()
            write_outputs()
        elif args.write:
            write_outputs()
        elif args.self_test:
            mutation_self_test()
        else:
            check_outputs()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"SP-80 check failed: {exc}", file=sys.stderr)
        return 1
    print("PASS: SP-80 evidence pins, six zero-eligible bundles, and mutation rejection verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
