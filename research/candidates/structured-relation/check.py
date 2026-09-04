#!/usr/bin/env python3
"""Validate the stopped SP-21 package and fail closed on its SP-10 dependency."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = Path(__file__).resolve().parent
H_IDS = [f"H{i}" for i in range(8)]
CONVERSION_FORMS = ["AIR", "R1CS", "CCS", "Boolean"]


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def contains_exact(path: Path, fragment: str, errors: list[str]) -> None:
    require(fragment in path.read_text(encoding="utf-8"), f"{path}: missing frozen fragment {fragment!r}", errors)


def numeric_values(value: Any, location: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, bool):
        return found
    if isinstance(value, (int, float)):
        found.append(location or "<root>")
    elif isinstance(value, dict):
        for key, child in value.items():
            found.extend(numeric_values(child, f"{location}.{key}" if location else key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(numeric_values(child, f"{location}[{index}]"))
    return found


def check_hashes(errors: list[str]) -> None:
    pins = load_json(PACKAGE / "source-hashes.json")
    require(pins.get("algorithm") == "sha256", "source-hashes algorithm must be sha256", errors)
    files = pins.get("files")
    require(isinstance(files, dict) and bool(files), "source-hashes files must be nonempty", errors)
    if not isinstance(files, dict):
        return
    for relative, expected in sorted(files.items()):
        path = ROOT / relative
        require(path.is_file(), f"missing pinned source: {relative}", errors)
        if path.is_file():
            require(digest(path) == expected, f"source hash mismatch: {relative}", errors)


def check_frozen_relation(errors: list[str]) -> None:
    relation = ROOT / "crates/pqtc-poseidon-air/src/lib.rs"
    for fragment in (
        "pub nullifier_secret: CanonicalSecret,",
        "pub trapdoor: CanonicalSecret,",
        "pub leaf_index: u32,",
        "pub path_bits: [u8; TREE_DEPTH as usize],",
        "pub siblings: [Digest512; TREE_DEPTH as usize],",
        "if nullifier_hash(statement.scope, witness.nullifier_secret) != statement.nullifier_hash",
        "if current != statement.root",
        "statement.scope,",
        "statement.root,",
        "statement.nullifier_hash,",
        "statement.payout_digest,",
    ):
        contains_exact(relation, fragment, errors)

    air = ROOT / "crates/pqtc-poseidon-air/src/air.rs"
    for fragment in (
        "pub const ACTIVE_PERMUTATIONS: usize = 240;",
        "append_hash(",
        "Kind::Nullifier,",
        "Kind::Note,",
        "for level in 0..20",
        "Kind::Merkle,",
        "assert_eq!(inputs.len(), ACTIVE_PERMUTATIONS);",
    ):
        contains_exact(air, fragment, errors)

    hash_source = ROOT / "crates/pqtc-hash/src/lib.rs"
    for fragment in ("domains::NULLIFIER", "domains::NOTE", "domains::APP_MERKLE_NODE"):
        contains_exact(hash_source, fragment, errors)


def check_dependency(results: dict[str, Any], errors: list[str]) -> bool:
    observed: list[dict[str, Any]] = []
    eligible: list[str] = []
    for candidate_id in H_IDS:
        status = load_json(ROOT / f"research/candidates/{candidate_id}/status.json")
        gate = status.get("gateComparison")
        require(isinstance(gate, dict), f"{candidate_id}: gateComparison missing", errors)
        if not isinstance(gate, dict):
            continue
        disposition = gate.get("airDisposition")
        all_pass = gate.get("allPass")
        observed.append({
            "candidateId": candidate_id,
            "status": status.get("status"),
            "allPass": all_pass,
            "airDisposition": disposition,
        })
        require(disposition == "STOPPED", f"{candidate_id}: airDisposition must be STOPPED", errors)
        require(all_pass is False, f"{candidate_id}: allPass must be false", errors)
        if all_pass is True and disposition == "ELIGIBLE_FOR_AIR":
            eligible.append(candidate_id)
    require(results["dependencyObservation"]["candidates"] == observed, "results dependency observation is stale", errors)
    require(results["dependencyObservation"]["eligibleCandidate"] is None, "stopped results must not name a finalist", errors)

    sp02 = load_json(ROOT / "research/advisories/status.json")
    require(sp02.get("status") == "ARCHIVED_FAILED", "SP-02 status must be ARCHIVED_FAILED", errors)
    require(sp02.get("gateResult") == "FAIL", "SP-02 gateResult must be FAIL", errors)
    require(sp02.get("integrationAllowed") is False, "SP-02 integrationAllowed must be false", errors)
    return bool(eligible)


def check_backend_evidence(results: dict[str, Any], errors: list[str]) -> None:
    landscape = load_json(ROOT / "research/backends/landscape/matrix.json")
    records = {row["id"]: row for row in landscape.get("candidates", []) if isinstance(row, dict) and "id" in row}
    spartan = records.get("SP-60-NATIVE")
    flock = records.get("SP-62-FLOCK")
    require(isinstance(spartan, dict), "landscape SP-60-NATIVE record missing", errors)
    require(isinstance(flock, dict), "landscape SP-62-FLOCK record missing", errors)
    if isinstance(spartan, dict):
        finding = spartan["field_and_relation_constraints"]["finding"]
        require("no special repeated-block PQTC API" in finding, "Spartan repeated-block finding changed", errors)
    if isinstance(flock, dict):
        require(flock.get("status") == "STOP", "Flock landscape status must be STOP", errors)
        breaking = flock.get("breaking_change", {}).get("finding", "")
        require("0f0d63268e1373c585251e95152b3a6943e2d818" in breaking, "Flock removal pin changed", errors)
        require("c2d0c2485a54f7b7694e19f4f59730ffde3405cf" in breaking, "Flock historical parent changed", errors)

    comparison = {row["backend"]: row for row in results["backendSourceComparison"]}
    require(comparison["ethereum/spartan-whir"].get("structuredPqtcApi") is False, "Spartan must not claim a structured PQTC API", errors)
    require(comparison["Flock"].get("currentApplicationKeccakApi") is False, "Flock current application Keccak API finding mismatch", errors)
    require(all(row.get("conversion") == "NOT_ATTEMPTED_BY_GATE" for row in comparison.values()), "backend comparison must not claim a conversion", errors)


def check_results(results: dict[str, Any], errors: list[str]) -> None:
    require(results.get("status") == "STOPPED_BY_DEPENDENCY", "results status mismatch", errors)
    semantics = results["resultSemantics"]
    require(semantics.get("relationImplementation") is False, "results must not claim relation code", errors)
    require(semantics.get("schemaIsExecutable") is False, "schema must not be executable", errors)
    require(semantics.get("selectedBackend") is None, "selected backend must be null", errors)
    require(semantics.get("conversionResult") is None, "conversion result must be null", errors)

    control = results["frozenControl"]
    require(control.get("evidenceClass") == "SOURCE_VERIFIED_BASELINE", "frozen control evidence class mismatch", errors)
    require(control.get("publicValueOrder") == ["scope", "root", "nullifierHash", "payoutDigest"], "frozen public order mismatch", errors)
    require(control.get("publicValueCount") == 64, "frozen public count mismatch", errors)
    require(control.get("privateWitness") == ["nullifierSecret", "trapdoor", "leafIndex", "pathBits[20]", "siblings[20]"], "frozen private partition mismatch", errors)
    corpus_manifest = load_json(ROOT / "research/common-corpus/corpus-manifest.json")
    corpus = control.get("corpus", {})
    require(corpus.get("sha256") == corpus_manifest["artifactDigests"]["semantic-cases.json"]["sha256"], "corpus digest mismatch", errors)
    require(corpus.get("semanticCases") == corpus_manifest["counts"]["semanticCases"], "corpus count mismatch", errors)
    require(corpus.get("corpusVersion") == corpus_manifest["corpusVersion"], "corpus version mismatch", errors)
    require(corpus.get("protocolSemanticVersion") == "pqtc-withdrawal-semantics-v1", "corpus semantic version mismatch", errors)
    require(corpus.get("conversionExecution") == "NOT_ATTEMPTED_BY_GATE", "corpus conversion must remain not attempted", errors)
    require(control.get("applicationInvocationCounts") == {"nullifier": 1, "noteCommitment": 1, "merkleNode": 20, "total": 22}, "frozen 22-call identity mismatch", errors)
    require(control.get("poseidonPermutationExpansion") == {"nullifier": 9, "noteCommitment": 11, "merkleNodes": 220, "total": 240}, "frozen permutation expansion mismatch", errors)

    schema = results["intendedSchema"]
    require(schema.get("schemaClass") == "HYPOTHESIS_ONLY", "intended schema must be hypothesis only", errors)
    require(schema.get("disposition") == "NOT_ATTEMPTED_BY_GATE", "schema disposition mismatch", errors)
    require(schema.get("relationImplementation") is False, "schema must not claim implementation", errors)
    require(schema.get("qualifiedPrimitive") is None, "schema must not invent a finalist", errors)
    require(schema["block"].get("definition") == "UNKNOWN_UNTIL_SP10_FINALIST", "F definition must remain unknown", errors)

    instances = schema["batch"]["instances"]
    require(len(instances) == 22, "schema must contain exactly 22 ordered instance descriptors", errors)
    require([row.get("instanceId") for row in instances] == [f"F{i:02d}" for i in range(22)], "instance identifiers must be F00-F21", errors)
    require([row.get("role") for row in instances[:2]] == ["nullifier", "noteCommitment"], "first two instance roles mismatch", errors)
    require(all(row.get("role") == "merkleNode" for row in instances[2:]), "F02-F21 must be Merkle instances", errors)
    require([row.get("ordinal") for row in instances[2:]] == [str(i) for i in range(20)], "Merkle ordinals must cover levels 0-19", errors)
    require(schema["glue"].get("pathOrderSelections") == 20, "glue must retain 20 path selections", errors)
    require(schema["partition"].get("backendPublicInputSource") == "VERIFIER_SELECTED_APPLICATION_STATEMENT", "public input authority mismatch", errors)
    require(all(row.get("evidenceClass") == "SYMBOLIC_LOWER_BOUND" for row in schema["symbolicLowerBounds"]), "symbolic lower bounds must be labeled", errors)

    conversions = results["conversions"]
    require([row.get("form") for row in conversions] == CONVERSION_FORMS, "conversion table forms mismatch", errors)
    for row in conversions:
        require(row.get("disposition") == "NOT_ATTEMPTED_BY_GATE", f"{row.get('form')}: conversion disposition mismatch", errors)
        require(row.get("measured") is False, f"{row.get('form')}: measured must be false", errors)
        numbers = numeric_values(row)
        require(not numbers, f"{row.get('form')}: conversion row contains numeric values at {numbers}", errors)
        for metric in ("variables", "constraints", "nonzeros", "glueConstraints", "memoryLayout"):
            require(row.get(metric) == "UNKNOWN_NOT_COMPILED", f"{row.get('form')}: {metric} must be unknown", errors)

    checklist = results["backendApiPreservationChecklist"]
    require([row.get("id") for row in checklist] == [f"API-{i:02d}" for i in range(1, 9)], "API preservation checklist incomplete", errors)
    require(all(row.get("required") is True and row.get("evaluation") == "NOT_ATTEMPTED_BY_GATE" for row in checklist), "API checklist must remain required and not attempted", errors)

    stops = {row["id"]: row for row in results["stopConditions"]}
    for stop_id in ("STOP-DEPENDENCY", "STOP-FLAT-ONLY", "STOP-METADATA", "STOP-EXPANSION-UNKNOWN", "STOP-EXPANSION-ADVANTAGE", "STOP-CORPUS"):
        require(stop_id in stops, f"missing stop condition {stop_id}", errors)
    require(stops.get("STOP-EXPANSION-ADVANTAGE", {}).get("threshold") == "NO_NUMERIC_THRESHOLD_SPECIFIED_BY_SP21", "must not invent an expansion threshold", errors)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-eligible", action="store_true", help="fail closed unless SP-10 exposes an eligible relation candidate")
    args = parser.parse_args()
    errors: list[str] = []

    check_hashes(errors)
    check_frozen_relation(errors)
    manifest = load_json(PACKAGE / "manifest.json")
    status = load_json(PACKAGE / "status.json")
    results = load_json(PACKAGE / "results.json")
    negatives = load_json(PACKAGE / "negative-results.json")
    assumptions = load_json(PACKAGE / "assumptions.json")

    for name, artifact in (("manifest", manifest), ("status", status), ("results", results), ("negative-results", negatives), ("assumptions", assumptions)):
        require(artifact.get("status") == "STOPPED_BY_DEPENDENCY", f"{name}: status must be STOPPED_BY_DEPENDENCY", errors)
    require(manifest.get("relationImplementation") is False, "manifest must not claim relation implementation", errors)
    require(manifest.get("conversionImplementation") is False, "manifest must not claim conversion implementation", errors)
    require(status.get("selectedBackend") is None, "status must not select a backend", errors)
    require(status.get("benchmarkResult") is None, "status must not claim benchmark result", errors)

    check_results(results, errors)
    check_backend_evidence(results, errors)
    eligible = check_dependency(results, errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    if args.require_eligible and not eligible:
        print(json.dumps({"studyId": "SP-21", "dependencyGate": "FAIL", "reason": "NO_ELIGIBLE_SP10_CANDIDATE"}, sort_keys=True))
        return 3
    print(json.dumps({"studyId": "SP-21", "checker": "PASS", "status": "STOPPED_BY_DEPENDENCY", "stoppedAirDispositions": 8, "conversionDispositions": {form: "NOT_ATTEMPTED_BY_GATE" for form in CONVERSION_FORMS}}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
