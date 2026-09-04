#!/usr/bin/env python3
"""Validate the stopped SP-20 package and its frozen-source evidence."""

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
EXPECTED_A2_LANES = ["1", "2", "4", "8", "16", "full"]


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


def check_frozen_sources(errors: list[str]) -> None:
    air = ROOT / "crates/pqtc-poseidon-air/src/air.rs"
    for fragment in (
        "pub const NUM_CONSTRAINTS: usize = 1_186;",
        "pub const ACTIVE_PERMUTATIONS: usize = 240;",
        "pub const TRACE_HEIGHT: usize = 256;",
        "pub const MAX_CONSTRAINT_DEGREE: usize = 7;",
        "assert!(NUM_POSEIDON_COLS == 157)",
        "assert!(NUM_WITHDRAWAL_COLS == 190)",
        "for level in 0..20",
        "inputs.resize(TRACE_HEIGHT, [BabyBear::ZERO; WIDTH]);",
    ):
        contains_exact(air, fragment, errors)

    security = ROOT / "crates/pqtc-security/src/lib.rs"
    contains_exact(security, "pub const BATCHED_FUNCTIONS: usize = NUM_WITHDRAWAL_COLS + 16 + 4;", errors)

    stark = ROOT / "crates/pqtc-stark/src/lib.rs"
    contains_exact(stark, "Self::SepoliaV03 => (4, 0, 32, 16, 16)", errors)
    contains_exact(stark, "Self::Ci | Self::SepoliaV03 => 4", errors)

    codec = ROOT / "crates/pqtc-stark/src/codec.rs"
    contains_exact(codec, "const QUOTIENT_CHUNKS: usize = 16;", errors)
    contains_exact(codec, "const MMCS_SALT_ELEMENTS: usize = 8;", errors)
    contains_exact(codec, "TRACE_HEIGHT.ilog2() as usize + 1", errors)

    ood = ROOT / "contracts/src/verifier/StarkOodVerifier.sol"
    contains_exact(ood, "uint256 private constant QUOTIENT_LOG_SIZE = 12;", errors)
    contains_exact(ood, "uint256 private constant QUOTIENT_CHUNK_LOG_SIZE = 8;", errors)
    contains_exact(ood, "uint256 private constant QUOTIENT_CHUNKS = 16;", errors)


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


