#!/usr/bin/env python3
"""Run one finite local research command with a clean environment and retained evidence."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
SAFE_ENV = ("PATH", "HOME", "TMPDIR", "RUSTUP_HOME", "CARGO_HOME", "SDKROOT", "MACOSX_DEPLOYMENT_TARGET")
ALLOWED_EXTRA = {"CARGO_TARGET_DIR", "RUSTFLAGS", "RAYON_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "CARGO_BUILD_JOBS", "RUST_BACKTRACE", "EVM_BIN"}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--cwd", type=Path, default=ROOT)
    p.add_argument("--timeout", type=int, default=7200)
    p.add_argument("--env", action="append", default=[])
    p.add_argument("command", nargs=argparse.REMAINDER)
    a = p.parse_args()
    command = a.command[1:] if a.command[:1] == ["--"] else a.command
    if not command or a.timeout <= 0:
        p.error("provide a finite command and a positive timeout")
    out = a.output.resolve()
    if not out.is_relative_to(ROOT / "research/r2") or out.exists():
        p.error("output must be a new directory under research/r2")
    environment = {key: os.environ[key] for key in SAFE_ENV if key in os.environ}
    environment.update({"LC_ALL": "C", "TZ": "UTC"})
    for item in a.env:
        key, separator, value = item.partition("=")
        if not separator or key not in ALLOWED_EXTRA:
            p.error("unapproved environment variable")
        environment[key] = value
    out.mkdir(parents=True)
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    timed_command = ["/usr/bin/time", "-l" if platform.system() == "Darwin" else "-v", *command]
    started = time.monotonic()
    timed_out = False
    with (out / "stdout.log").open("wb") as stdout, (out / "stderr.log").open("wb") as stderr:
        process = subprocess.Popen(timed_command, cwd=a.cwd, env=environment, stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            code = process.wait(timeout=a.timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            code = process.wait()
    wall = time.monotonic() - started
    logs = {name: {"bytes": (out / name).stat().st_size, "sha256": hashlib.sha256((out / name).read_bytes()).hexdigest()} for name in ("stdout.log", "stderr.log")}
    record = {"schema": "pqtc.r2.command-run.v1", "command": command, "timing_command": timed_command, "cwd": str(a.cwd.resolve()), "environment": environment, "started_utc": timestamp, "returncode": code, "timed_out": timed_out, "timeout_seconds": a.timeout, "wall_seconds": wall, "rss_unit": "bytes" if platform.system() == "Darwin" else "KiB", "rss_source": "external /usr/bin/time in stderr.log; do not confuse process-tree command time with prover-only timing", "platform": platform.platform(), "architecture": platform.machine(), "logs": logs, "scope": "local non-custodial research command; success is execution, not artifact qualification"}
    (out / "command.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"returncode": code, "timed_out": timed_out, "wall_seconds": wall, "evidence": str(out.relative_to(ROOT))}))
    return 124 if timed_out else code

if __name__ == "__main__":
    raise SystemExit(main())
