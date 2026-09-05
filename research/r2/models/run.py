#!/usr/bin/env python3
"""Predeclare, then execute bounded real proof anchors in fresh serial processes.

Build binaries first (Main owns scheduling):
 cargo build --release --locked --manifest-path research/r2/models/rust/Cargo.toml
 cargo build --release --manifest-path research/r2/air/rust/Cargo.toml
 python3 research/r2/models/run.py --declare --output research/r2/models/outputs/plan.json
 python3 research/r2/models/run.py --plan research/r2/models/outputs/plan.json --relations C0 \
   --c0-binary research/r2/models/rust/target/release/pqtc-r2-model-anchors \
   --input research/r2/corpus/h0/fixed --output research/r2/models/outputs/anchors

--normalized-selections explicitly binds normalized profiles; unresolved slots never run.
No production/testnet signing or network activity is performed by this runner.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

from codec import byte_model, c10_counts, parse_c10, postcard_model
from model import ROOT, dump, evm_work, load, pareto


def declaration():
    return load(Path(__file__).parent/"anchor-plan.json")


def safe_environment():
    # Binaries are prebuilt. No HOME credentials, RPC/key variables, or arbitrary inherited environment.
    allowed = ("PATH", "TMPDIR", "LANG", "LC_ALL", "SYSTEMROOT")
    env = {k: os.environ[k] for k in allowed if k in os.environ}
    env.update(RAYON_NUM_THREADS="1", RUST_BACKTRACE="1")
    return env


def resolve_slots(plan, relation, selections):
    resolved = []
    for base in plan["slots"]:
        slot = {"log_final_poly": 0, "max_log_arity": 1, "cap_height": 0,
                "commit_pow": 16, "query_pow": 16, **base}
        if slot.get("selection_required"):
            aliases = {"no_johnson_condition": "no-Johnson-UDR",
                       "conditional_johnson": "conditional-Johnson-full-objective"}
            found = [s for s in selections if s.get("candidate_id", s.get("candidate", "")).removeprefix("R2-") == relation
                     and s["regime"] in (slot["regime"], aliases[slot["regime"]])]
            if not found:
                slot["blocked_reason"] = "exact reviewed-calculator normalized selection absent"
            else:
                # Predeclared selection rule: smallest q reaching target, then smallest blowup.
                reached = [s for s in found if s.get("target_reached", s.get("status") == "TARGET_MET_CONDITIONALLY")]
                source = min(reached or found, key=lambda s: (s.get("q", s.get("queries")), s["log_blowup"]))
                selection = {**source, "queries": source.get("q", source.get("queries")),
                             "security_model": source.get("model", source.get("security_model")),
                             "target_reached": bool(reached),
                             "source": source.get("source", "explicit --normalized-selections frozen copy")}
                required = ("queries", "log_blowup", "security_model", "target_bits", "achieved_bits", "target_reached", "source")
                if any(selection.get(k) is None for k in required):
                    raise ValueError("normalized selection missing explicit model, target, achieved bits, or source")
                if not selection["target_reached"]:
                    slot["blocked_reason"] = "declared normalization target not reached; retain security result without relabeling fixed control"
                slot.update({k: selection[k] for k in required})
                for k in ("log_final_poly", "max_log_arity", "cap_height", "commit_pow", "query_pow"):
                    if k in selection:
                        slot[k] = selection[k]
        resolved.append(slot)
    return resolved


def command_for(args, relation, slot, out):
    if relation == "C0":
        manifest = load(ROOT/"research/fri-pareto/manifests/b4-q32-c16x16-f0-r4.json")
        manifest.update(profile_id="R2-C0-"+slot["id"], fri_num_queries=slot["queries"], fri_log_blowup=slot["log_blowup"],
                        fri_log_final_poly_len=slot["log_final_poly"], fri_max_log_arity=slot["max_log_arity"],
                        commit_grinding_bits=slot["commit_pow"], query_grinding_bits=slot["query_pow"])
        dump(out/"manifest.json", manifest)
        return [str(args.c0_binary.resolve()), "--manifest", str(out/"manifest.json"), "--input", str(args.input.resolve()),
                "--out", str(out), "--repetitions", "2", "--cap-height", str(slot["cap_height"])]
    command = [str(args.air_binary.resolve()), "--candidate", relation, "--profile", slot["profile"],
               "--queries", str(slot["queries"]), "--log-blowup", str(slot["log_blowup"]),
               "--log-final-poly", str(slot["log_final_poly"]), "--max-log-arity", str(slot["max_log_arity"]),
               "--cap-height", str(slot["cap_height"]), "--commit-pow", str(slot["commit_pow"]),
               "--query-pow", str(slot["query_pow"]), "--output", str(out),
               "--statement", str(args.input.resolve()/"statement.json"),
               "--witness", str(args.input.resolve()/"witness.json")]
    if slot["profile"] == "normalized":
        command += ["--security-model", slot["security_model"]]
    return command


def c0_rows(out, relation, slot):
    result = load(out/"measurements.json")
    rows = []
    for rep in result["repetitions"]:
        if not rep["native_verified"]:
            raise ValueError("native proof verification failed")
        raw = (out/f"proof-{rep['repetition']}.bin").read_bytes()
        ledger = parse_c10(raw)
        geometry = ledger["geometry"]
        shape = {"queries": slot["queries"], "degree_bits": rep["degree_bits"], "log_blowup": slot["log_blowup"],
                 "trace_width": 190, "quotient_chunks": 16, "random_codewords": 4,
                 "cap_height": slot["cap_height"], "final_poly_len": geometry["final_poly_len"],
                 "input_matrix_widths": [b["rows"][0] for b in geometry["inputs"]],
                 "fri_log_arities": [r["log_arity"] for r in geometry["fri_rounds"]]}
        counts = c10_counts(shape, rep["input_frontier_digests"], rep["fri_frontier_digests"])
        predicted = byte_model(counts)
        if counts != ledger["wire_counts"] or predicted["total_bytes"] != rep["research_canonical_raw_bytes"]:
            raise ValueError("independent structural formula does not match parser/native lengths")
        work = evm_work(shape, rep["query_indices"])
        dump(out/f"ledger-{rep['repetition']}.json", ledger)
        rows.append({"id": f"{relation}-{slot['id']}-{rep['repetition']}", "proof_sha256": ledger["proof_sha256"],
                     "proof_bytes": len(raw), "prove_ms": rep["prove_ms"], "native_verify_ms": rep["native_verify_ms"],
                     "peak_rss_bytes": rep["process_peak_rss_bytes"] or None, "features": work["features"],
                     "shape": shape, "structural_bytes_residual": len(raw)-predicted["total_bytes"],
                     "codec": "PQTCC10R1", "implementation_id": "r2-c0-anchor-fork",
                     "complete_native_verified": True, "narrow_relation": False})
    return rows


def air_rows(out, relation, slot, repetition):
    result = load(out/"results.json")
    if result["native_verified"] is not True:
        raise ValueError("native AIR proof verification failed")
    raw = (out/result["proof_path"]).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if len(raw) != result["raw_proof_bytes"]:
        raise ValueError("AIR proof length mismatch")
    shape = load(out/result["shape_path"])
    ledger = load(out/result["byte_ledger_path"])
    structural = postcard_model(raw, ledger, load(out/"proof.json"))
    dump(out/"structural-byte-model.json", structural)
    return [{"id": f"{relation}-{slot['id']}-{repetition}", "proof_sha256": digest,
             "proof_bytes": len(raw), "prove_ms": result["prove_ms"], "native_verify_ms": result["verify_ms"],
             "shape": shape, "actual_ledger": ledger, "features": result.get("evm_work_features"),
             "codec": "postcard", "implementation_id": "r2-air",
             "complete_native_verified": True, "narrow_relation": relation in ("C1", "C3"),
             "structural_bytes_residual": structural["structural_bytes_residual"],
             "structural_model_status": "MEASURED: value-dependent postcard widths, not canonical-v3 lengths"}]


def execute(args):
    plan = load(args.plan)
    if plan["schema"] != "pqtc.r2.models.anchor-plan.v1" or len(plan["slots"]) > 12:
        raise ValueError("bounded predeclared plan required")
    selections = load(args.normalized_selections) if args.normalized_selections else []
    output = args.output.resolve()
    if output.exists():
        raise ValueError("fresh output directory required; never overwrite or resample previous rows")
    output.mkdir(parents=True)
    dump(output/"frozen-plan.json", plan)
    dump(output/"normalized-selections.json", selections)
    rows, records, identities = [], [], set()
    environment = safe_environment()
    binaries = [p for p in (args.c0_binary, args.air_binary) if p and p.is_file()]
    binary_hashes = {str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest() for p in binaries}
    dump(output/"source-epoch.json", {
        "binaries": binary_hashes,
        "sources": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in [Path(__file__).resolve(), Path(__file__).with_name("codec.py"), Path(__file__).with_name("model.py")]},
        "input": {name: hashlib.sha256((args.input/name).read_bytes()).hexdigest() for name in ("statement.json", "witness.json")}})
    # A single advisory lock shared by every invocation of this package enforces serial process timing.
    with (Path(__file__).parent/".anchor.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for relation in args.relations.split(","):
            if relation not in plan["relations"]:
                raise ValueError("relation absent from frozen plan")
            seen_configs = {}
            for slot in resolve_slots(plan, relation, selections):
                if args.anchor and slot["id"] not in args.anchor:
                    continue
                if slot.get("blocked_reason"):
                    records.append({"relation": relation, "slot": slot, "measurement_status": "EXECUTION_BLOCKED", "reason": slot["blocked_reason"]})
                    continue
                key = tuple(slot[k] for k in ("queries", "log_blowup", "log_final_poly", "max_log_arity", "cap_height", "commit_pow", "query_pow"))
                if key in seen_configs:
                    records.append({"relation": relation, "slot": slot, "alias_of": seen_configs[key],
                                    "measurement_status": "NOT_EVALUATED", "reason": "same protocol configuration; not a new sample"})
                    continue
                seen_configs[key] = slot["id"]
                for rep in range(1 if relation == "C0" else 2):
                    out = output/relation/slot["id"]/str(rep)
                    out.mkdir(parents=True)
                    command = command_for(args, relation, slot, out)
                    started = time.perf_counter()
                    try:
                        proc = subprocess.run(command, cwd=ROOT, env=environment, text=True, capture_output=True, timeout=args.timeout)
                        record = {"command": command, "cwd": str(ROOT), "exit_status": proc.returncode,
                                  "binary_sha256": binary_hashes[command[0]],
                                  "stdout": proc.stdout, "stderr": proc.stderr,
                                  "serial_process_wall_ms": (time.perf_counter()-started)*1000,
                                  "environment": environment, "timing_scope": "whole prebuilt process, not native proof-only interval"}
                    except subprocess.TimeoutExpired as error:
                        record = {"command": command, "exit_status": None, "measurement_status": "EXECUTION_BLOCKED",
                                  "stop_reason_class": "resource/budget limit", "timeout_seconds": args.timeout,
                                  "stdout": (error.stdout or b"").decode(errors="replace") if isinstance(error.stdout, bytes) else error.stdout,
                                  "stderr": (error.stderr or b"").decode(errors="replace") if isinstance(error.stderr, bytes) else error.stderr}
                        dump(out/"command.json", record)
                        records.append({"relation": relation, "slot": slot, **record})
                        break
                    dump(out/"command.json", record)
                    if proc.returncode:
                        records.append({"relation": relation, "slot": slot, "measurement_status": "EXECUTION_BLOCKED", **record})
                        break
                    fresh = c0_rows(out, relation, slot) if relation == "C0" else air_rows(out, relation, slot, rep)
                    for row in fresh:
                        if row["proof_sha256"] in identities:
                            raise ValueError("duplicate proof identity; entropy/sample independence gate failed")
                        identities.add(row["proof_sha256"])
                        row.update(relation=relation, profile_id=slot["id"], regime=slot["regime"], split=slot["split"],
                                   measurement_status="MEASURED", metric_scope="native_proof", historical=False,
                                   complete_transaction_gas=None, evm_execution_gas=None,
                                   physical_feasibility="UNKNOWN", qualification="NOT_QUALIFIED")
                        rows.append(row)
                    records.append({"relation": relation, "slot": slot, "measurement_status": "MEASURED", "command_record": str(out/"command.json")})
                    dump(output/"samples.json", rows)
                    dump(output/"records.json", records)
    dump(output/"samples.json", rows)
    dump(output/"records.json", records)
    dump(output/"pareto-measured-native.json", pareto(rows, ["proof_bytes", "prove_ms"]))
    print(json.dumps({"samples": len(rows), "records": len(records), "output": str(output), "complete_transaction_gas": None}))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--declare", action="store_true")
    p.add_argument("--plan", type=Path)
    p.add_argument("--normalized-selections", type=Path)
    p.add_argument("--relations", default="C0,C1,C2,C3")
    p.add_argument("--anchor", action="append")
    p.add_argument("--input", type=Path, default=ROOT/"research/r2/corpus/h0/fixed")
    p.add_argument("--c0-binary", type=Path, default=Path(__file__).parent/"rust/target/release/pqtc-r2-model-anchors")
    p.add_argument("--air-binary", type=Path)
    p.add_argument("--timeout", type=int, default=1800)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.declare:
        dump(args.output, declaration())
    else:
        if not args.plan or (any(c != "C0" for c in args.relations.split(",")) and not args.air_binary):
            p.error("--plan and applicable prebuilt binaries required")
        execute(args)


if __name__ == "__main__":
    main()
