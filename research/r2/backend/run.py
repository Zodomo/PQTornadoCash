#!/usr/bin/env python3
"""Run exact-H0 controls and bounded API repairs; Main serializes execution."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parents[2]
ALLOW_ENV = {"PATH", "HOME", "TMPDIR", "TMP", "TEMP", "RUSTUP_HOME", "CARGO_HOME", "RUSTUP_TOOLCHAIN", "RUSTC", "RUSTFLAGS", "SDKROOT", "MACOSX_DEPLOYMENT_TARGET", "CC", "CXX", "AR", "RAYON_NUM_THREADS", "CARGO_BUILD_JOBS"}


def clean_env():
    result = {k: v for k, v in os.environ.items() if k in ALLOW_ENV}
    result.update(CARGO_TARGET_DIR=str(PACKAGE / "target"), CARGO_TERM_COLOR="never", CARGO_NET_OFFLINE="true", PYTHONDONTWRITEBYTECODE="1")
    return result


def dump(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--statement", type=Path, default=ROOT / "research/r2/corpus/h0/fixed/statement.json")
    parser.add_argument("--witness", type=Path, default=ROOT / "research/r2/corpus/h0/fixed/witness.json")
    parser.add_argument("--output", type=Path, default=PACKAGE / "outputs")
    parser.add_argument("--stage", choices=["all", "api", "native", "repair"], default="all")
    parser.add_argument("--security-level", choices=[32, 128], type=int, default=32)
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(PACKAGE):
        parser.error("outputs must remain under research/r2/backend")
    output.mkdir(parents=True, exist_ok=True)
    if (output / "results.json").exists():
        parser.error("refusing to overwrite an existing run; select a new --output")
    env = clean_env()
    commands = []
    manifest = PACKAGE / "rust/Cargo.toml"

    def run(label, argv):
        start = time.time_ns()
        record = {"label": label, "argv": [str(a) for a in argv], "cwd": str(ROOT), "environment_keys": sorted(env)}
        try:
            with (output / f"{label}.stdout.log").open("w") as out, (output / f"{label}.stderr.log").open("w") as err:
                result = subprocess.run(record["argv"], cwd=ROOT, env=env, stdout=out, stderr=err, timeout=args.timeout, check=False)
            record["exit_code"] = result.returncode
        except (OSError, subprocess.TimeoutExpired) as error:
            record.update(exit_code=None, execution_error=str(error))
        record["elapsed_wall_ns"] = time.time_ns() - start
        record["measurement_class"] = "EXECUTION_LOG_NOT_BENCHMARK"
        commands.append(record)
        dump(output / "commands.json", commands)
        return record

    results = {"schema": "pqtc.r2.backend-results.v1", "pipeline_id": "R2-C4",
        "specification_status": "EXACT_H0", "correctness_evidence": "NOT_EVALUATED",
        "privacy_evidence": "HIDING_APPLICATION_NOT_ESTABLISHED", "security_status": "SECURITY_NOT_QUALIFIED",
        "performance_evidence": "NOT_EVALUATED", "implementation_stage": "API_AND_BOUNDED_REPAIR",
        "promotion_status": "NOT_READY_FOR_BUILD_SELECTION", "requested_security_bits": args.security_level,
        "independent_outputs": {}, "api_barriers": {}, "full_evm": "NOT_EVALUATED_NO_COMPLETE_HIDING_NATIVE_PROOF"}
    build = run("build", ["cargo", "build", "--release", "--manifest-path", manifest, "--lib"])
    if build["exit_code"] != 0:
        results.update(implementation_stage="BUILD_BARRIER", correctness_evidence="EXECUTION_BLOCKED")
        dump(output / "results.json", results)
        return 1
    run("dependency-graph", ["cargo", "metadata", "--locked", "--format-version", "1", "--manifest-path", manifest])
    metadata_path = output / "dependency-graph.stdout.log"
    if metadata_path.stat().st_size:
        metadata = json.loads(metadata_path.read_text())
        dump(output / "license-inventory.json", [{"package": p["name"], "version": p["version"], "source": p["source"], "license_declaration": p["license"], "license_file": p["license_file"], "manifest_path": p["manifest_path"], "legal_clearance": "NOT_ASSESSED"} for p in metadata["packages"]])
    shutil.copyfile(PACKAGE / "rust/Cargo.lock", output / "Cargo.lock")
    if args.stage in ("all", "api"):
        for label, trait in [("uni-api-barrier", "Pcs"), ("multi-api-barrier", "PrescribedPointPcs")]:
            record = run(label, ["cargo", "check", "--locked", "--manifest-path", manifest, "--features", label, "--bin", label])
            stderr = (output / f"{label}.stderr.log").read_text()
            demonstrated = record["exit_code"] not in (0, None) and "E0277" in stderr and trait in stderr and "HidingWhirPcs" in stderr
            results["api_barriers"][label] = {"expected_trait": trait, "missing_trait_demonstrated": demonstrated, "status": "CONCRETE_API_BARRIER" if demonstrated else "UNEXPECTED_RESULT_REQUIRES_INSPECTION"}
    if args.stage != "api":
        if not args.statement.is_file() or not args.witness.is_file():
            results["input_error"] = "Run baseline prepare-corpus or pass exact canonical statement/witness paths. No synthetic proxy fallback."
        else:
            for label, binary in [("non-hiding-control", "h0-control"), ("hiding-repair", "hiding-repair")]:
                if (args.stage == "native" and binary != "h0-control") or (args.stage == "repair" and binary != "hiding-repair"):
                    continue
                compiled = run(f"build-{binary}", ["cargo", "build", "--release", "--locked", "--manifest-path", manifest, "--bin", binary])
                if compiled["exit_code"] != 0:
                    results["independent_outputs"][label] = {"status": "BUILD_BARRIER", "exit_code": compiled["exit_code"]}
                    continue
                dest = output / label
                record = run(label, [PACKAGE / "target/release" / binary, args.statement.resolve(), args.witness.resolve(), dest, args.security_level])
                path = dest / "result.json"
                results["independent_outputs"][label] = json.loads(path.read_text()) if path.exists() else {"status": "EXECUTION_BLOCKED", "exit_code": record["exit_code"]}
    if results["independent_outputs"]:
        results["correctness_evidence"] = "SEE_INDEPENDENT_OUTPUTS_NO_HIDING_RELATION_CLAIM"
        results["performance_evidence"] = "SEE_COMPONENT_AND_NON_HIDING_CONTROL_SCOPES"
    hashes = []
    source_paths = list((PACKAGE / "rust/src").glob("*.rs")) + list(PACKAGE.glob("*.py")) + [manifest, PACKAGE / "adapter.json"]
    for path in sorted(source_paths):
        hashes.append({"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    for relative in ["crates/pqtc-poseidon-air/src/air.rs", "crates/pqtc-poseidon-air/src/lib.rs", "crates/pqtc-spec/src/lib.rs"]:
        hashes.append({"path": relative, "sha256": hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()})
    dump(output / "source-hashes.json", hashes)
    dump(output / "artifact-ledger.json", [{"path": str(p.relative_to(output)), "bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(output.rglob("*")) if p.is_file()])
    dump(output / "results.json", results)
    print(output / "results.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
