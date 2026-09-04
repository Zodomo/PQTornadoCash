#!/usr/bin/env python3
"""Deterministic Foundry artifact extractor and deployment-binding checker.

The checker consumes Foundry's canonical per-contract JSON artifacts. It never
invokes forge or solc, and it distinguishes creation code, full initcode, the
unpatched runtime template, and constructor-resolved runtime code.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

MASK64 = (1 << 64) - 1
RATE = 136
ROTATIONS = (
    0, 1, 62, 28, 27, 36, 44, 6, 55, 20, 3, 10, 43, 25, 39,
    41, 45, 15, 21, 8, 18, 2, 61, 56, 14,
)
ROUND_CONSTANTS = (
    0x0000000000000001, 0x0000000000008082, 0x800000000000808A,
    0x8000000080008000, 0x000000000000808B, 0x0000000080000001,
    0x8000000080008081, 0x8000000000008009, 0x000000000000008A,
    0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
    0x000000008000808B, 0x800000000000008B, 0x8000000000008089,
    0x8000000000008003, 0x8000000000008002, 0x8000000000000080,
    0x000000000000800A, 0x800000008000000A, 0x8000000080008081,
    0x8000000000008080, 0x0000000080000001, 0x8000000080008008,
)
EMPTY_KECCAK = "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"


class BindingError(RuntimeError):
    """A stable, machine-readable binding failure."""

    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def rol(value: int, shift: int) -> int:
    if shift == 0:
        return value
    return ((value << shift) | (value >> (64 - shift))) & MASK64


def permutation(state: list[int]) -> None:
    for rc in ROUND_CONSTANTS:
        columns = [
            state[x] ^ state[x + 5] ^ state[x + 10] ^ state[x + 15] ^ state[x + 20]
            for x in range(5)
        ]
        for x in range(5):
            delta = columns[(x - 1) % 5] ^ rol(columns[(x + 1) % 5], 1)
            for y in range(5):
                state[x + 5 * y] ^= delta
        moved = [0] * 25
        for x in range(5):
            for y in range(5):
                moved[y + 5 * ((2 * x + 3 * y) % 5)] = rol(
                    state[x + 5 * y], ROTATIONS[x + 5 * y]
                )
        for x in range(5):
            for y in range(5):
                state[x + 5 * y] = (
                    moved[x + 5 * y]
                    ^ ((~moved[(x + 1) % 5 + 5 * y]) & moved[(x + 2) % 5 + 5 * y])
                ) & MASK64
        state[0] ^= rc


def keccak256(data: bytes) -> str:
    state = [0] * 25
    padded = bytearray(data)
    padded.append(0x01)  # Ethereum Keccak domain; SHA3 uses 0x06.
    padded.extend(b"\x00" * ((RATE - len(padded) % RATE) % RATE))
    padded[-1] ^= 0x80
    for offset in range(0, len(padded), RATE):
        block = padded[offset:offset + RATE]
        for lane in range(RATE // 8):
            start = lane * 8
            state[lane] ^= int.from_bytes(block[start:start + 8], "little")
        permutation(state)
    return b"".join(lane.to_bytes(8, "little") for lane in state)[:32].hex()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BindingError("INVALID_JSON", f"{path}: {exc}") from exc
    if not isinstance(value, dict):
        raise BindingError("INVALID_JSON", f"{path}: root must be an object")
    return value


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def decode_hex(value: Any, field: str, *, allow_empty: bool = False) -> bytes:
    if not isinstance(value, str):
        raise BindingError("INVALID_HEX", f"{field} must be a string")
    raw = value[2:] if value.startswith("0x") else value
    if not raw and allow_empty:
        return b""
    if not raw or len(raw) % 2:
        raise BindingError("INVALID_HEX", f"{field} is empty or odd-length")
    try:
        return bytes.fromhex(raw)
    except ValueError as exc:
        raise BindingError("UNRESOLVED_BYTECODE", f"{field} contains non-hex placeholders") from exc


def exact(actual: Any, expected: Any, code: str, detail: str) -> None:
    if actual != expected:
        raise BindingError(code, f"{detail}: expected {expected!r}, got {actual!r}")


def refs_nonempty(refs: Any) -> bool:
    if not isinstance(refs, dict):
        return bool(refs)
    return any(bool(per_file) for per_file in refs.values())


def resolve_runtime(
    runtime: bytes,
    references: dict[str, Any],
    bindings: dict[str, Any],
    contract_name: str,
) -> bytes:
    exact(set(bindings), set(references), "UNRESOLVED_IMMUTABLES", f"{contract_name} immutable IDs")
    resolved = bytearray(runtime)
    occupied: set[int] = set()
    for immutable_id in sorted(references, key=lambda value: int(value)):
        word = decode_hex(bindings[immutable_id], f"{contract_name}.immutableBindings[{immutable_id}]")
        locations = references[immutable_id]
        if not isinstance(locations, list) or not locations:
            raise BindingError("INVALID_IMMUTABLE_REFERENCE", f"{contract_name}:{immutable_id} has no locations")
        for location in locations:
            start = location.get("start")
            length = location.get("length")
            if not isinstance(start, int) or not isinstance(length, int) or length <= 0:
                raise BindingError("INVALID_IMMUTABLE_REFERENCE", f"{contract_name}:{immutable_id} malformed location")
            if len(word) != length or start < 0 or start + length > len(resolved):
                raise BindingError("INVALID_IMMUTABLE_REFERENCE", f"{contract_name}:{immutable_id} out of range")
            indices = set(range(start, start + length))
            if occupied & indices:
                raise BindingError("INVALID_IMMUTABLE_REFERENCE", f"{contract_name}:{immutable_id} overlaps another reference")
            occupied |= indices
            if any(resolved[start:start + length]):
                raise BindingError("RESOLVED_IMMUTABLE_TEMPLATE", f"{contract_name}:{immutable_id} template is not zero-filled")
            resolved[start:start + length] = word
    return bytes(resolved)


def artifact_settings(artifact: dict[str, Any]) -> dict[str, Any]:
    metadata = artifact.get("metadata")
    if not isinstance(metadata, dict):
        raise BindingError("MISSING_METADATA", "Foundry artifact lacks parsed metadata")
    compiler = metadata.get("compiler", {})
    settings = metadata.get("settings", {})
    return {
        "compilerVersion": compiler.get("version"),
        "optimizer": settings.get("optimizer"),
        "viaIR": settings.get("viaIR"),
        "evmVersion": settings.get("evmVersion"),
        "bytecodeHash": settings.get("metadata", {}).get("bytecodeHash"),
        "remappings": settings.get("remappings"),
        "libraries": settings.get("libraries"),
        "compilationTarget": settings.get("compilationTarget"),
    }


def extract_contract(repo: Path, record: dict[str, Any], artifact_override: dict[str, Any] | None = None) -> dict[str, Any]:
    name = record["name"]
    artifact_path = repo / record["artifact"]
    source_path = repo / record["source"]
    artifact = artifact_override if artifact_override is not None else load_json(artifact_path)
    bytecode = artifact.get("bytecode", {})
    deployed = artifact.get("deployedBytecode", {})
    if refs_nonempty(bytecode.get("linkReferences", {})) or refs_nonempty(deployed.get("linkReferences", {})):
        raise BindingError("UNRESOLVED_LINKS", f"{name} contains unresolved library references")
    creation = decode_hex(bytecode.get("object"), f"{name}.bytecode.object")
    runtime_template = decode_hex(deployed.get("object"), f"{name}.deployedBytecode.object")
    constructor_args = decode_hex(record.get("constructorArgsHex", ""), f"{name}.constructorArgsHex", allow_empty=True)
    immutable_refs = deployed.get("immutableReferences", {})
    if not isinstance(immutable_refs, dict):
        raise BindingError("INVALID_IMMUTABLE_REFERENCE", f"{name} immutableReferences must be an object")
    bindings = record.get("immutableBindings", {})
    if not isinstance(bindings, dict):
        raise BindingError("UNRESOLVED_IMMUTABLES", f"{name} immutableBindings must be an object")
    runtime = resolve_runtime(runtime_template, immutable_refs, bindings, name)
    return {
        "name": name,
        "artifact": record["artifact"],
        "artifactSha256": sha256_file(artifact_path) if artifact_override is None else None,
        "source": record["source"],
        "sourceSha256": sha256_file(source_path),
        "settings": artifact_settings(artifact),
        "creationCodeBytes": len(creation),
        "constructorArgsBytes": len(constructor_args),
        "fullInitcodeBytes": len(creation) + len(constructor_args),
        "runtimeBytes": len(runtime),
        "creationCodeKeccak256": "0x" + keccak256(creation),
        "fullInitcodeKeccak256": "0x" + keccak256(creation + constructor_args),
        "runtimeTemplateKeccak256": "0x" + keccak256(runtime_template),
        "runtimeKeccak256": "0x" + keccak256(runtime),
        "immutableReferenceIds": sorted(immutable_refs, key=lambda value: int(value)),
        "unresolvedLinkReferences": False,
        "unresolvedImmutableReferences": False,
    }


def validate_expected(record: dict[str, Any], extracted: dict[str, Any]) -> None:
    expected = record.get("expected", {})
    required = (
        "artifactSha256", "sourceSha256", "creationCodeKeccak256",
        "fullInitcodeKeccak256", "runtimeTemplateKeccak256", "runtimeKeccak256",
    )
    for key in required:
        value = expected.get(key)
        if not isinstance(value, str) or not value:
            raise BindingError("EMPTY_EXPECTED_HASH", f"{record['name']}.expected.{key}")
        exact(extracted[key], value, "HASH_MISMATCH", f"{record['name']}.{key}")
    for key in ("creationCodeBytes", "constructorArgsBytes", "fullInitcodeBytes", "runtimeBytes"):
        exact(extracted[key], expected.get(key), "SIZE_MISMATCH", f"{record['name']}.{key}")


def abi_address_word(value: Any, field: str) -> str:
    raw = decode_hex(value, field)
    if len(raw) != 20:
        raise BindingError("BINDING_MISMATCH", f"{field} must be a 20-byte address")
    return (b"\x00" * 12 + raw).hex()


def validate_constructor_bindings(manifest: dict[str, Any], records: list[dict[str, Any]]) -> None:
    parameter = decode_hex(manifest["proofSystemId"], "proofSystemId")
    projection = manifest.get("projection", {})
    addresses = projection.get("addresses", {})
    air = abi_address_word(addresses.get("airVerifier"), "projection.addresses.airVerifier")
    query = abi_address_word(addresses.get("queryVerifier"), "projection.addresses.queryVerifier")
    registry = abi_address_word(addresses.get("registry"), "projection.addresses.registry")
    denomination = int(projection.get("denominationWei", "0")).to_bytes(32, "big").hex()
    expected_by_name = {
        "PQTCAirStageVerifier": ("", {}),
        "PQTCQueryVerifier": ("", {}),
        "PQTCVerificationRegistry": (
            air + query + parameter.hex(),
            {
                "parameterLeft": parameter[:32].hex(),
                "parameterRight": parameter[32:].hex(),
                "airVerifier": air,
                "queryVerifier": query,
            },
        ),
        "PQTCClassicPool": (
            denomination + parameter.hex() + registry,
            {"denomination": denomination, "verificationRegistry": registry},
        ),
    }
    exact(set(record["name"] for record in records), set(expected_by_name),
          "BINDING_MISMATCH", "required deployment contracts")
    for record in records:
        name = record["name"]
        expected_args, expected_roles = expected_by_name[name]
        actual_args = decode_hex(record.get("constructorArgsHex", ""), f"{name}.constructorArgsHex", allow_empty=True).hex()
        exact(actual_args, expected_args, "BINDING_MISMATCH", f"{name} constructor arguments")
        role_ids = record.get("immutableRoles", {})
        exact(set(role_ids), set(expected_roles), "BINDING_MISMATCH", f"{name} immutable roles")
        for role, expected_word in expected_roles.items():
            immutable_id = role_ids[role]
            actual_word = decode_hex(
                record.get("immutableBindings", {}).get(immutable_id),
                f"{name}.immutableBindings[{immutable_id}]",
            ).hex()
            exact(actual_word, expected_word, "BINDING_MISMATCH", f"{name}.{role}")


def deployment_manifest_id(
    manifest: dict[str, Any], extracted_contracts: list[dict[str, Any]]
) -> tuple[str, dict[str, Any]]:
    projection = manifest["projection"]
    payload = {
        "schema": "PQTC_DEPLOYMENT_MANIFEST_V1",
        "proofSystemId": manifest["proofSystemId"].lower(),
        "chainId": projection["chainId"],
        "denominationWei": projection["denominationWei"],
        "addresses": projection["addresses"],
        "consumer": projection["addresses"]["pool"],
        "compilerProfile": {
            "sha256": manifest["compilerProfile"]["sha256"],
            "artifactSettings": manifest["compilerProfile"]["artifactSettings"],
        },
        "contracts": [
            {
                "name": record["name"],
                "address": projection["addresses"][
                    {
                        "PQTCAirStageVerifier": "airVerifier",
                        "PQTCQueryVerifier": "queryVerifier",
                        "PQTCVerificationRegistry": "registry",
                        "PQTCClassicPool": "pool",
                    }[record["name"]]
                ],
                "constructorArgsHex": record["constructorArgsHex"],
                "fullInitcodeKeccak256": extracted["fullInitcodeKeccak256"],
                "runtimeKeccak256": extracted["runtimeKeccak256"],
            }
            for record, extracted in zip(manifest["contracts"], extracted_contracts, strict=True)
        ],
    }
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    return "0x" + keccak256(encoded), payload


def check_manifest(
    manifest: dict[str, Any],
    repo: Path,
    artifact_overrides: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if keccak256(b"") != EMPTY_KECCAK:
        raise BindingError("KECCAK_SELF_TEST", "Ethereum Keccak-256 self-test failed")
    exact(manifest.get("schemaVersion"), 1, "SCHEMA_MISMATCH", "schemaVersion")
    contracts = manifest.get("contracts")
    order = manifest.get("contractOrder")
    if not isinstance(contracts, list) or not contracts:
        raise BindingError("EMPTY_EXPECTED_HASH", "contracts must be non-empty")
    names = [record.get("name") for record in contracts]
    exact(names, order, "CONTRACT_ORDER_MISMATCH", "ordered contract list")

    frozen = manifest.get("frozenV03", {})
    parameter_path = repo / frozen.get("parameterIdPath", "")
    actual_parameter = parameter_path.read_text(encoding="utf-8").strip().lower()
    exact(sha256_file(parameter_path), frozen.get("parameterIdSha256"),
          "PARAMETER_ID_MISMATCH", "frozen parameter-ID file SHA-256")
    parameter = manifest.get("proofSystemId", "").lower()
    exact(parameter, actual_parameter, "PARAMETER_ID_MISMATCH", "frozen parameter ID")
    if len(decode_hex(parameter, "proofSystemId")) != 64:
        raise BindingError("PARAMETER_ID_MISMATCH", "proofSystemId must be 64 bytes")
    frozen_manifest_path = repo / frozen.get("manifestPath", "")
    frozen_manifest = load_json(frozen_manifest_path)
    frozen_hashes = frozen_manifest.get("expected_runtime_code_hashes")
    exact(frozen_hashes, [], "FROZEN_BASELINE_CHANGED", "v0.3 frozen runtime hash list")
    exact(frozen.get("observedExpectedRuntimeCodeHashes"), frozen_hashes,
          "FROZEN_BASELINE_CHANGED", "recorded empty v0.3 runtime hash list")
    exact(sha256_file(frozen_manifest_path), frozen.get("manifestSha256"), "HASH_MISMATCH", "frozen manifest SHA-256")

    profile = manifest.get("compilerProfile", {})
    profile_path = repo / profile.get("path", "")
    exact(sha256_file(profile_path), profile.get("sha256"), "PROFILE_MISMATCH", "Foundry profile SHA-256")
    expected_settings = profile.get("artifactSettings")
    if not isinstance(expected_settings, dict):
        raise BindingError("PROFILE_MISMATCH", "artifactSettings must be an object")
    validate_constructor_bindings(manifest, contracts)

    extracted_contracts = []
    for record in contracts:
        override = (artifact_overrides or {}).get(record["name"])
        extracted = extract_contract(repo, record, override)
        exact(extracted["settings"], expected_settings | {"compilationTarget": record["compilationTarget"]},
              "PROFILE_MISMATCH", f"{record['name']} compiler settings")
        validate_expected(record, extracted)
        extracted_contracts.append(extracted)

    inventory = manifest.get("researchCandidates")
    if not isinstance(inventory, list) or not inventory:
        raise BindingError("EMPTY_CANDIDATE_INVENTORY", "researchCandidates must be non-empty")
    candidate_results = []
    for candidate in inventory:
        path = repo / candidate["source"]
        actual = sha256_file(path)
        exact(actual, candidate.get("sourceSha256"), "CANDIDATE_SOURCE_MISMATCH", candidate["source"])
        exact(candidate.get("canonicalFoundryArtifact"), None, "UNREVIEWED_CANDIDATE_ARTIFACT", candidate["id"])
        candidate_results.append({
            "id": candidate["id"], "source": candidate["source"], "sourceSha256": actual,
            "bindingStatus": "SOURCE_ONLY_NO_CANONICAL_FOUNDRY_ARTIFACT",
        })

    manifest_id, manifest_payload = deployment_manifest_id(manifest, extracted_contracts)
    expected_manifest_id = manifest.get("expectedDeploymentManifestId")
    if not isinstance(expected_manifest_id, str) or not expected_manifest_id:
        raise BindingError("EMPTY_EXPECTED_HASH", "expectedDeploymentManifestId")
    exact(manifest_id, expected_manifest_id, "HASH_MISMATCH", "deploymentManifestId")
    return {
        "schemaVersion": 1,
        "study": "runtime-binding",
        "result": "PASS_RESEARCH_BINDING_CHECK",
        "deploymentReady": False,
        "deploymentReadinessReason": "frozen v0.3 expected_runtime_code_hashes is empty and the addresses/chain are projections, not a reviewed deployment",
        "factClassification": {
            "measured": "hashes and sizes extracted from the present canonical Foundry artifacts",
            "projected": "constructor-resolved initcode/runtime hashes use the manifest's explicit hypothetical deployment addresses and denomination",
        },
        "proofSystemId": parameter,
        "frozenRuntimeHashList": frozen_hashes,
        "deploymentManifestId": manifest_id,
        "deploymentManifestPayload": manifest_payload,
        "contracts": extracted_contracts,
        "researchCandidates": candidate_results,
    }


def regression_cases(manifest: dict[str, Any], repo: Path) -> list[dict[str, Any]]:
    cases: list[tuple[str, str, Any]] = []

    def add(name: str, expected_code: str, mutation: Any) -> None:
        cases.append((name, expected_code, mutation))

    add("byte_change", "HASH_MISMATCH", "byte_change")
    add("reordered_contracts", "CONTRACT_ORDER_MISMATCH", "reordered_contracts")
    add("wrong_compiler", "PROFILE_MISMATCH", "wrong_compiler")
    add("wrong_profile", "PROFILE_MISMATCH", "wrong_profile")
    add("unresolved_link_reference", "UNRESOLVED_LINKS", "unresolved_link_reference")
    add("unresolved_immutable_reference", "UNRESOLVED_IMMUTABLES", "unresolved_immutable_reference")
    add("empty_hashes", "EMPTY_EXPECTED_HASH", "empty_hashes")
    add("wrong_parameter_id", "PARAMETER_ID_MISMATCH", "wrong_parameter_id")

    output = []
    for name, expected_code, mutation in cases:
        altered = copy.deepcopy(manifest)
        overrides: dict[str, dict[str, Any]] = {}
        if mutation == "reordered_contracts":
            altered["contracts"][0], altered["contracts"][1] = altered["contracts"][1], altered["contracts"][0]
        elif mutation == "unresolved_immutable_reference":
            target = altered["contracts"][0]
            artifact = load_json(repo / target["artifact"])
            artifact["deployedBytecode"]["immutableReferences"] = {
                "999999": [{"start": 0, "length": 32}]
            }
            overrides[target["name"]] = artifact
        elif mutation == "empty_hashes":
            altered["contracts"][0]["expected"]["runtimeKeccak256"] = ""
        elif mutation == "wrong_parameter_id":
            altered["proofSystemId"] = "0x" + "00" * 64
        else:
            target = altered["contracts"][0]
            artifact = load_json(repo / target["artifact"])
            if mutation == "byte_change":
                raw = artifact["deployedBytecode"]["object"]
                artifact["deployedBytecode"]["object"] = ("01" if raw[:2] != "01" else "00") + raw[2:]
            elif mutation == "wrong_compiler":
                artifact["metadata"]["compiler"]["version"] = "0.8.29+commit.ab55807c"
            elif mutation == "wrong_profile":
                artifact["metadata"]["settings"]["optimizer"]["runs"] = 1
            elif mutation == "unresolved_link_reference":
                artifact["bytecode"]["linkReferences"] = {
                    "Library.sol": {"Library": [{"start": 1, "length": 20}]}
                }
            overrides[target["name"]] = artifact
        try:
            check_manifest(altered, repo, overrides)
        except BindingError as exc:
            passed = exc.code == expected_code
            output.append({
                "case": name,
                "expectedFailureCode": expected_code,
                "actualFailureCode": exc.code,
                "passed": passed,
            })
        else:
            output.append({
                "case": name, "expectedFailureCode": expected_code,
                "actualFailureCode": None, "passed": False,
            })
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("extract", "check", "regressions"))
    parser.add_argument("--manifest", default="research/runtime-binding/manifest.json")
    parser.add_argument("--repo", default=None, help="repository root (inferred by default)")
    parser.add_argument("--output", default=None, help="write canonical JSON here; stdout otherwise")
    args = parser.parse_args()
    repo = Path(args.repo).resolve() if args.repo else Path(__file__).resolve().parents[2]
    manifest = load_json(repo / args.manifest)
    try:
        if args.command == "extract":
            value = {
                "schemaVersion": 1,
                "contracts": [extract_contract(repo, record) for record in manifest["contracts"]],
            }
        elif args.command == "check":
            value = check_manifest(manifest, repo)
        else:
            results = regression_cases(manifest, repo)
            value = {
                "schemaVersion": 1,
                "study": "runtime-binding-negative-regressions",
                "result": "PASS" if all(item["passed"] for item in results) else "FAIL",
                "cases": results,
            }
            if value["result"] != "PASS":
                raise BindingError("REGRESSION_FAILURE", "one or more negative cases did not fail as expected")
    except (BindingError, OSError, KeyError, TypeError) as exc:
        if isinstance(exc, BindingError):
            error = {"result": "FAIL", "code": exc.code, "detail": exc.detail}
        else:
            error = {"result": "FAIL", "code": "MALFORMED_INPUT", "detail": str(exc)}
        print(json.dumps(error, sort_keys=True), file=sys.stderr)
        return 1
    if args.output:
        write_json(repo / args.output, value)
    else:
        print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
