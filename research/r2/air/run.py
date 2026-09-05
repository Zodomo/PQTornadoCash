#!/usr/bin/env python3
"""Run one already-built AIR experiment, retaining exact stdout/stderr and RSS.
Main serializes invocations; this entrypoint never builds, starts services or loads .env.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
ALLOWED = {"PATH", "HOME", "CARGO_HOME", "RUSTUP_HOME", "CARGO_TARGET_DIR", "RAYON_NUM_THREADS", "OMP_NUM_THREADS", "TMPDIR", "SDKROOT", "MACOSX_DEPLOYMENT_TARGET"}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, default=ROOT / "research/r2/air/target/release/pqtc-r2-air")
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    argv = args.arguments
    if argv[:1] == ["--"]:
        argv = argv[1:]
    if "--output" not in argv:
        parser.error("pass explicit --output after -- for isolated run provenance")
    out = (ROOT / argv[argv.index("--output")+1]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    env = {k: v for k, v in os.environ.items() if k in ALLOWED}
    env.update({"NO_COLOR": "1", "RUST_BACKTRACE": "1"})
    command = ["/usr/bin/time", "-l" if platform.system() == "Darwin" else "-v", str(args.binary.resolve()), *argv]
    start = time.monotonic()
    with (out / "stdout.log").open("wb") as stdout, (out / "stderr.log").open("wb") as stderr:
        process = subprocess.run(command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr)
    elapsed = time.monotonic()-start
    raw = (out / "stderr.log").read_text(errors="replace")
    pattern = r"(\d+)\s+maximum resident set size" if platform.system() == "Darwin" else r"Maximum resident set size \(kbytes\):\s*(\d+)"
    match = re.search(pattern, raw)
    rss = int(match.group(1))*(1 if platform.system() == "Darwin" else 1024) if match else None
    provenance = {"argv": command, "cwd": str(ROOT), "environment": env, "exit_status": process.returncode,
                  "finished_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "wall_seconds": elapsed,
                  "peak_rss_bytes": rss, "measurement_class": "MEASURED" if process.returncode == 0 else "EXECUTION_BLOCKED",
                  "stdout_path": "stdout.log", "stderr_path": "stderr.log", "security": "SECURITY_NOT_QUALIFIED"}
    (out / "command.json").write_text(json.dumps(provenance, indent=2)+"\n")
    results = out / "results.json"
    if process.returncode == 0 and results.exists():
        data = json.loads(results.read_text())
        data.update({"peak_rss_bytes": rss, "peak_rss_status": "MEASURED" if rss is not None else "NOT_EVALUATED", "command_provenance": "command.json"})
        results.write_text(json.dumps(data, indent=2)+"\n")
    print(json.dumps(provenance))
    return process.returncode

if __name__ == "__main__":
    sys.exit(main())
