#!/usr/bin/env python3
"""Run SP-31 research kernels and regenerate candidate evidence.

This driver never reads .env, contacts RPC endpoints, or modifies production paths.
Without --metadata-only it executes only the isolated Rust and Foundry packages below
this directory. Complete-transaction fields remain unavailable unless the frozen
canonical proof fixture exists; isolated kernel deltas are never added together.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
HISTORIC_BASELINE = {
    "source": "historic report comparator; never used as the projection anchor",
    "executionGas": {"partA": 14891070, "partB": 12356373},
    "totalGas": {"partA": 16539302, "partB": 14105909},
    "registryExecutionGas": {"partA": 14056853, "partB": 11470158},
    "abiBytes": {"partA": 102308, "partB": 108644},
    "proofBytes": {"partA": 101990, "partB": 108294},
    "zeroBytes": {"partA": 808, "partB": 814},
}


def load_canonical_baseline() -> dict:
    run_path = ROOT / "research/runs/v03-fixed-01.json"
    if not run_path.is_file():
        raise RuntimeError(f"source-bound canonical run is required: {run_path}")
    raw = run_path.read_bytes()
    run = json.loads(raw)
    if run.get("candidate_id") != "C00/v03-baseline":
        raise RuntimeError("canonical run has wrong candidate_id")
    if run.get("git", {}).get("commit") != "00f829001999ee66da6fd5161c4c205c07d0b937":
        raise RuntimeError("canonical run is not bound to the frozen v0.3 commit")
    artifacts = {Path(a["path"]).name: a for a in run["artifacts"]}
    required = ("part-a.pqtc", "part-b.pqtc", "part-a.calldata", "part-b.calldata")
    if any(name not in artifacts for name in required):
        raise RuntimeError("canonical run omits proof/calldata artifacts")
    exact = {}
    for name in required:
        path = ROOT / artifacts[name]["path"]
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if len(data) != artifacts[name]["bytes"] or digest != artifacts[name]["digests"]["sha256"]:
            raise RuntimeError(f"canonical artifact mismatch: {name}")
        exact[name] = {"bytes": len(data), "zeroBytes": data.count(0), "sha256": digest}
    gas_a = {row["name"]: row["total_gas"] for row in run["evm"]["gas_scenarios"]}
    gas_b = {row["name"]: row["total_gas"] for row in run["evm"]["part_b_gas_scenarios"]}
    return {
        "source": {"kind": "source-bound canonical run", "record": str(run_path.relative_to(ROOT)), "recordSha256": hashlib.sha256(raw).hexdigest(), "commit": run["git"]["commit"]},
        "executionGas": {"partA": run["evm"]["component_gas"]["pool_a_execution"], "partB": run["evm"]["component_gas"]["pool_b_execution"]},
        "totalGas": {"partA": gas_a["ACTIVE_EIP7623"], "partB": gas_b["ACTIVE_EIP7623"]},
        "scenarioGas": {
            "partA": {"active": gas_a["ACTIVE_EIP7623"], "uniform64": gas_a["FUTURE_EIP7976_64_64"], "uniform96": gas_a["DRAFT_EIP8311_96_96"]},
            "partB": {"active": gas_b["ACTIVE_EIP7623"], "uniform64": gas_b["FUTURE_EIP7976_64_64"], "uniform96": gas_b["DRAFT_EIP8311_96_96"]},
        },
        "registryExecutionGas": None,
        "abiBytes": {"partA": exact["part-a.calldata"]["bytes"], "partB": exact["part-b.calldata"]["bytes"]},
        "proofBytes": {"partA": exact["part-a.pqtc"]["bytes"], "partB": exact["part-b.pqtc"]["bytes"]},
        "zeroBytes": {"partA": exact["part-a.calldata"]["zeroBytes"], "partB": exact["part-b.calldata"]["zeroBytes"]},
        "runtimeBytes": run["evm"]["runtime_bytes"],
        "proverNs": round(run["prover"]["proof_only_ms"] * 1_000_000),
        "nativeVerifierNs": round(run["prover"]["native_verify_ms"] * 1_000_000),
        "artifacts": exact,
    }


BASELINE = load_canonical_baseline()
CANDIDATES = {
    "V1": ("Streaming alpha accumulation", "Horner and forward streaming eliminate the power vector; reverse Horner is permitted only where coefficient order is fixed before alpha."),
    "V2": ("Checked inverse witnesses", "Witnesses are accepted only for denominators whose nonzero obligation is independently enforced. Zero-legal batch and selector legs retain native handling."),
    "V3": ("Fused canonical parse and dot product", "Every big-endian u32 is rejected at p before it contributes to the accumulator; there is no reduction modulo p."),
    "V4": ("Calldata-native bounded-memory evaluation", "Loops are length-bounded before entry and consume calldata directly; V3+V4 is the simplifying combination."),
    "V5": ("Fixed, derived, and checked calldata tables", "Code-embedded powers, in-EVM derivation, and recurrence-checked calldata are measured separately with deployment/runtime effects."),
    "V6": ("Query-point computation strategies", "Exponentiation, incremental generation, and recurrence-checked supplied points are compared; proof-supplied points remain transcript-bound."),
    "V7": ("Exact MMCS frontier, cap, and digest-width variants", "Exact binary frontier counts are used. 384/320-bit truncation is rejected absent external review; 256-bit is only a lower bound."),
    "V8": ("Uniquely decodable canonical proof codecs", "31-bit packing has exact section lengths, canonical field rejection, and zero terminal padding. Derived-value omission is allowed only when recomputed from prior transcript state."),
    "V9": ("Asymmetric query split and AIR placement", "All required 8/24 through 16/16 splits and both AIR placements are projected against one component model; minimum margin, not equal count, is optimized."),
}
NEGATIVE = {
    "V1": ["Horner over coefficients in forward protocol order changes the polynomial and is rejected by differential equality.", "Streaming cannot cross an absorb/challenge boundary."],
    "V2": ["d=0 is rejected before witness multiplication.", "Inverse witnesses are forbidden for zero-legal selector and batch legs.", "Noncanonical and incorrect witnesses are rejected."],
    "V3": ["u32 values at or above BabyBear p are rejected, never reduced.", "Truncated and overlong sections are rejected before the loop."],
    "V4": ["Lengths above 512 and offset-plus-length overflow are rejected before allocation or evaluation.", "Calldata aliasing does not bypass per-element canonical checks."],
    "V5": ["A checked table with wrong first value or recurrence is rejected.", "Calldata tables do not become trusted constants merely by transcript absorption."],
    "V6": ["Supplied point zero, wrong recurrence, noncanonical point, or wrong count is rejected.", "Points derived after their binding transcript challenge are not accepted."],
    "V7": ["Duplicate, unsorted, and out-of-range indices are rejected.", "Frontier counts below the exact worst case are not accepted as bounds.", "384/320 truncation has no external review; 256-bit is not acceptable for the 100-bit quantum collision target."],
    "V8": ["Noncanonical field, truncated section, trailing byte, nonzero padding, count overflow, and section overrun are rejected.", "Unframed concatenated packed sections are not uniquely decodable and are rejected."],
    "V9": ["Only the enumerated splits totaling 32 are modeled.", "A split is not selected from isolated gas alone when its calldata floor or other part has lower margin."],
}


def dump(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_native(repetitions: int) -> dict:
    with tempfile.NamedTemporaryFile(suffix=".json") as output:
        subprocess.run([
            "cargo", "run", "--release", "--quiet", "--manifest-path", str(HERE / "Cargo.toml"), "--",
            "--output", output.name, "--repetitions", str(repetitions),
        ], cwd=ROOT, check=True)
        return json.loads(Path(output.name).read_text())


def run_solidity() -> tuple[dict, str]:
    process = subprocess.run([
        "forge", "test", "--match-contract", "VerifierOptimizationGasTest", "-vv",
    ], cwd=HERE / "solidity", check=True, text=True, capture_output=True)
    transcript = process.stdout + process.stderr
    values = {name: int(value) for name, value in re.findall(r"([A-Z][A-Za-z0-9.]+):\s*([0-9]+)", transcript)}
    required = {"V1.materializedGas", "V1.streamedGas", "V2.exponentiationGas", "V2.checkedWitnessGas", "V8.unpack31Gas", "COMMON.runtimeBytes"}
    missing = required - values.keys()
    if missing:
        raise RuntimeError(f"Foundry output omitted required measurements: {sorted(missing)}")
    return values, transcript


def calldata_models(execution: int, total_bytes: int, zero_bytes: int) -> dict:
    nonzero = total_bytes - zero_bytes
    tokens = zero_bytes + 4 * nonzero
    standard = 21000 + 4 * tokens + execution
    active_floor = 21000 + 10 * tokens
    return {
        "active": max(standard, active_floor),
        "activeFloorOnly": active_floor,
        "uniform64": max(standard, 21000 + 64 * total_bytes),
        "uniform96": max(standard, 21000 + 96 * total_bytes),
        "standard": standard,
    }


def split_model() -> list[dict]:
    # Query-dependent component is the explicitly named historic component
    # profile (input-MMCS + DEEP-X + FRI), distributed over 32 positions.
    # Fixed terms are solved against the source-bound canonical run, so 16/16
    # reproduces its exact pool A/B execution rather than the historic fixture.
    query_total = 1_751_463 + 2_483_581 + 2_523_737
    per_query = query_total / 32
    air = 2_863_647
    fixed_a = BASELINE["executionGas"]["partA"] - 16 * per_query - air
    fixed_b = BASELINE["executionGas"]["partB"] - 16 * per_query
    rows = []
    for a in (8, 10, 12, 13, 14, 15, 16):
        b = 32 - a
        for placement in ("A", "B"):
            ea = round(fixed_a + a * per_query + (air if placement == "A" else 0))
            eb = round(fixed_b + b * per_query + (air if placement == "B" else 0))
            # Proof bytes are linearly allocated only for sensitivity; shared 9,208 B
            # remains in both calls. It is a projection, not a codec measurement.
            pa = round(9208 + (BASELINE["proofBytes"]["partA"] - 9208) * a / 16)
            pb = round(9208 + (BASELINE["proofBytes"]["partB"] - 9208) * b / 16)
            abi_a = BASELINE["abiBytes"]["partA"] + pa - BASELINE["proofBytes"]["partA"]
            abi_b = BASELINE["abiBytes"]["partB"] + pb - BASELINE["proofBytes"]["partB"]
            zero_a = round(BASELINE["zeroBytes"]["partA"] * abi_a / BASELINE["abiBytes"]["partA"])
            zero_b = round(BASELINE["zeroBytes"]["partB"] * abi_b / BASELINE["abiBytes"]["partB"])
            scenarios_a = calldata_models(ea, abi_a, zero_a)
            scenarios_b = calldata_models(eb, abi_b, zero_b)
            rows.append({"split": [a, b], "airPlacement": placement, "executionGas": [ea, eb], "projectedProofBytes": [pa, pb], "projectedAbiBytes": [abi_a, abi_b], "totalGas": {k: [scenarios_a[k], scenarios_b[k]] for k in ("active", "uniform64", "uniform96")}, "minimumMarginActive": 16_777_216 - max(scenarios_a["active"], scenarios_b["active"])})
    return rows


def exact_tables(native: dict | None) -> dict:
    worst = 256 if native is None else native["measurements"]["V7"]["exactWorstCaseFrontierDigests"]
    caps = []
    for cap_height in (0, 1, 2, 3, 4):
        # For q=32 and heights below log2(q), the exact adversarial placement
        # retains all 256 authentication digests below the cap. A transmitted
        # cap therefore adds 2**h digests; it does not erase 32 digests/level.
        digest_count = worst if cap_height == 0 else worst + (1 << cap_height)
        caps.append({"capHeight": cap_height, "worstCaseDigestCountModel": digest_count, "bytes512": digest_count * 64})
    return {"treeDepth": 13, "queries": 32, "exactWorstCaseFrontierDigests": worst, "widths": [
        {"bits": 512, "bytes": worst * 64, "decision": "ELIGIBLE"},
        {"bits": 384, "bytes": worst * 48, "decision": "REJECT_NO_EXTERNAL_REVIEW"},
        {"bits": 320, "bytes": worst * 40, "decision": "REJECT_NO_EXTERNAL_REVIEW"},
        {"bits": 256, "bytes": worst * 32, "decision": "LOWER_BOUND_ONLY_NOT_ACCEPTABLE"},
    ], "caps": caps}


def logical_kernel_counts(cid: str) -> dict:
    return {
        "V1": {"baseline": {"mulmod": 511, "addmod": 256, "memoryWords": 256}, "streamed": {"mulmod": 512, "addmod": 256, "memoryWords": 0}, "horner": {"mulmod": 256, "addmod": 256, "memoryWords": 0}},
        "V2": {"perInverseBaseline": {"mulmod": 61}, "perCheckedWitness": {"mulmod": 1, "canonicalChecks": 1, "nonzeroGuards": 1}},
        "V3": {"baseline": {"canonicalLoads": 256, "mulmod": 256, "scratchWords": 256}, "fused": {"canonicalLoads": 256, "mulmod": 256, "scratchWords": 0}},
        "V4": {"baseline": {"calldataWordsCopied": 256, "scratchWords": 256}, "calldataNative": {"calldataWordsCopied": 0, "scratchWords": 0, "boundChecksBeforeLoop": 1}},
        "V5": {"fixed": {"codeTableBytes": 128, "tableLoads": 32}, "derived": {"mulmod": 32}, "checkedCalldata": {"mulmod": 31, "calldataFields": 32}},
        "V6": {"exponentiation": {"powCalls": 32}, "incremental": {"powCalls": 1, "mulmod": 32}, "checkedPoints": {"powCalls": 1, "mulmod": 31, "calldataFields": 32}},
        "V7": {"currentAndExactWorstCase": {"frontierDigests": 256}, "hashCallsDependOnFixture": None},
        "V8": {"u32": {"inputBitsPerField": 32}, "packed31": {"inputBitsPerField": 31, "canonicalChecksPerField": 1, "terminalPaddingChecks": 1}},
        "V9": {"querySplitsEvaluated": 7, "airPlacementsPerSplit": 2, "completeOpcodeTrace": None},
    }[cid]


def isolated_floor_delta(cid: str, solidity: dict | None) -> dict | None:
    if solidity is None:
        return None
    keys = {
        "V1": ("materializedGas", "hornerGas", 1024, 1024),
        "V2": ("exponentiationGas", "checkedWitnessGas", 4, 8),
        "V3": ("separateParseDotGas", "fusedParseDotGas", 1024, 1024),
        "V4": ("copiedEvaluationGas", "calldataEvaluationGas", 1024, 1024),
        "V5": ("fixedTableGas", "derivedTableGas", 0, 0),
        "V6": ("exponentiationGas", "incrementalGas", 0, 0),
        "V8": ("unpack32Gas", "unpack31Gas", 1024, 992),
    }
    if cid not in keys:
        return None
    before_key, after_key, before_bytes, after_bytes = keys[cid]
    prefix = cid + "."
    before_gas = solidity[prefix + before_key]
    after_gas = solidity[prefix + after_key]
    before = calldata_models(before_gas, before_bytes, 0)
    after = calldata_models(after_gas, after_bytes, 0)
    return {
        "scope": "isolated kernel with compact-section bytes; not a verifier transaction",
        "executionGasDelta": after_gas - before_gas,
        "calldataBytesDelta": after_bytes - before_bytes,
        "totalGasDelta": {k: after[k] - before[k] for k in ("active", "uniform64", "uniform96")},
    }


def native_kernel_delta(cid: str, native_row: dict | None) -> dict | None:
    if native_row is None:
        return None
    keys = {
        "V1": ("materializedNs", "hornerNs"),
        "V2": ("exponentiationNs", "checkedWitnessNs"),
        "V3": ("separateParseDotNs", "fusedParseDotNs"),
        "V4": ("copyEvaluateNs", "sliceEvaluateNs"),
        "V5": ("fixedReadNs", "derivedNs"),
        "V6": ("exponentiationNs", "incrementalNs"),
        "V8": ("u32ReadNs", "pack31Ns"),
    }
    if cid not in keys:
        return None
    before, after = keys[cid]
    return {"classification": "DIAGNOSTIC_NOT_COMMON_PROTOCOL", "scope": "native isolated aggregate kernel timing; no warmup or distribution", "nanosecondsDelta": native_row[after] - native_row[before], "baselineKey": before, "candidateKey": after}


def candidate_measurement(cid: str, native: dict | None, solidity: dict | None) -> dict:
    n = None if native is None else native["measurements"][cid]
    s = None if solidity is None else {k.split(".", 1)[1]: v for k, v in solidity.items() if k.startswith(cid + ".")}
    base_active = {part: calldata_models(BASELINE["executionGas"][part], BASELINE["abiBytes"][part], BASELINE["zeroBytes"][part]) for part in ("partA", "partB")}
    result = {
        "schema": "pqtc-sp31-candidate-output-v1", "candidateId": cid,
        "measurementScope": "isolated Solidity gas is measured; Rust aggregate timing is diagnostic, not common-protocol evidence",
        "nativeMeasured": None, "nativeDiagnostic": n, "nativeDiagnosticClassification": "DIAGNOSTIC_NOT_COMMON_PROTOCOL" if n is not None else "NOT_EVALUATED", "solidityMeasured": s,
        "baselineCompleteTransaction": BASELINE,
        "completeTransactionMeasured": None,
        "completeTransactionProjected": None,
        "opcodeCounts": {"evmDynamicBaseline": None, "evmDynamicCandidate": None, "status": "NOT_EVALUATED: canonical full-transaction opcode trace unavailable", "logicalKernelCounts": logical_kernel_counts(cid)},
        "active64And96Baseline": {p: {k: v[k] for k in ("active", "uniform64", "uniform96")} for p, v in base_active.items()},
        "isolatedActive64And96Delta": isolated_floor_delta(cid, solidity),
        "calldataDeltaBytes": 0, "runtimeByteDelta": {"value": None, "status": "NOT_ATTRIBUTABLE: shared experiment contract"}, "proofByteDelta": 0,
        "deploymentGasDelta": {"value": None, "status": "NOT_ATTRIBUTABLE: shared experiment contract"}, "proverDelta": {"nanoseconds": 0, "kind": "projected verifier-only change"}, "nativeVerifierDelta": native_kernel_delta(cid, n),
        "differentialTests": {"rustDiagnosticAssertions": 9 if native is not None else 0, "solidityUnsafeCases": 0 if solidity is None else {"V2": 3, "V7": 2, "V8": 4}.get(cid, 1)},
        "noMicrobenchmarkSumClaim": True,
    }
    if cid == "V2":
        result.update({
            "calldataDeltaBytes": {"perBaseInverse": 4, "perExtensionInverse": 16, "fullProof": None},
            "proofByteDelta": {"perBaseInverse": 4, "perExtensionInverse": 16, "fullProof": None},
            "proverDelta": {"nanoseconds": None, "extraWork": "serialize witnesses; compute only inverses not already available"},
            "uniformFloorDeltaPerBaseInverse": {"64": 256, "96": 384},
            "legalityMatrix": [
                {"leg": "DEEP denominators", "eligible": True, "guard": "zeta is checked outside every evaluation domain"},
                {"leg": "batch inversion, all-nonzero", "eligible": True, "guard": "check every denominator before accepting products"},
                {"leg": "batch inversion, zero legal", "eligible": False, "guard": "retain zero-aware native algorithm"},
                {"leg": "FRI fold points", "eligible": True, "guard": "derived nonzero two-adic point and canonical witness"},
                {"leg": "selector denominators on-domain", "eligible": False, "guard": "zero is legal at the selected row"},
                {"leg": "selector denominators out-of-domain", "eligible": True, "guard": "explicit domain exclusion"},
                {"leg": "quotient recomposition", "eligible": True, "guard": "zeta^n != 1 checked independently"},
            ],
        })
    elif cid == "V5": result.update({"calldataDeltaBytes": {"fixed": 0, "derived": 0, "checkedCalldata32": 128}, "proofByteDelta": {"fixed": 0, "derived": 0, "checkedCalldata32": 128}, "proverDelta": {"fixed": 0, "derived": 0, "checkedCalldata": "serialize 32 canonical fields"}})
    elif cid == "V6": result.update({"calldataDeltaBytes": {"exponentiation": 0, "incremental": 0, "checkedPoints32": 128, "fixedTable": 0}, "proofByteDelta": {"exponentiation": 0, "incremental": 0, "checkedPoints32": 128, "fixedTable": 0}, "proverDelta": {"exponentiation": 0, "incremental": 0, "checkedPoints": "serialize 32 canonical fields", "fixedTable": 0}})
    elif cid == "V7": result.update({"frontierAndWidth": exact_tables(native), "proofByteDelta": "variant-specific worst-case table; full proof unavailable", "calldataDeltaBytes": "same as variant-specific frontier proof-byte delta", "proverDelta": {"nanoseconds": None, "hashAndSerializationCounts": "variant-specific"}, "uniformFloorDeltaFrom512WorstCase": {"384": {"bytes": -4096, "gas64": -262144, "gas96": -393216}, "320": {"bytes": -6144, "gas64": -393216, "gas96": -589824}, "256LowerBound": {"bytes": -8192, "gas64": -524288, "gas96": -786432}}})
    elif cid == "V8": result.update({"calldataDeltaBytes": {"per256CanonicalFields": -32, "u32Bytes": 1024, "packed31Bytes": 992, "framedSectionBytes": 996, "derivedOnlySectionBytes": 4, "oneTransactionDuplicateGlobalProjection": -9208}, "codecComparisons": {"u32": 1024, "packed31": 992, "lengthPrefixedPacked31": 996, "derivedOmissionWhenAll256ValuesArePriorTranscriptFunctions": 4, "removeSecondGlobalCopyOnlyInOneTransactionModel": -9208}, "proofByteDelta": {"per256CanonicalFields": -32, "fullProof": None}, "proverDelta": {"classification": "DIAGNOSTIC_NOT_COMMON_PROTOCOL", "scope": "isolated pack256 aggregate timing; no warmup or distribution", "nanosecondsTotal": None if n is None else n["pack31Ns"]}, "uniformFloorDeltaPer256Fields": {"64": -2048, "96": -3072}})
    elif cid == "V9": result["completeTransactionProjected"] = {"kind": "component-model projection, not measurement", "rows": split_model()}
    return result


def canonical_fixture_observation() -> dict:
    proof_root = HERE.parent / "v03-baseline" / "proofs"
    fixtures = sorted(p for p in proof_root.glob("v03-fixed-*") if p.is_dir())
    if not fixtures:
        return {"status": "UNAVAILABLE", "searched": str(proof_root.relative_to(ROOT))}
    fixture = fixtures[0]
    names = ("part-a.pqtc", "part-b.pqtc", "part-a.calldata", "part-b.calldata")
    if any(not (fixture / name).is_file() for name in names):
        return {"status": "INCOMPLETE", "path": str(fixture.relative_to(ROOT))}
    records = {}
    for name in names:
        data = (fixture / name).read_bytes()
        records[name] = {"bytes": len(data), "zeroBytes": data.count(0), "sha256": hashlib.sha256(data).hexdigest()}
    return {"status": "OBSERVED_BASELINE_ONLY", "path": str(fixture.relative_to(ROOT)), "artifacts": records, "optimizedFullPath": "UNAVAILABLE: isolated kernels are not integrated into custody verifier"}


def inheritance_matrix(cid: str) -> dict:
    inherited = {
        "noteEncoding": "Frozen pqtc-note-v3 note encoding is byte-for-byte unchanged.",
        "applicationDigest": "Frozen P2BB512-v1 application digest, typed domains, and 64-byte output are unchanged.",
        "applicationMode": "Frozen width-16 rate-4 capacity-12 Poseidon2 application sponge mode is unchanged.",
        "tree": "Frozen binary depth-20 application Merkle tree and root representation are unchanged.",
        "publicStatement": "Frozen four-Digest512 withdrawal statement and 64 canonical BabyBear public values are unchanged.",
        "relation": "Frozen 256-row, 190-column, 1,186-constraint withdrawal AIR is unchanged.",
        "baseField": "Frozen BabyBear modulus and canonical field semantics are unchanged.",
        "challengeField": "Frozen degree-4 BabyBear extension and coefficient ordering are unchanged.",
        "pcs": "Frozen hiding two-adic FRI q32 profile, blowup, rounds, and grinding are unchanged.",
        "hiding": "Frozen random codewords, MMCS salts, and fresh prover randomness are unchanged.",
        "mmcs": "Frozen binary pruned MMCS with full 512-bit digests remains the compatibility baseline.",
        "transcript": "Frozen KeccakPair512 transcript order, domains, and challenges are unchanged.",
        "proofCodec": "Frozen canonical Part A/B proof codec remains the compatibility baseline.",
        "evmVerifier": "Frozen custody verifier is untouched; only an isolated research kernel is modified.",
        "checkpointModel": "Frozen consumer-bound A/B checkpoint state and replay rules are unchanged.",
        "deploymentManifest": "Frozen parameter/deployment manifest remains authoritative; no candidate deployment artifact is proposed.",
    }
    matrix = {key: {"disposition": "INHERITED", "compatibility": value} for key, value in inherited.items()}
    changes = {
        "V1": {"evmVerifier": ("MODIFIED", "Alpha accumulation implementation changes only; Horner is compatible only where frozen coefficient order permits exact differential equality.")},
        "V2": {
            "proofCodec": ("MODIFIED", "Eligible nonzero inverse witnesses add canonical fields and require a new versioned section; zero-legal legs retain the frozen encoding."),
            "evmVerifier": ("MODIFIED", "Exponentiation may be replaced by witness multiplication only behind verifier-owned nonzero-leg guards."),
        },
        "V3": {"evmVerifier": ("MODIFIED", "Parsing and dot product are fused while preserving frozen big-endian u32 canonical rejection and field order.")},
        "V4": {"evmVerifier": ("MODIFIED", "Evaluation consumes bounded calldata directly instead of copying arrays; public proof bytes remain compatible.")},
        "V5": {
            "proofCodec": ("MODIFIED", "Fixed and derived variants preserve the codec; the checked-calldata table variant adds a versioned canonical table section."),
            "evmVerifier": ("MODIFIED", "Constant lookup changes among code-embedded, derived, and recurrence-checked calldata strategies."),
        },
        "V6": {
            "proofCodec": ("MODIFIED", "Exponentiation/incremental/fixed variants preserve bytes; checked supplied points require a versioned canonical section."),
            "evmVerifier": ("MODIFIED", "Query-point computation strategy changes but every point remains bound to the frozen transcript challenge."),
        },
        "V7": {
            "mmcs": ("REPLACED", "Exact 512-bit frontier counting is compatible; cap and digest-width variants change commitment/verification semantics and require a new reviewed parameter set. 384/320/256 are not accepted."),
            "proofCodec": ("REPLACED", "Cap/frontier/digest-width variants require distinct bounded sections and are not byte-compatible with frozen Part A/B."),
            "evmVerifier": ("MODIFIED", "Exact frontier validation and variant-specific cap traversal replace only the isolated MMCS verification kernel."),
        },
        "V8": {
            "proofCodec": ("REPLACED", "Length-framed canonical 31-bit sections and derived-value omission are uniquely decodable but not byte-compatible with frozen 32-bit sections."),
            "evmVerifier": ("MODIFIED", "The parser adds bounded 31-bit decoding, canonical rejection, and terminal zero-padding enforcement."),
            "checkpointModel": ("MODIFIED", "Removing duplicated globals applies only to a one-transaction model; frozen A/B checkpoints retain both bindings."),
        },
        "V9": {
            "proofCodec": ("MODIFIED", "Query bundles are repartitioned across A/B while total q32 content and canonical per-query encoding remain unchanged."),
            "evmVerifier": ("MODIFIED", "Part boundaries and AIR-segment placement change; the custody verifier is not integrated."),
            "checkpointModel": ("MODIFIED", "Checkpoint position/count fields must bind the selected versioned asymmetric split; frozen 16/16 remains the control."),
        },
    }
    for key, (disposition, compatibility) in changes[cid].items():
        matrix[key] = {"disposition": disposition, "compatibility": compatibility}
    return matrix


def write_candidate(cid: str, native: dict | None, solidity: dict | None) -> None:
    title, assumption = CANDIDATES[cid]
    directory = HERE.parent / cid
    output = candidate_measurement(cid, native, solidity)
    solidity_measured = solidity is not None
    manifest = {
        "candidateId": cid, "spikeId": "SP-31", "title": title, "status": "BENCHMARK_ONLY",
        "baseline": "source-bound C00/v03-baseline run research/runs/v03-fixed-01.json at 00f829001999ee66da6fd5161c4c205c07d0b937",
        "plonky3Commit": "3152b14a89067c83775a8076cc262ffc48a1fd7c",
        "inheritanceMatrix": inheritance_matrix(cid),
        "canonicalFixture": canonical_fixture_observation(),
        "researchOnly": True, "custodyIntegration": "PROHIBITED", "publicNetwork": "PROHIBITED",
        "measurementState": "ISOLATED_SOLIDITY_MEASURED_RUST_DIAGNOSTIC_NOT_COMMON_PROTOCOL" if solidity_measured else "NOT_EVALUATED",
        "completeTransactionState": "NOT_EVALUATED: no isolated full-verifier variant; microbenchmark deltas are not summed",
        "gate": "Keep only after >=2% full-verifier saving, security-risk removal, or material worst-case byte reduction.",
        "sharedImplementation": "../verifier-optimization-common",
    }
    status = {
        "candidateId": cid, "status": "BENCHMARK_ONLY",
        "isolatedRust": "DIAGNOSTIC_NOT_COMMON_PROTOCOL" if native is not None else "NOT_EVALUATED",
        "isolatedSolidity": "PASS" if solidity_measured else "NOT_EVALUATED",
        "fullPath": "NOT_EVALUATED", "gateDecision": "PENDING_FULL_PATH",
        "reason": "No isolated full-verifier variant exists; baseline canonical evidence is observed, Solidity gas is isolated measured evidence, and Rust aggregate timings are diagnostic only.",
        "unsafeCases": "PASS" if solidity_measured and cid in ("V2", "V7", "V8") else "SOURCE_PRESENT_NOT_RUN" if cid in ("V2", "V7", "V8") else "NOT_APPLICABLE",
    }
    assumptions = {"candidateId": cid, "inherited": ["Frozen v0.3 relation, q32 profile, transcript, BabyBear modulus, two-call semantics, and 512-bit proof digests remain unchanged unless the inheritance matrix explicitly marks a layer modified or replaced."], "new": [assumption], "forbidden": ["custody integration", "public RPC", ".env or live keys", "classical wrapper", "modular reduction of encoded fields", "claiming isolated kernel sums as complete-transaction gas"]}
    dump(directory / "manifest.json", manifest)
    dump(directory / "status.json", status)
    dump(directory / "assumptions.json", assumptions)
    (directory / "assumptions.md").write_text(
        f"# {cid} assumptions\n\n"
        f"- Inherited: {assumptions['inherited'][0]}\n"
        f"- New: {assumption}\n"
        "- Encoded BabyBear fields are canonical big-endian u32 or the explicitly framed little-endian 31-bit stream; neither form reduces out-of-range values.\n"
        "- Full-transaction gas, runtime attribution, proof/prover delta, and dynamic opcode counts remain unmeasured until a canonical full verifier variant exists.\n"
        "- Rust `bench()` totals have no warmup or distribution and are DIAGNOSTIC_NOT_COMMON_PROTOCOL; only isolated Solidity gas is classified as measured.\n"
        "- No isolated microbenchmark delta is added to another to claim complete-verifier savings.\n"
    )
    dump(directory / "negative-results.json", {"candidateId": cid, "cases": NEGATIVE[cid]})
    dump(directory / "outputs" / "benchmark.json", output)
    sources = [HERE / "Cargo.toml", HERE / "src/main.rs", HERE / "solidity/foundry.toml", HERE / "solidity/src/VerifierOptimizationBench.sol", HERE / "solidity/test/VerifierOptimization.t.sol", HERE / "run-focused.py"]
    dump(directory / "source-hashes.json", {"algorithm": "sha256", "files": {str(p.relative_to(ROOT)): sha256(p) for p in sources}})
    decision = "PENDING: remain BENCHMARK_ONLY until a canonical full-path replay establishes a gate."
    (directory / "ADR.md").write_text(f"# {cid}: {title}\n\n## Status\n\n{decision}\n\n## Context\n\nSP-31 requires this optimization in isolation and in a non-additive combined package against the frozen v0.3 baseline. Projections are anchored to the source-bound canonical v03-fixed-01 run; the historic report fixture is retained only as a named comparator. The kernels are not integrated into a full verifier, so their measurements cannot be relabeled as transaction measurements.\n\n## Decision\n\nUse the shared Rust/Solidity kernels and fail-closed driver. Preserve canonical encodings and protocol ordering. {assumption}\n\n## Gate\n\nKeep only with at least 2% measured complete-verifier savings, removal of a known security risk, or material measured worst-case proof-byte reduction. Small V3+V4 work may be grouped only as a simplifying combination. No custody code is changed.\n")


def write_combined(native: dict | None, solidity: dict | None, transcript_hash: str | None) -> None:
    solidity_measured = solidity is not None
    outputs = {cid: candidate_measurement(cid, native, solidity) for cid in CANDIDATES}
    report = {
        "schema": "pqtc-sp31-combined-report-v1", "status": "BENCHMARK_ONLY",
        "measured": {"scope": "isolated Solidity gas kernels only", "available": solidity_measured, "solidity": solidity, "forgeTranscriptSha256": transcript_hash},
        "nativeDiagnostic": {"scope": "isolated Rust aggregate timing without warmup or distribution", "classification": "DIAGNOSTIC_NOT_COMMON_PROTOCOL", "commonProtocolComparable": False, "available": native is not None, "values": native},
        "canonicalFixture": canonical_fixture_observation(),
        "baseline": {"projectionAnchor": BASELINE, "historicComparator": HISTORIC_BASELINE},
        "projected": {"scope": "source-bound canonical run plus explicitly named historic component model; calldata-floor values recomputed from exact current bytes", "querySplits": split_model(), "mmcs": exact_tables(native)},
        "completeTransaction": {"measured": None, "reason": "canonical baseline is observed, but no optimized full-verifier path exists", "combinedSavings": None, "reasonCombined": "isolated microbenchmarks overlap and are deliberately not summed"},
        "candidateOutputs": outputs,
        "simplifyingCombinations": [{"members": ["V3", "V4"], "reason": "one bounded calldata-consumption loop removes both the parse pass and memory copy without introducing another abstraction"}],
        "gatePolicy": ">=2% measured full verifier saving, security-risk removal, or material measured worst-case byte reduction",
    }
    dump(HERE / "outputs" / "combined.json", report)
    dump(HERE / "outputs" / "baseline-reference.json", {"projectionAnchor": BASELINE, "historicComparator": HISTORIC_BASELINE})
    dump(HERE / "status.json", {"status": "BENCHMARK_ONLY", "isolatedSolidityMeasurements": "PASS" if solidity_measured else "NOT_EVALUATED", "isolatedRustTiming": "DIAGNOSTIC_NOT_COMMON_PROTOCOL" if native is not None else "NOT_EVALUATED", "fullPath": "NOT_EVALUATED", "combinedGate": "PENDING_FULL_PATH", "noAdditiveClaim": True})
    dump(HERE / "manifest.json", {"candidateId": "SP-31/V1-V9", "status": "BENCHMARK_ONLY", "command": "python3 research/candidates/verifier-optimization-common/run-focused.py", "paths": list(CANDIDATES), "plonky3Commit": "3152b14a89067c83775a8076cc262ffc48a1fd7c", "custodyIntegration": False})
    (HERE / "ADR.md").write_text(
        "# SP-31 combined verifier optimization package\n\n"
        "## Status\n\nBENCHMARK_ONLY. No custody integration is authorized.\n\n"
        "## Decision\n\nRun V1-V9 from one fail-closed command. Keep measured isolated Solidity gas and diagnostic Rust aggregate timings in separate JSON fields. "
        "The Rust `bench()` loop has no warmup or sample distribution and is not common-protocol-comparable. Do not add overlapping microbenchmarks. "
        "V3+V4 is the only predeclared simplifying combination. A complete-transaction gate remains pending because no isolated optimized full-verifier variant exists; "
        "the source-bound canonical baseline is observed and used for projections.\n"
    )
    (HERE / "assumptions.md").write_text(
        "# SP-31 combined assumptions\n\n"
        "- The projection anchor is the source-bound v03-fixed-01 run and its hash-checked proof/calldata files; historic report values are only a named comparator.\n"
        "- The V9 model allocates the explicitly named historic MMCS, DEEP-X, and FRI component total uniformly over 32 query positions, then solves fixed terms to reproduce the current canonical 16/16 execution values.\n"
        "- The active/64/96 schedules are recomputed from current exact calldata bytes and zero counts; each total is the maximum of the standard path and its floor.\n"
        "- The canonical proof is consumed for baseline bytes, hashes, and gas. No optimized full verifier is integrated, so no full-path savings are claimed.\n"
    )
    dump(HERE / "negative-results.json", {"package": "SP-31", "results": ["Canonical v03-fixed-01 is consumed as the projection anchor, but no optimized full-verifier path exists.", "Dynamic full-verifier opcode counts remain unavailable.", "384/320-bit digest truncation lacks external review.", "No individual candidate has passed the complete-verifier gate.", "Isolated kernel savings are not summed.", "Rust aggregate timings have no warmup or distribution and are DIAGNOSTIC_NOT_COMMON_PROTOCOL."]})


def validate() -> None:
    combined = json.loads((HERE / "outputs/combined.json").read_text())
    assert combined["completeTransaction"]["combinedSavings"] is None
    assert len(combined["projected"]["querySplits"]) == 14
    assert [r["split"] for r in combined["projected"]["querySplits"][::2]] == [[8,24],[10,22],[12,20],[13,19],[14,18],[15,17],[16,16]]
    baseline_rows = [r for r in combined["projected"]["querySplits"] if r["split"] == [16, 16] and r["airPlacement"] == "A"]
    assert len(baseline_rows) == 1
    assert baseline_rows[0]["executionGas"] == [BASELINE["executionGas"]["partA"], BASELINE["executionGas"]["partB"]]
    assert BASELINE["proofBytes"] == {"partA": 108326, "partB": 103878}
    assert BASELINE["totalGas"] == {"partA": 16742112, "partB": 13943756}
    for cid in CANDIDATES:
        directory = HERE.parent / cid
        for name in ("manifest.json", "status.json", "assumptions.json", "assumptions.md", "negative-results.json", "source-hashes.json", "ADR.md", "outputs/benchmark.json"):
            assert (directory / name).is_file(), f"missing {cid}/{name}"
        assert json.loads((directory / "manifest.json").read_text())["status"] == "BENCHMARK_ONLY"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata-only", action="store_true", help="regenerate fail-closed metadata without compiling kernels")
    parser.add_argument("--repetitions", type=int, default=2000)
    args = parser.parse_args()
    if args.repetitions < 1: parser.error("--repetitions must be positive")
    native = solidity = None
    transcript_hash = None
    if not args.metadata_only:
        native = run_native(args.repetitions)
        solidity, transcript = run_solidity()
        transcript_path = HERE / "outputs" / "forge-transcript.txt"
        transcript_path.parent.mkdir(parents=True, exist_ok=True)
        transcript_path.write_text(transcript)
        transcript_hash = sha256(transcript_path)
    for cid in CANDIDATES: write_candidate(cid, native, solidity)
    write_combined(native, solidity, transcript_hash)
    validate()
    print(f"SP-31 focused package: {'isolated measurements complete' if native else 'metadata regenerated; measurements not run'}; full path NOT_EVALUATED")
    return 0

if __name__ == "__main__":
    sys.exit(main())
