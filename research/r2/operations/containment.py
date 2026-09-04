#!/usr/bin/env python3
"""Run serialized and constructed native proof attacks in disposable worker processes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]
PARAMETER = "35adfcc070249bb0393c2fd45f0bbd48ef03cbfc08070d03335eaf952975e62ab7bc82ead4f8c1f1c39b3372be85195853134dfc9d24f43b97a5e0454ea07779"
MUTATIONS = ("trace-local-empty", "trace-next-absent", "quotient-empty", "random-absent", "hiding-empty", "fri-input-empty", "fri-openings-empty", "fri-final-empty", "fri-commits-empty", "fri-witnesses-empty")

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--binary", type=Path, default=ROOT / "research/r2/operations/target/release/verify-worker")
    p.add_argument("--input", type=Path, default=ROOT / "research/candidates/v03-baseline/proofs/v03-fixed-01")
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    output = a.output.resolve()
    if not output.is_relative_to(ROOT / "research/r2/operations") or output.exists():
        p.error("output must be new and remain in the owned research package")
    output.mkdir(parents=True)
    original_a = (a.input / "part-a.pqtc").read_bytes()
    original_b = (a.input / "part-b.pqtc").read_bytes()
    records = []
    environment = {"PATH": os.defpath, "RAYON_NUM_THREADS": "1", "RUST_BACKTRACE": "0", "LC_ALL": "C"}
    def run(label, part_a, part_b, mutation="none", uncontained=False):
        directory = output / label
        directory.mkdir()
        for name, data in (("part-a.pqtc", part_a), ("part-b.pqtc", part_b)):
            (directory / name).write_bytes(data)
        argv = [str(a.binary.resolve()), "--statement", str((a.input / "statement.json").resolve()), "--parameter", PARAMETER, "--part-a", str(directory / "part-a.pqtc"), "--part-b", str(directory / "part-b.pqtc"), "--mutation", mutation]
        if uncontained:
            argv.append("--uncontained")
        started = time.monotonic()
        command = ["/usr/bin/time", "-l" if platform.system() == "Darwin" else "-v", *argv]
        with (directory / "stdout.log").open("wb") as stdout, (directory / "stderr.log").open("wb") as stderr:
            worker = subprocess.Popen(command, env=environment, stdout=stdout, stderr=stderr, start_new_session=True)
            timed_out = False
            try:
                code = worker.wait(timeout=15)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(worker.pid, signal.SIGKILL)
                code = worker.wait()
        text = (directory / "stdout.log").read_text()
        data = next((json.loads(line) for line in reversed(text.splitlines()) if line.startswith('{"')), None)
        record = {"label": label, "command": argv, "environment": environment, "exit_code": code, "timed_out": timed_out, "wall_seconds": time.monotonic()-started, "worker": data, "rss_unit": "bytes" if platform.system() == "Darwin" else "KiB", "rss_source": str((directory / "stderr.log").relative_to(ROOT)), "part_a_sha256": hashlib.sha256(part_a).hexdigest(), "part_b_sha256": hashlib.sha256(part_b).hexdigest()}
        (directory / "result.json").write_text(json.dumps(record, indent=2) + "\n")
        records.append(record)
        return record
    valid = run("valid-before", original_a, original_b)
    assert valid["exit_code"] == 0 and valid["worker"]["status"] == "ACCEPTED", "valid control failed"
    noncanonical = bytearray(original_a)
    noncanonical[82:86] = (2013265921).to_bytes(4, "big")
    wrong_digest = bytearray(original_a)
    wrong_digest[338] ^= 1
    serialized = {"empty-a": (b"", original_b), "truncated-a": (original_a[:len(original_a)//2], original_b), "trailing-b": (original_a, original_b+b"\x00"), "oversize-a": (b"\x00"*524289, original_b), "noncanonical-public": (bytes(noncanonical), original_b), "wrong-global-digest": (bytes(wrong_digest), original_b), "corrupt-frontier": (original_a, original_b[:-5]+bytes([original_b[-5]^1])+original_b[-4:])}
    for label, (part_a, part_b) in serialized.items():
        record = run(label, part_a, part_b)
        assert not record["worker"] or record["worker"]["status"] != "ACCEPTED", label
    for mutation in MUTATIONS:
        raw = run("raw-"+mutation, original_a, original_b, mutation, True)
        contained = run("contained-"+mutation, original_a, original_b, mutation)
        assert contained["exit_code"] == 0 and contained["worker"]["status"] != "ACCEPTED", mutation
        assert contained["worker"]["valid_request_after_mutation"] is True, mutation
    final = run("valid-after", original_a, original_b)
    assert final["exit_code"] == 0 and final["worker"]["status"] == "ACCEPTED"
    report = {"schema": "pqtc.r2.native-containment.v1", "measurement_status": "MEASURED", "configuration": "frozen H0 v0.3 q32 codec/native verifier; R2 wrapper only", "security_status": "SECURITY_NOT_QUALIFIED", "valid_controls": 2, "serialized_mutations": len(serialized), "constructed_mutations": len(MUTATIONS), "observed_contained_panics": sum(bool(r["worker"] and r["worker"]["status"] == "PANIC_CONTAINED_AND_REJECTED") for r in records), "raw_process_failures": sum(r["label"].startswith("raw-") and r["exit_code"] != 0 for r in records), "limits": {"proof_part_bytes_each": 524288, "statement_bytes": 16384, "worker_wall_seconds": 15, "rss_hard_limit": None, "memory_limit_scope": "Input byte ceiling and separate processes; no claimed platform-enforced RSS ceiling. Allocator abort is not catchable by Rust unwind."}, "claim": "Observed worker recovery and hostile-input rejection only. Constructed mutations are not evidence of serialized reachability or Solidity bypass. No proof of global native panic-freedom.", "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "binary_sha256": hashlib.sha256(a.binary.read_bytes()).hexdigest(), "runs": records}
    (output / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ("valid_controls", "serialized_mutations", "constructed_mutations", "observed_contained_panics", "raw_process_failures")}))

if __name__ == "__main__":
    main()