def check_results(results: dict[str, Any], errors: list[str]) -> None:
    require(results.get("status") == "STOPPED_BY_DEPENDENCY", "results status mismatch", errors)
    require(results["resultSemantics"].get("selectedGeometry") is None, "selected geometry must be null", errors)
    require(results["resultSemantics"].get("pcsIntegratedGeometry") is None, "PCS geometry must be null", errors)

    corpus = load_json(ROOT / "research/common-corpus/corpus-manifest.json")
    corpus_record = results["relationIdentity"]["corpus"]
    require(corpus_record.get("sha256") == corpus["artifactDigests"]["semantic-cases.json"]["sha256"], "corpus identity mismatch", errors)
    require(corpus_record.get("semanticCases") == corpus["counts"]["semanticCases"], "corpus count mismatch", errors)
    relation = results["relationIdentity"]
    require(relation.get("publicValueOrder") == ["scope", "root", "nullifierHash", "payoutDigest"], "public value order mismatch", errors)
    require(relation.get("publicValues") == 64, "public value count mismatch", errors)
    require(relation.get("treeDepth") == 20, "tree depth mismatch", errors)
    require(relation.get("applicationInvocations") == {"nullifier": 1, "noteCommitment": 1, "merkleNode": 20, "total": 22}, "application invocation identity mismatch", errors)
    require(relation.get("poseidonPermutations") == {"nullifier": 9, "noteCommitment": 11, "merkleNodes": 220, "total": 240}, "permutation schedule mismatch", errors)
    require(relation.get("payoutBindingRows") == 4, "payout binding row count mismatch", errors)
    require(relation.get("columnMap") == {
        "poseidonSubAir": "0..156",
        "isNote": 157,
        "isNullifier": 158,
        "isMerkle": 159,
        "isPayout": 160,
        "isPadding": 161,
        "stepBits": "162..165",
        "levelBits": "166..170",
        "isLastLevel": 171,
        "pathBit": 172,
        "leafIndex": 173,
        "work": "174..189",
    }, "A0 column map mismatch", errors)
    require(corpus_record.get("protocolSemanticVersion") == "pqtc-withdrawal-semantics-v1", "corpus semantic version mismatch", errors)
    require(corpus_record.get("corpusVersion") == 1, "corpus version mismatch", errors)
    require(corpus_record.get("candidateNeutral") is True, "corpus must remain candidate-neutral", errors)

    a0 = results["families"]["A0"]
    expected_geometry = {
        "logicalRows": 256,
        "activePermutationRows": 240,
        "payoutBindingRows": 4,
        "paddingRows": 12,
        "paddedRows": 256,
        "baseDegreeBits": 8,
        "hidingDegreeBits": 9,
        "traceWidthByTable": {"main": 190},
        "poseidonSubAirWidth": 157,
        "preprocessedWidth": 0,
        "constraintCount": 1186,
        "maximumDegree": 7,
        "quotientDegreeBits": 12,
        "quotientChunkDegreeBits": 8,
        "quotientChunks": 16,
        "batchedFunctions": {"trace": 190, "quotient": 16, "randomCodewords": 4, "total": 210},
        "transitionRotations": [0, 1],
        "activeVsPaddingRows": {"active": 244, "padding": 12},
    }
    require(a0.get("evidenceClass") == "SOURCE_VERIFIED_BASELINE", "A0 evidence class mismatch", errors)
    require(a0.get("geometry") == expected_geometry, "A0 frozen geometry mismatch", errors)
    require(a0.get("measured") is False, "A0 must not be labeled a new measurement", errors)
    expected_hiding = {
        "profile": "sepolia-v0.3",
        "baseField": "BabyBear",
        "challengeExtensionDegree": 4,
        "friLogBlowup": 4,
        "friQueries": 32,
        "friLogFinalPolynomialLength": 0,
        "friMaximumLogArity": 1,
        "commitProofOfWorkBits": 16,
        "queryProofOfWorkBits": 16,
        "randomCodewords": 4,
        "mmcsSaltElements": 8,
        "hiding": True,
    }
    require(a0.get("hidingAndFriInputs") == expected_hiding, "A0 hiding/FRI inputs mismatch", errors)

    families = results["families"]
    for family_id in ("A1", "A2", "A3", "A4"):
        family = families[family_id]
        require(family.get("evidenceClass") == "NOT_ATTEMPTED_BY_GATE", f"{family_id}: evidence class mismatch", errors)
        require(family.get("disposition") == "NOT_ATTEMPTED_BY_GATE", f"{family_id}: disposition mismatch", errors)
        require(family.get("measured") is False, f"{family_id}: measured must be false", errors)
        numbers = numeric_values(family)
        require(not numbers, f"{family_id}: symbolic worksheet contains numeric values at {numbers}", errors)

    lanes = [row.get("laneParallelismLabel") for row in families["A2"]["rows"]]
    require(lanes == EXPECTED_A2_LANES, "A2 lane sweep must be 1/2/4/8/16/full", errors)
    for row in families["A2"]["rows"]:
        require(row.get("requiredMetrics") == "ALL_UNKNOWN_NOT_IMPLEMENTED", "A2 row claims geometry", errors)
        require(row.get("symbolicLowerBound", {}).get("evidenceClass") == "SYMBOLIC_LOWER_BOUND", "A2 symbolic bound missing", errors)

    a3_tables = [row.get("table") for row in families["A3"]["tables"]]
    require(a3_tables == ["controller/path", "application-compression", "fixed/preprocessed-rounds", "linking permutation-or-lookup"], "A3 table worksheet incomplete", errors)
    a4_forms = [row.get("form") for row in families["A4"]["rows"]]
    require(a4_forms == ["AIR", "R1CS", "CCS", "Boolean"], "A4 backend-neutral worksheet incomplete", errors)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-eligible", action="store_true", help="fail closed unless SP-10 exposes an eligible AIR candidate")
    args = parser.parse_args()
    errors: list[str] = []

    check_hashes(errors)
    check_frozen_sources(errors)
    manifest = load_json(PACKAGE / "manifest.json")
    status = load_json(PACKAGE / "status.json")
    results = load_json(PACKAGE / "results.json")
    negatives = load_json(PACKAGE / "negative-results.json")
    assumptions = load_json(PACKAGE / "assumptions.json")

    for name, artifact in (("manifest", manifest), ("status", status), ("results", results), ("negative-results", negatives), ("assumptions", assumptions)):
        require(artifact.get("status") == "STOPPED_BY_DEPENDENCY", f"{name}: status must be STOPPED_BY_DEPENDENCY", errors)
    require(manifest.get("relationImplementation") is False, "manifest must not claim a relation implementation", errors)
    require(status.get("selectedGeometry") is None, "status must not select geometry", errors)
    require(status.get("benchmarkResult") is None, "status must not claim benchmark result", errors)
    require(status.get("pcsIntegration") == "PROHIBITED", "PCS integration must be prohibited", errors)

    check_results(results, errors)
    eligible = check_dependency(results, errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    if args.require_eligible and not eligible:
        print(json.dumps({"studyId": "SP-20", "dependencyGate": "FAIL", "reason": "NO_ELIGIBLE_SP10_CANDIDATE"}, sort_keys=True))
        return 3
    print(json.dumps({"studyId": "SP-20", "checker": "PASS", "status": "STOPPED_BY_DEPENDENCY", "stoppedAirDispositions": 8, "symbolicFamilies": ["A1", "A2", "A3", "A4"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
