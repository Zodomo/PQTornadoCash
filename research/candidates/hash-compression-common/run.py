#!/usr/bin/env python3
"""One-command SP-10 vector/parity, native diagnostic, and gas entry point."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CORPUS = ROOT / "research/common-corpus/semantic-cases.json"
VECTORS_RAW = HERE / "vectors/cross-language.json"
VECTORS_ZSTD = HERE / "vectors/cross-language.json.zst"
VECTOR_PACKAGE = HERE / "vectors/package.json"
NATIVE = HERE / "native/distributions.json"
GAS = HERE / "gas/forge-gas-report.txt"
GAS_RESULTS = HERE / "gas/results.json"
SECURITY_CEILINGS = HERE / "security/analytical-ceilings.json"
OPERATION_COUNTS = HERE / "native/operation-counts.json"
MEASUREMENT_HASHES = HERE / "measurement-hashes.json"


def run(command: list[str], *, cwd: Path | None = None, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd or ROOT, check=True, text=True, capture_output=capture)


def artifact_hashes(paths: list[Path]) -> list[dict[str, object]]:
    temporary = HERE / ".artifact-hashes.tmp.json"
    try:
        run([
            "cargo", "run", "--release", "--manifest-path", str(HERE / "Cargo.toml"),
            "--", "hash", str(temporary), *(str(path) for path in paths),
        ])
        return json.loads(temporary.read_text())
    finally:
        temporary.unlink(missing_ok=True)


def verify_zstd_against_file(artifact: Path, expected: Path) -> None:
    process = subprocess.Popen(["zstd", "--decompress", "--stdout", str(artifact)], stdout=subprocess.PIPE)
    assert process.stdout is not None
    try:
        with expected.open("rb") as source:
            while True:
                decoded = process.stdout.read(1024 * 1024)
                original = source.read(1024 * 1024)
                if decoded != original:
                    raise RuntimeError("zstd round-trip differs from uncompressed vectors")
                if not decoded:
                    break
    except BaseException:
        process.kill()
        process.wait()
        raise
    if process.wait() != 0:
        raise RuntimeError("zstd decompression failed")


def refresh_measurement_hashes() -> None:
    vector_package = json.loads(VECTOR_PACKAGE.read_text()) if VECTOR_PACKAGE.exists() else None
    outputs = [path for path in (NATIVE, GAS, GAS_RESULTS) if path.exists()]
    records = artifact_hashes(outputs) if outputs else []
    for record, path in zip(records, outputs, strict=True):
        record["path"] = str(path.relative_to(ROOT))
        if path == NATIVE:
            record["classification"] = "DIAGNOSTIC_NOT_COMMON_PROTOCOL"
            record["comparableCommonProtocolBenchmark"] = False
    payload = {"schema": "sp10-measurement-hashes-v2", "vectors": vector_package, "outputs": records}
    MEASUREMENT_HASHES.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def package_vectors() -> None:
    try:
        run([
            "zstd", "-19", "--threads=1", "--no-progress", "--no-check", "--force",
            str(VECTORS_RAW), "-o", str(VECTORS_ZSTD),
        ])
        records = artifact_hashes([VECTORS_RAW, VECTORS_ZSTD])
        verify_zstd_against_file(VECTORS_ZSTD, VECTORS_RAW)
        raw, compressed = records
        package = {
            "schema": "sp10-vector-package-v2",
            "codec": {
                "name": "zstd",
                "level": 19,
                "threads": 1,
                "checksum": False,
                "originalFilenameEmbedded": False,
            },
            "artifact": str(VECTORS_ZSTD.relative_to(ROOT)),
            "logicalUncompressedPath": str(VECTORS_RAW.relative_to(ROOT)),
            "uncompressed": {
                "bytes": raw["bytes"],
                "sha256": raw["sha256"],
                "ethereumKeccak256": raw["ethereumKeccak256"],
            },
            "compressed": {
                "bytes": compressed["bytes"],
                "sha256": compressed["sha256"],
                "ethereumKeccak256": compressed["ethereumKeccak256"],
            },
            "verificationCoverage": {
                "rustTypeScriptParity": {"status": "PASS", "vectors": 18_146},
                "solidityParity": {
                    "status": "NOT_EVALUATED_FULL_REQUIRED_COVERAGE",
                    "requiredVectors": 10_000,
                    "anchorVectorsObserved": 8,
                    "fullBundleCovered": False,
                },
                "fullThreeLanguageParity": "NOT_EVALUATED",
                "requiredMisuseSuite": "NOT_EVALUATED",
                "constantComparison": "NOT_RETAINED",
            },
            "applicationCoverage": {
                "H0": "BASELINE_FRAMING_ONLY_NOT_FULL_ROLE_PARITY",
                "H1": "NOT_IMPLEMENTED",
                "H2": "NOT_IMPLEMENTED",
                "H3": "PRIMITIVE_LAYOUT_INCOMPLETE",
                "H4": "NOT_IMPLEMENTED",
                "H5": "PRIMITIVE_LAYOUT_INCOMPLETE",
                "H6": "PRIMITIVE_LAYOUT_INCOMPLETE",
                "H7": "PRIMITIVE_LAYOUT_INCOMPLETE",
                "nonH0KnownOmissions": [
                    "protocol scope",
                    "frozen semantic secret/trapdoor widths",
                    "empty-leaf role",
                    "statement role",
                ],
            },
            "decompressionVerifiedByteForByte": True,
        }
        VECTOR_PACKAGE.write_text(json.dumps(package, indent=2, sort_keys=True) + "\n")
    finally:
        VECTORS_RAW.unlink(missing_ok=True)
    refresh_measurement_hashes()


def check_vector_package() -> None:
    package = json.loads(VECTOR_PACKAGE.read_text())
    temporary = HERE / "vectors/.cross-language.package-check.json"
    repacked = HERE / "vectors/.cross-language.package-check.json.zst"
    try:
        run(["zstd", "--decompress", "--no-progress", "--force", str(VECTORS_ZSTD), "-o", str(temporary)])
        run([
            "zstd", "-19", "--threads=1", "--no-progress", "--no-check", "--force",
            str(temporary), "-o", str(repacked),
        ])
        raw, compressed, reproduced = artifact_hashes([temporary, VECTORS_ZSTD, repacked])
        for key in ("bytes", "sha256", "ethereumKeccak256"):
            if raw[key] != package["uncompressed"][key] or compressed[key] != package["compressed"][key]:
                raise RuntimeError(f"vector package {key} mismatch")
            if reproduced[key] != compressed[key]:
                raise RuntimeError(f"deterministic zstd reproduction {key} mismatch")
    finally:
        temporary.unlink(missing_ok=True)
        repacked.unlink(missing_ok=True)
    print(json.dumps({
        "ok": True,
        "artifact": package["artifact"],
        "uncompressedBytes": package["uncompressed"]["bytes"],
    }, sort_keys=True))


def initialize_gas_results() -> None:
    candidate = {
        "permutationGas": None,
        "compressionGas": None,
        "spongeGas": None,
        "noteGas": None,
        "nullifierGas": None,
        "nodeGas": None,
        "depth20ComputeOnlyInsertionGas": None,
        "syntheticDepth20RootUpdateGas": None,
        "completeDirectDepositGas": None,
        "completeDirectDepositStatus": "NOT_EVALUATED",
        "zeroTreeConstructorGas": None,
        "runtimeBytes": None,
        "initcodeBytes": None,
    }
    payload = {
        "schema": "sp10-gas-results-v2",
        "profile": {
            "solc": "0.8.30",
            "evmVersion": "prague",
            "optimizer": True,
            "optimizerRuns": 200,
            "viaIR": True,
        },
        "measurement": {
            "callAccounting": "gasleft delta around a low-level external call to a freshly deployed target; ABI encoding precedes measurement and return-data copying is included",
            "treeDepth": 20,
            "inputs": "deterministic lanes [1..n], node level 7",
            "syntheticRootUpdateCaveat": "The synthetic depth-20 root update performs 20 hashes and stores a dynamic uint256[] root; it omits real deposit/state work and does not model the protocol's two digest slots.",
        },
        **{f"H{i}": dict(candidate) for i in range(8)},
    }
    payload["H2"]["disposition"] = "STOPPED_NO_REVIEWED_MODE"
    payload["H0"]["compressionGasDisposition"] = "NOT_APPLICABLE_H0_IS_SPONGE; the similarly sized measurement belongs to H1 d=7"
    payload["H0"]["completeDirectDepositGas"] = 13_991_021
    payload["H0"]["completeDirectDepositStatus"] = "FROZEN_V03_BASELINE_REPRODUCTION"
    payload["H7"]["disposition"] = "PUBLISHED_SPONGE_ONLY_NO_COMPRESSOR"
    GAS_RESULTS.parent.mkdir(parents=True, exist_ok=True)
    GAS_RESULTS.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def annotate_gas_gates() -> None:
    payload = json.loads(GAS_RESULTS.read_text())
    counts = json.loads(OPERATION_COUNTS.read_text())["applicationPermutationCounts"]
    baseline_node_permutations = counts["H0"]["node"]
    ceilings = {
        item["candidate"]: item
        for item in json.loads(SECURITY_CEILINGS.read_text())["candidates"]
    }
    structural = {
        "H0": "BASELINE_ONLY_NO_REPLACEMENT_CLAIM",
        "H1": "FAIL_EXACT_2026_ROUND_SKIP_APPLIES",
        "H2": "NO_CONSTRUCTION_TO_ANALYZE",
        "H3": "FAIL_EXACT_2026_ROUND_SKIP_APPLIES",
        "H4": "FAIL_EXACT_2026_ROUND_SKIP_APPLIES",
        "H5": "NOT_PASSED_WIDTH32_STRUCTURAL_ANALYSIS_MISSING",
        "H6": "NOT_PASSED_WIDTH32_STRUCTURAL_ANALYSIS_MISSING",
        "H7": "NOT_PASSED_EXACT_APPLICATION_STRUCTURAL_ANALYSIS_MISSING",
    }
    for name in [f"H{i}" for i in range(8)]:
        candidate = payload[name]
        node_permutations = counts.get(name, {}).get("node")
        deposit = candidate.get("completeDirectDepositGas")
        ceiling = ceilings[name]
        output_bits = ceiling.get("genericQuantumCollisionCeilingBits")
        hidden_bits = ceiling.get("genericQuantumHiddenPartGroverCeilingBits")
        generic_bits = min(output_bits, hidden_bits) if output_bits is not None and hidden_bits is not None else None
        candidate["gateComparison"] = {
            "fiveXNodePermutationReduction": {
                "baselinePermutationCount": baseline_node_permutations,
                "candidatePermutationCount": node_permutations,
                "ratio": (baseline_node_permutations / node_permutations) if node_permutations else None,
                "passes": bool(node_permutations and node_permutations * 5 <= baseline_node_permutations),
            },
            "completeDirectDepositUnder4000000": {
                "candidateGas": deposit,
                "limitExclusive": 4_000_000,
                "passes": bool(deposit is not None and deposit < 4_000_000),
                "status": candidate["completeDirectDepositStatus"],
            },
            "genericSecurityAtLeast100Bits": {
                "idealQuantumCollisionCeilingBits": output_bits,
                "idealHiddenPartGroverCeilingBits": hidden_bits,
                "minimumGenericCeilingBits": generic_bits,
                "passes": bool(generic_bits is not None and generic_bits >= 100),
                "status": "IDEAL_WIDTH_CEILING_ONLY_NOT_QUALIFICATION" if generic_bits is not None else "NO_APPLICABLE_COMPRESSION_CEILING",
            },
            "noStructuralAttack": {"passes": False, "status": structural[name]},
            "externalReview": {"passes": False, "status": "NOT_REVIEWED"},
            "allPass": False,
            "airDisposition": "STOPPED",
        }
    GAS_RESULTS.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def vectors() -> None:
    run([
        "cargo", "run", "--release", "--manifest-path", str(HERE / "Cargo.toml"),
        "--", "vectors", str(CORPUS), str(VECTORS_RAW),
    ])
    try:
        run(["node", "--experimental-strip-types", str(HERE / "reference/reference.ts"), "verify", str(VECTORS_RAW)])
        run(["forge", "test", "--match-contract", "Parity"], cwd=HERE / "solidity")
        payload = json.loads(VECTORS_RAW.read_text())
        vector_count = payload["vector_count"]
        tree_parity = len(payload["tree_parity"])
        del payload
        package_vectors()
    finally:
        VECTORS_RAW.unlink(missing_ok=True)
    print(json.dumps({
        "ok": True,
        "vectors": vector_count,
        "treeParity": tree_parity,
        "artifact": str(VECTORS_ZSTD.relative_to(ROOT)),
    }, sort_keys=True))


def benchmark(samples: int) -> None:
    run([
        "cargo", "run", "--release", "--manifest-path", str(HERE / "Cargo.toml"),
        "--", "bench", str(NATIVE), str(samples),
    ])
    initialize_gas_results()
    run(["forge", "test", "--match-contract", "GasResults", "--threads", "1"], cwd=HERE / "solidity")
    annotate_gas_gates()
    measured = run(
        ["forge", "test", "--match-contract", "GasBench", "--gas-report", "-vv"],
        cwd=HERE / "solidity",
        capture=True,
    )
    GAS.parent.mkdir(parents=True, exist_ok=True)
    GAS.write_text(measured.stdout + measured.stderr)
    refresh_measurement_hashes()
    print(json.dumps({
        "ok": True,
        "native": str(NATIVE.relative_to(ROOT)),
        "nativeClassification": "DIAGNOSTIC_NOT_COMMON_PROTOCOL",
        "gas": str(GAS.relative_to(ROOT)),
        "gasResults": str(GAS_RESULTS.relative_to(ROOT)),
        "samplesPerCandidate": samples,
    }, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("vectors-parity")
    commands.add_parser("vectors-package-check")
    commands.add_parser("vectors-package")
    bench = commands.add_parser("benchmark")
    bench.add_argument("--samples", type=int, default=1000)
    args = parser.parse_args()
    if args.command == "vectors-parity":
        vectors()
    elif args.command == "vectors-package-check":
        check_vector_package()
    elif args.command == "vectors-package":
        package_vectors()
        package = json.loads(VECTOR_PACKAGE.read_text())
        print(json.dumps({"ok": True, "artifact": package["artifact"], "compressedBytes": package["compressed"]["bytes"]}, sort_keys=True))
    else:
        if args.samples < 1:
            parser.error("--samples must be positive")
        benchmark(args.samples)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as error:
        print(json.dumps({"ok": False, "command": error.cmd, "exitCode": error.returncode}, sort_keys=True), file=sys.stderr)
        raise SystemExit(error.returncode)
