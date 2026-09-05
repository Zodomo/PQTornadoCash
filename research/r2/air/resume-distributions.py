#!/usr/bin/env python3
"""Serial independent proofs; warmup is machine/cache warming, not reused prover state."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time

sys.dont_write_bytecode = True
from run import ROOT, ALLOWED


def identity(path):
    path = Path(path).resolve()
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--samples", type=int, default=30)
    ap.add_argument("--warmup", type=int, default=2)
    args = ap.parse_args()
    if args.samples < 30 or args.samples > 256 or args.warmup < 1:
        ap.error("require 30..256 distinct varied cases and at least one separate warmup per mode/config")
    out = args.output.resolve()
    if not any(p.startswith("resume-") for p in out.parts):
        ap.error("new outputs must be under resume-*")
    manifest = json.loads(args.manifest.read_text())
    configs = manifest["configurations"]
    names = [c["name"] for c in configs]
    if not names or len(set(names)) != len(names) or any(Path(n).name != n or n in (".", "..") for n in names):
        ap.error("require unique safe configuration names")
    for cfg in configs:
        required = ("{output}", "{input}") if any("{input}" in arg for arg in cfg["command"]) else ("{output}", "{statement}", "{witness}", "{case_index}")
        for token in required:
            if not any(token in arg for arg in cfg["command"]):
                ap.error(f"{cfg['name']}: command must explicitly contain {token}")
    out.mkdir(parents=True, exist_ok=False)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    source = {str(p.relative_to(ROOT)): identity(p) for p in [
        ROOT / "research/r2/air/resume-distributions.py", ROOT / "research/r2/air/run.py",
        ROOT / "research/r2/corpus/freeze.json", ROOT / "research/r2/corpus/semantic-cases.json"]}
    for cfg in configs:
        source[cfg["name"]] = {p: identity(ROOT / p) for p in cfg["source_files"]}
    (out / "source-identities.json").write_text(json.dumps(source, indent=2)+"\n")
    env = {k: v for k, v in os.environ.items() if k in ALLOWED}
    env["NO_COLOR"] = "1"
    records, seen, h5_cases, configuration_ids = [], set(), {}, {}
    for phase, count in (("warmup", args.warmup), ("measured", args.samples)):
        for number in range(count):
            for mode in ("fixed", "varied"):
                # Spread the varied observations across structured and random strata.
                index = 0 if mode == "fixed" else number*255//max(count-1, 1)
                case_id = f"swc-v1-{index:03d}"
                case = ROOT / "research/r2/corpus/h0/corpus" / case_id
                values = {"input": str(case), "statement": str(case / "statement.json"), "witness": str(case / "witness.json"), "case_index": str(index)}
                # Rotate first candidate on successive samples to reduce ordering bias.
                order = configs[number % len(configs):]+configs[:number % len(configs)]
                for cfg in order:
                    sample = out / phase / mode / f"{number:03d}" / cfg["name"]
                    sample.parent.mkdir(parents=True, exist_ok=True)
                    values["output"] = str(sample)
                    command = [arg.format_map(values) for arg in cfg["command"]]
                    started = time.monotonic()
                    with (sample.parent / (cfg["name"]+".launcher.log")).open("wb") as log:
                        process = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
                    record = {"phase": phase, "mode": mode, "sample": number, "configuration": cfg["name"], "case_id": case_id,
                              "argv": command, "output": str(sample), "exit_status": process.returncode, "wall_seconds": time.monotonic()-started,
                              "statement": identity(values["statement"]), "witness": identity(values["witness"])}
                    if process.returncode == 0:
                        result = json.loads((sample / cfg.get("result_file", "results.json")).read_text())
                        proof = identity(sample / cfg.get("proof_file", "proof.postcard"))
                        if result.get("native_verified") is not True or proof["sha256"] in seen:
                            raise AssertionError("proof must be independently generated, distinct and native verified")
                        seen.add(proof["sha256"])
                        config_identity = identity(sample / cfg.get("configuration_file", "configuration.json"))
                        if configuration_ids.setdefault(cfg["name"], config_identity["sha256"]) != config_identity["sha256"]:
                            raise AssertionError("configuration/source identity changed inside one distribution")
                        record.update({"proof": proof, "results": result, "configuration_identity": config_identity})
                        if (sample / "h5-case.json").exists():
                            mapped = identity(sample / "h5-case.json")
                            previous = h5_cases.setdefault(case_id, mapped["sha256"])
                            if previous != mapped["sha256"]:
                                raise AssertionError("C2/C3 H5 mapping changed for the same frozen H0 case")
                            record["h5_case"] = mapped
                    records.append(record)
                    with (out / "samples.jsonl").open("a") as log:
                        log.write(json.dumps(record)+"\n")
                    if process.returncode:
                        raise RuntimeError(f"sample failed; evidence retained at {sample}")
    rows = []
    for cfg in configs:
        for mode in ("fixed", "varied"):
            samples = [r for r in records if r["phase"] == "measured" and r["mode"] == mode and r["configuration"] == cfg["name"]]
            if len(samples) != args.samples or (mode == "varied" and len({r["witness"]["sha256"] for r in samples}) != args.samples):
                raise AssertionError("independent distribution coverage incomplete")
            metrics = {}
            for key in ("prove_ms", "verify_ms", "raw_proof_bytes", "peak_rss_bytes"):
                values = sorted(r["results"][key] for r in samples if r["results"].get(key) is not None)
                if len(values) != args.samples:
                    raise AssertionError(f"missing measured {key}: {cfg['name']}/{mode}")
                metrics[key] = {"median": statistics.median(values), "p90_nearest_rank": values[math.ceil(.90*len(values))-1], "p95_nearest_rank": values[math.ceil(.95*len(values))-1], "p99_nearest_rank": values[math.ceil(.99*len(values))-1], "min": values[0], "max": values[-1], "sample_standard_deviation": statistics.stdev(values), "sample_count": len(values), "p99_caveat": "Nearest-rank order statistic only; no strong population p99 claim", "probability_sample_max_covers_population_p99_iid": 1-.99**len(values)}
            rows.append({"configuration": cfg["name"], "mode": mode, "samples": len(samples), "metrics": metrics})
    summary = {"measurement_class": "MEASURED", "rows": rows, "warmup_samples_per_mode_configuration": args.warmup,
               "warmup_definition": "discarded independent fresh processes warm machine/filesystem caches; no claim of reused in-process prover state",
               "independence": "fresh process and OS proof entropy; all proof SHA256 identities distinct including warmup", "security": "SECURITY_NOT_QUALIFIED", "promotion": "NOT_AUTHORIZED"}
    (out / "summary.json").write_text(json.dumps(summary, indent=2)+"\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
