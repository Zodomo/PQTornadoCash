#!/usr/bin/env python3
"""Detect public local hardware capabilities and emit, but never execute, proof commands."""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def capture(argv):
    try:
        result = subprocess.run(argv, env={"PATH": os.defpath, "LC_ALL": "C"},
                                capture_output=True, text=True, timeout=5)
        return result.stdout.strip() if result.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def detect(args):
    system, arch = platform.system(), platform.machine()
    cpu, memory, features = None, None, None
    if system == "Darwin":
        cpu = capture(["/usr/sbin/sysctl", "-n", "machdep.cpu.brand_string"])
        memory = capture(["/usr/sbin/sysctl", "-n", "hw.memsize"])
        features = capture(["/usr/sbin/sysctl", "-n", "machdep.cpu.features"])
        if arch in ("arm64", "aarch64"):
            optional = capture(["/usr/sbin/sysctl", "hw.optional"])
            features = " ".join(line.split(":", 1)[0] for line in (optional or "").splitlines()
                                if line.endswith(": 1")) or None
    elif system == "Linux":
        cpuinfo = Path("/proc/cpuinfo").read_text()
        info = dict(line.split(":", 1) for line in cpuinfo.splitlines() if ":" in line)
        info = {key.strip(): value.strip() for key, value in info.items()}
        cpu = info.get("model name", info.get("Hardware"))
        features = info.get("flags", info.get("Features"))
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                memory = int(line.split()[1]) * 1024
    tools = {name: shutil.which(name) for name in ("cargo", "rustc", "qemu-x86_64", "qemu-system-x86_64", "ssh")}
    target = args.build_root.resolve()
    portable_bin = target / "release/pqtc-r2-air"
    proof_args = ["--candidate", args.candidate, "--profile", args.profile,
                  "--queries", str(args.queries), "--log-blowup", str(args.log_blowup),
                  "--geometry", args.geometry,
                  "--statement", str(ROOT / "research/r2/corpus/h0/fixed/statement.json"),
                  "--witness", str(ROOT / "research/r2/corpus/h0/fixed/witness.json")]
    if args.security_model:
        proof_args.extend(["--security-model", args.security_model])
    labels = ["process-cold", "warmup", *[f"warm-{i:02d}" for i in range(1, args.samples + 1)]]
    run_env = {"RAYON_NUM_THREADS": str(args.threads), "OMP_NUM_THREADS": str(args.threads)}
    portable = None
    if tools["cargo"] and tools["rustc"]:
        portable = {"classification": "PORTABLE_BUILD_ON_LOCAL_HARDWARE_NOT_NEW_MACHINE",
            "build_argv": [tools["cargo"], f"+{args.toolchain}", "build", "--locked", "--offline", "--release", "--manifest-path",
                           str(ROOT / "research/r2/air/rust/Cargo.toml"), "--target-dir", str(target)],
            "env": {"RUSTFLAGS": "-C target-cpu=generic", **run_env, "CARGO_BUILD_JOBS": "4"},
            "run_commands": [{"label": label, "include_in_warm_distribution": label.startswith("warm-"),
                              "env": run_env,
                              "argv": [sys.executable, "-B", str(ROOT / "research/r2/air/run.py"),
                                       "--binary", str(portable_bin), "--", *proof_args,
                                       "--output", str(args.run_root.resolve() / label)]}
                             for label in labels],
            "toolchain_argv": [tools["rustc"], f"+{args.toolchain}", "-vV"],
            "execution_status": "NOT_EVALUATED", "prover_ms": None, "peak_rss_bytes": None}
    x86 = None
    binary_info = None
    if args.x86_binary:
        binary = args.x86_binary.resolve()
        if not binary.is_file():
            raise ValueError("explicit x86 binary does not exist")
        binary_info = capture(["/usr/bin/file", "-b", str(binary)])
        if binary_info and ("x86-64" in binary_info or "x86_64" in binary_info):
            prefix = None
            label = None
            if arch in ("x86_64", "AMD64") and os.access(binary, os.X_OK):
                if (system == "Linux" and "ELF" in binary_info) or (system == "Darwin" and "Mach-O" in binary_info):
                    prefix, label = [], "NATIVE_LOCAL_X86_NOT_YET_MEASURED"
            elif system == "Linux" and tools["qemu-x86_64"] and "ELF" in binary_info and "statically linked" in binary_info:
                prefix, label = [tools["qemu-x86_64"]], "EMULATED_X86_NOT_COMMODITY_X86_MEASUREMENT"
            if prefix is not None:
                x86 = {"classification": label,
                       "run_commands": [{"label": sample, "include_in_warm_distribution": sample.startswith("warm-"),
                                         "env": run_env, "argv": [*prefix, str(binary), *proof_args, "--output",
                                                                   str(args.run_root.resolve() / "x86" / sample)]}
                                        for sample in labels],
                       "env": run_env, "execution_status": "NOT_EVALUATED", "prover_ms": None}
    return {"schema": "pqtc.r2.conditional-hardware.v1", "measurement_status": "MEASURED",
            "measurement_scope": "local capability inventory only; no proof measurements executed",
            "host": {"os": system, "architecture": arch, "cpu": cpu, "memory_bytes": int(memory) if memory else None,
                     "cpu_features": features.split() if features else None, "logical_cpus": os.cpu_count(),
                     "requested_threads": args.threads, "kernel": platform.release()},
            "power_configuration": capture(["/usr/bin/pmset", "-g", "custom"]) if system == "Darwin" else None,
            "tools": tools, "portable_h1_command": portable, "x86_command": x86, "explicit_x86_binary_format": binary_info,
            "remote": {"configured_hosts": [], "evidence": "No explicit remote machine supplied; no private config was inspected", "available": None, "measurement_status": "NOT_EVALUATED"},
            "commodity_x86_measurements": None,
            "unavailable_reason": None if x86 else "No compatible explicit x86 executable and local native/user-emulator pair; a qemu-system executable alone is not an available guest machine.",
            "gate": "Full hardware expansion requires complete native candidate proof; command availability is not gate passage.",
            "protocol": {"execution_owner": "Main, serial benchmark processes", "randomness_policy": "same candidate OS-entropy hiding policy; record each actual proof hash, never seed reuse",
                         "cold_definition": "first process invocation; OS cache and power state uncontrolled, not claimed cold hardware",
                         "warm_definition": "subsequent sequential process invocations after one excluded warmup; OS caches may be warm, this is not same-process warm state",
                         "sample_count": args.samples, "stratum": "fixed frozen witness only; varied-witness promotion distribution remains separate",
                         "build_profile": "release; explicit Rust toolchain; target-cpu=generic, not proof of a fully scalar/no-SIMD implementation",
                         "rss_method": "air/run.py wraps /usr/bin/time, bytes on Darwin and kbytes converted to bytes on Linux",
                         "missing_measurements": ["time", "peak RSS", "actual proof verification", "power mode", "commodity x86 cold/warm samples"]}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", choices=["C1", "C2", "C3"], default="C1")
    parser.add_argument("--profile", choices=["fixed", "normalized"], default="fixed")
    parser.add_argument("--queries", type=int, default=32)
    parser.add_argument("--log-blowup", type=int, default=4)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--geometry", choices=["decomposed", "whole-round", "lanes4"], default="decomposed")
    parser.add_argument("--security-model")
    parser.add_argument("--samples", type=int, default=30)
    parser.add_argument("--toolchain", default="1.97.0", help="repository-pinned supported release compiler")
    parser.add_argument("--build-root", type=Path, default=HERE / "resume-build/portable")
    parser.add_argument("--run-root", type=Path, default=HERE / "outputs/resume-portable-C1-t1")
    parser.add_argument("--x86-binary", type=Path, help="explicit public executable; no config discovery or SSH")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.threads < 1 or args.queries < 1 or args.log_blowup < 1 or args.samples < 1:
        parser.error("thread/query/blowup/sample counts must be positive")
    if args.profile == "normalized" and not args.security_model:
        parser.error("normalized profile requires --security-model")
    for path in (args.build_root.resolve(), args.run_root.resolve()):
        if not path.is_relative_to(HERE) or not any(part.startswith("resume-") for part in path.relative_to(HERE).parts):
            parser.error("build/run roots must be resume-* paths under research/r2/conditional")
    if args.run_root.exists():
        parser.error("run root already exists; choose a fresh resume-* path")
    output = args.output.resolve()
    if not output.is_relative_to(HERE):
        parser.error("output must remain under research/r2/conditional")
    if output.exists():
        parser.error("output already exists; choose a fresh resume-* path")
    result = detect(args)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(output)


if __name__ == "__main__":
    main()
