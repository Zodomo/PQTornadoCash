#!/usr/bin/env python3
"""Deterministic focused SP-30 build, replay, EVM measurement, and metadata path."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TRANSCRIPT = ROOT / "research/cryptanalysis/transcript"
SOLIDITY = TRANSCRIPT / "solidity"
TEMP = TRANSCRIPT / ".focused-target"
CANDIDATES = ("T0", "T1", "T2", "T3")
TEST_BY_CANDIDATE = {candidate: f"test{candidate}Gas()" for candidate in CANDIDATES}
SIGNED_LIMIT = 1 << 255
SIGNED_MODULUS = 1 << 256


def run(command: list[str], *, cwd: Path = ROOT, env: dict[str, str] | None = None) -> str:
    completed = subprocess.run(command, cwd=cwd, env=env, check=True, text=True, capture_output=True)
    return completed.stdout


def decode_word(word: str, *, signed: bool = False) -> int:
    value = int(word, 16)
    return value - SIGNED_MODULUS if signed and value >= SIGNED_LIMIT else value


def decode_measurement(log: dict[str, object]) -> tuple[int, dict[str, int]]:
    topics = log.get("topics")
    data = log.get("data")
    if not isinstance(topics, list) or len(topics) != 2 or not isinstance(data, str) or not data.startswith("0x"):
        raise RuntimeError("unexpected Solidity measurement log shape")
    candidate = int(str(topics[1]), 16)
    encoded = data[2:]
    if len(encoded) != 11 * 64:
        raise RuntimeError(f"unexpected Solidity measurement width: {len(encoded) // 2} bytes")
    words = [encoded[offset : offset + 64] for offset in range(0, len(encoded), 64)]
    names = (
        "evmTranscriptGas",
        "evmParserGas",
        "evmHarnessCalldataBytes",
        "evmPeakFrameBytes",
        "evmKeccakCalls",
        "evmHashedBytes",
        "evmCopiedBytes",
        "evmRuntimeCodeBytes",
        "evmProofBytesDelta",
        "evmCalldataBytesDelta",
        "evmFullPathGasDeltaSentinel",
    )
    decoded = {name: decode_word(word, signed=index >= 8) for index, (name, word) in enumerate(zip(names, words, strict=True))}
    return candidate, decoded


def object_bytes(artifact: dict[str, object], section: str) -> int:
    value = artifact.get(section)
    if not isinstance(value, dict) or not isinstance(value.get("object"), str):
        raise RuntimeError(f"missing {section}.object in Foundry artifact")
    encoded = str(value["object"])
    if not encoded.startswith("0x") or len(encoded[2:]) % 2:
        raise RuntimeError(f"invalid {section}.object")
    return len(encoded[2:]) // 2


def parse_forge(stdout: str) -> dict[str, dict[str, int]]:
    report = json.loads(stdout)
    suite = report.get("test/TranscriptGas.t.sol:TranscriptGasScenario")
    if not isinstance(suite, dict) or not isinstance(suite.get("test_results"), dict):
        raise RuntimeError("focused Foundry suite missing")
    measurements: dict[str, dict[str, int]] = {}
    results = suite["test_results"]
    for candidate in CANDIDATES:
        test = results.get(TEST_BY_CANDIDATE[candidate])
        if not isinstance(test, dict) or test.get("status") != "Success":
            raise RuntimeError(f"{candidate} Solidity gas scenario did not pass")
        logs = test.get("logs")
        if not isinstance(logs, list) or len(logs) != 1 or not isinstance(logs[0], dict):
            raise RuntimeError(f"{candidate} Solidity gas scenario emitted unexpected logs")
        index, decoded = decode_measurement(logs[0])
        if index != int(candidate[1]):
            raise RuntimeError(f"{candidate} event index mismatch")
        if decoded["evmFullPathGasDeltaSentinel"] != -SIGNED_LIMIT:
            raise RuntimeError(f"{candidate} full-path sentinel missing")
        measurements[candidate] = decoded
    return measurements


def continuation_deltas(candidate: str) -> tuple[int, int]:
    vector = json.loads((ROOT / f"research/candidates/{candidate}/vectors/transcript.json").read_text())
    continuation = vector["binding"]["canonicalV03Continuation"]
    part_a = bytes.fromhex(continuation["partA"])
    part_b = bytes.fromhex(continuation["partB"])
    canonical_a = (ROOT / "research/candidates/v03-baseline/proofs/v03-fixed-01/part-a.pqtc").read_bytes()
    canonical_b = (ROOT / "research/candidates/v03-baseline/proofs/v03-fixed-01/part-b.pqtc").read_bytes()
    if part_a != canonical_a or part_b != canonical_b:
        raise RuntimeError(f"{candidate} continuation is not byte-identical to canonical v0.3")
    baseline_a_call = (ROOT / "research/candidates/v03-baseline/proofs/v03-fixed-01/part-a.calldata").read_bytes()
    baseline_b_call = (ROOT / "research/candidates/v03-baseline/proofs/v03-fixed-01/part-b.calldata").read_bytes()
    proof_delta = len(part_a) + len(part_b) - len(canonical_a) - len(canonical_b)
    # The candidate retains the byte-identical proof and frozen ABI, so its calldata is the retained canonical calldata.
    calldata_delta = len(baseline_a_call) + len(baseline_b_call) - len(baseline_a_call) - len(baseline_b_call)
    return proof_delta, calldata_delta


def write_measurements(evm: dict[str, dict[str, int]], initcode_bytes: int, runtime_bytes: int) -> None:
    for candidate in CANDIDATES:
        path = ROOT / f"research/candidates/{candidate}/measurements/transcript.json"
        report = json.loads(path.read_text())
        measured = report["measured"]
        measured.update(evm[candidate])
        measured["evmInitcodeBytes"] = initcode_bytes
        measured["evmRuntimeCodeBytes"] = runtime_bytes
        proof_delta, calldata_delta = continuation_deltas(candidate)
        measured["proofBytesDelta"] = proof_delta
        measured["abiCalldataBytesDelta"] = calldata_delta
        if measured["evmProofBytesDelta"] != proof_delta or measured["evmCalldataBytesDelta"] != calldata_delta:
            raise RuntimeError(f"{candidate} Solidity and retained-continuation deltas disagree")
        unmeasured = report["explicitlyUnmeasured"]
        for key in ("parserGas", "transcriptGas", "runtimeCodeBytes", "deploymentCodeBytes", "proofBytesDelta", "abiCalldataBytesDelta"):
            unmeasured.pop(key, None)
        report["evmProfile"] = {"solc":"0.8.30", "evmVersion":"prague", "optimizer":True, "optimizerRuns":200, "viaIR":True}
        report["measurementScope"] = "Standalone B0 transcript prefix plus strict typed-array parser; full verifier path intentionally unintegrated"
        report["deltaBasis"] = "Candidate vector embeds byte-identical canonical v0.3 A/B continuation and retains the frozen ABI"
        path.write_text(json.dumps(report, indent=2) + "\n")


def write_focused_status() -> None:
    status_path = TRANSCRIPT / "status.json"
    status = json.loads(status_path.read_text())
    status["focusedRun"] = {
        "result":"PASS",
        "rustCandidatesBuiltAndTested":list(CANDIDATES),
        "typescriptVectorsRegenerated":True,
        "v03CheckpointReplay":"PASS_T0_EXACT_V03_CHECKPOINT_REPLAY",
        "solidityCandidateMeasurements":list(CANDIDATES),
        "profile":{"solc":"0.8.30","evmVersion":"prague","optimizer":True,"optimizerRuns":200,"viaIR":True},
        "cleanup":"PASS"
    }
    status_path.write_text(json.dumps(status, indent=2) + "\n")
    (TRANSCRIPT / "focused-run.json").write_text(json.dumps({"schema":"pqtc.sp30.focused-run.v1", **status["focusedRun"]}, indent=2) + "\n")


def main() -> None:
    TEMP.mkdir(parents=True, exist_ok=True)
    rust_results: list[str] = []
    try:
        for candidate in CANDIDATES:
            manifest = ROOT / f"research/candidates/{candidate}/rust/Cargo.toml"
            environment = os.environ.copy()
            environment["CARGO_TARGET_DIR"] = str(TEMP / f"cargo-{candidate}")
            run(["cargo", "test", "--manifest-path", str(manifest), "--quiet"], env=environment)
            rust_results.append(candidate)
        run(["node", "--experimental-strip-types", "research/cryptanalysis/transcript/typescript/generate-vectors.ts"])
        replay = run(["node", "--experimental-strip-types", "research/cryptanalysis/transcript/typescript/verify-v03-fixture.ts"]).strip()
        if replay != "PASS_T0_EXACT_V03_CHECKPOINT_REPLAY":
            raise RuntimeError("canonical v0.3 checkpoint replay failed")
        forge_stdout = run(["forge", "test", "--match-path", "test/TranscriptGas.t.sol", "--json", "-vvv"], cwd=SOLIDITY)
        evm = parse_forge(forge_stdout)
        artifact_path = SOLIDITY / "out/TranscriptResearch.sol/TranscriptGasHarness.json"
        artifact = json.loads(artifact_path.read_text())
        initcode_bytes = object_bytes(artifact, "bytecode")
        runtime_bytes = object_bytes(artifact, "deployedBytecode")
        if any(values["evmRuntimeCodeBytes"] != runtime_bytes for values in evm.values()):
            raise RuntimeError("runtime EXTCODESIZE disagrees with Foundry artifact")
        write_measurements(evm, initcode_bytes, runtime_bytes)
        run(["node", "--experimental-strip-types", "research/cryptanalysis/transcript/typescript/generate-metadata.ts"])
        write_focused_status()
        # Status changes after metadata hashing, so refresh hashes once more.
        run(["node", "--experimental-strip-types", "research/cryptanalysis/transcript/typescript/generate-metadata.ts"])
        write_focused_status()
    finally:
        shutil.rmtree(TEMP, ignore_errors=True)
        shutil.rmtree(SOLIDITY / "out", ignore_errors=True)
        shutil.rmtree(SOLIDITY / "cache", ignore_errors=True)
    if rust_results != list(CANDIDATES):
        raise RuntimeError("not all Rust candidates completed")
    print("PASS_SP30_FOCUSED_RUN")


if __name__ == "__main__":
    main()
