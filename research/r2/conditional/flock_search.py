#!/usr/bin/env python3
"""Search bounded LOCAL upstream history; stage exact supported source, never invent parameters."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
HISTORICAL = "c2d0c2485a54f7b7694e19f4f59730ffde3405cf"
PINS = [HISTORICAL, "0f0d63268e1373c585251e95152b3a6943e2d818", "43f0eee06d887d87ad25d72614cbc2b17fe91430"]
CONFIG = "crates/flock-core/configs/ligerito/m21_fast.toml"
REGISTRY = "crates/flock-core/src/pcs/ligerito.rs"
BENCH = "crates/flock-prover/benches/keccak3_proof.rs"
GENERATOR = "crates/flock-prover/examples/gen_ligerito_configs.rs"
PINNED_HASHES = {
    BENCH: "965b64f1783814e62afee1a281fbbb33987d86555f3b3f0f5a25f23095f0c616",
    REGISTRY: "1e607b05604c5eb37cd68d9db57a56eb3e44f2e2680f056e4e86e3235494b4a5",
    "crates/flock-prover/src/r1cs_hashes/keccak3.rs": "f3bc3f7cdf477078a135b70b0eeee470d062b5be38bf075e5a59f7efa9dd14bf",
    "crates/flock-prover/src/prover.rs": "b5cf6523e987ae7e0ba23aaf07a3a3c089e3e724a8cec7b5a90a98b9f4641f7b",
}


def git(source, *args, required=True):
    env = {"PATH": os.defpath, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
           "GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0"}
    result = subprocess.run(["/usr/bin/git", "-C", str(source), *args], env=env,
                            capture_output=True, timeout=20)
    if result.returncode and required:
        raise ValueError(result.stderr.decode(errors="replace"))
    return result.stdout if result.returncode == 0 else None


def inspect(source, commit):
    config = git(source, "show", f"{commit}:{CONFIG}", required=False)
    registry = git(source, "show", f"{commit}:{REGISTRY}", required=False)
    bench = git(source, "show", f"{commit}:{BENCH}", required=False)
    text = (registry or b"").decode()
    macros = re.findall(r"profile_configs!\(([^)]*)\)", text)
    registered = any("21" in re.findall(r"\b\d+\b", macro) for macro in macros)
    # This bounded recognizer accepts only the retained registration convention.
    # Other conventions require source review, not a guessed positive match.
    return {"commit": commit, "m21_fast_present": config is not None,
            "retained_registry_convention_includes_m21": registered,
            "keccak_control_present": bench is not None and b"KECCAK3_KS" in bench,
            "supported_source_candidate": bool(config and registered and bench and b"KECCAK3_KS" in bench),
            "config_sha256": hashlib.sha256(config).hexdigest() if config else None,
            "registry_sha256": hashlib.sha256(registry).hexdigest() if registry else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="existing local succinctlabs/flock git checkout; never fetched")
    parser.add_argument("--max-commits", type=int, default=64)
    parser.add_argument("--tip", action="append", default=[], help="explicit full upstream commit (maximum four); no branches or URLs")
    parser.add_argument("--prepare", help="full matching commit, or historical pin for exact failure reproducer")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.max_commits <= 128 or len(args.tip) > 4:
        parser.error("bounded search permits 1..128 commits and at most four explicit tips")
    if any(not re.fullmatch(r"[0-9a-f]{40}", c) for c in args.tip + ([args.prepare] if args.prepare else [])):
        parser.error("commit IDs must be full lowercase 40-hex upstream identities")
    output = args.output.resolve()
    if not output.is_relative_to(HERE):
        parser.error("output must remain under research/r2/conditional")
    source = args.source.resolve()
    rows, missing_pins = [], []
    if source.is_dir():
        for path, expected in PINNED_HASHES.items():
            blob = git(source, "show", f"{HISTORICAL}:{path}")
            if hashlib.sha256(blob).hexdigest() != expected:
                raise ValueError(f"historical upstream source hash mismatch: {path}")
        tips = []
        for pin in args.tip + PINS:
            if git(source, "cat-file", "-e", f"{pin}^{{commit}}", required=False) is None:
                missing_pins.append(pin)
            else:
                tips.append(pin)
        commits = git(source, "rev-list", f"--max-count={args.max_commits}", *tips).decode().splitlines() if tips else []
        # Historical point is mandatory even when newer tips consume the history budget.
        commits = list(dict.fromkeys([HISTORICAL, *commits]))[:args.max_commits]
        rows = [inspect(source, commit) for commit in commits]
    else:
        missing_pins = PINS + args.tip
    prepared = None
    if args.prepare:
        eligible = {r["commit"] for r in rows if r["supported_source_candidate"]}
        if args.prepare != HISTORICAL and args.prepare not in eligible:
            parser.error("prepare requires an observed source-supported config and Keccak control at the SAME commit")
        dest = HERE / "work" / f"flock-{args.prepare}"
        if dest.exists():
            parser.error(f"refusing to overwrite an existing source copy: {dest}")
        archive = git(source, "archive", "--format=tar", args.prepare)
        dest.mkdir(parents=True)
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(dest, filter="data")
        prepared = {"source_commit": args.prepare, "cwd": str(dest),
                    "source_archive_sha256": hashlib.sha256(archive).hexdigest(),
                    "argv": ["cargo", "bench", "--locked", "--offline", "--bench", "keccak3_proof"],
                    "env": {"KECCAK3_KS": "44", "RAYON_NUM_THREADS": "1", "CARGO_NET_OFFLINE": "true"},
                    "execution_status": "NOT_EVALUATED", "expected_barrier": "MISSING_LIGERITO_M21_FAST_SECURITY_CONFIG" if args.prepare == HISTORICAL else None}
    failure_path = ROOT / "research/candidates/C70-flock-veil/outputs/flock-benchmark/stderr.log"
    failure_lines = [line for line in failure_path.read_text().splitlines() if "no security config registered" in line]
    result = {"schema": "pqtc.r2.conditional-flock.v1", "repository": "https://github.com/succinctlabs/flock",
        "pins": PINS, "veil_pin": "6d7ee5c091ad19e957a5faa5869de8739a76aa78",
        "search_scope": "bounded existing local git objects only; not a claim about all upstream history or latest HEAD",
        "max_commits": args.max_commits, "commits_inspected": len(rows), "missing_local_pins": missing_pins,
        "measurement_status": "MEASURED" if rows else "EXECUTION_BLOCKED", "measurement_scope": "source availability only, not prover performance",
        "search_results": rows, "supported_candidates": [r["commit"] for r in rows if r["supported_source_candidate"]],
        "historical_control": {"source_commit": HISTORICAL, "logical_permutations": 44, "capacity_permutations": 48,
            "dummy_permutations": 4, "dummy_semantics": "valid all-zero Keccak computations", "m": 21,
            "profile": "fast", "trial_policy": "retained benchmark best of three; not R2 median methodology",
            "barrier": "MISSING_LIGERITO_M21_FAST_SECURITY_CONFIG", "exact_error": failure_lines,
            "retained_log": str(failure_path.relative_to(ROOT)), "retained_log_sha256": hashlib.sha256(failure_path.read_bytes()).hexdigest(),
            "measurement_status": "EXECUTION_BLOCKED", "architecture_failed": None, "proof_bytes": None, "prover_ms": None},
        "repair_policy": "Only stage an unchanged complete upstream commit with the matching config, registry and Keccak harness. No generated presets, padded m changes, numerical edits, or cross-user witness pooling.",
        "generator_note": f"Historical {GENERATOR} derives only m22..35; widening its range to m21 is NOT approved by this reproducer.",
        "application_entry": {"entered": False, "requires": ["successful exact Keccak control", "exact glue relation", "complete hiding route and measured overhead", "EVM verifier path"],
                              "architecture_failed": None}, "prepared_command": prepared}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(output)


if __name__ == "__main__":
    main()
