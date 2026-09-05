#!/usr/bin/env python3
"""Measured C0 component gas only; never complete verifier/transaction gas.

Opening reduction uses real packed input fields with fixed benchmark alpha=7 (not
Fiat-Shamir). Node replay uses real frontier digest pairs repeated to the exact
pruned internal-node count. It does not reconstruct MMCS or authenticate roots.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlparse
from urllib.request import Request, urlopen

sys.dont_write_bytecode = True
from codec import MODULUS, parse_c10
from model import FEATURES, ROOT, calibration, dump, evm_work, load

HERE = Path(__file__).resolve().parent
SOURCES = ("resume-c0-first-anchor", "resume-c0-grid-01")
HELD_OUT = "fixed-b4-q48"
SENDER = "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266"
GAS_LIMIT = 16_777_216
LIBRARIES = ("BabyBear.sol", "Digest512.sol", "KeccakPair512.sol")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def rpc(url, method, params):
    request = Request(url, data=json.dumps({"jsonrpc": "2.0", "id": 1,
                      "method": method, "params": params}).encode(),
                      headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=180) as response:
        result = json.load(response)
    if "error" in result:
        raise RuntimeError(json.dumps(result["error"], sort_keys=True))
    return result["result"]


def receipt(url, transaction):
    for _ in range(120):
        result = rpc(url, "eth_getTransactionReceipt", [transaction])
        if result is not None:
            if int(result["status"], 16) != 1:
                raise RuntimeError(f"reverted transaction: {json.dumps(result)}")
            return result
        time.sleep(0.1)
    raise RuntimeError(f"receipt timeout: {transaction}")


def word(value):
    return value.to_bytes(32, "big")


def calldata(keccak, component, payload, active):
    if component == "opening":
        signature = b"opening(bytes,uint256,bool)"
        args = word(96) + word(7) + word(int(active))
    else:
        signature = b"nodes(bytes,bool)"
        args = word(64) + word(int(active))
    return keccak(signature)[:4] + args + word(len(payload)) + payload + bytes(-len(payload) % 32)


def inputs():
    """Reparse pinned proof bytes; independently rederive the geometry operation ledger."""
    rows = []
    pins = {}
    for source in SOURCES:
        folder = HERE / "outputs" / source
        for name in ("samples.json", "records.json"):
            pins[str(folder / name)] = sha((folder / name).read_bytes())
        records = {r["slot"]["id"]: Path(r["command_record"]).parent for r in load(folder / "records.json")}
        for sample in load(folder / "samples.json"):
            # Normalized security regimes are never pooled into a fixed-regime cost fit.
            if sample["regime"] != "fixed_unqualified":
                continue
            profile = sample["profile_id"]
            rep = int(sample["id"].rsplit("-", 1)[1])
            directory = records[profile]
            proof = directory / f"proof-{rep}.bin"
            raw = proof.read_bytes()
            parsed = parse_c10(raw)
            if parsed["proof_sha256"] != sample["proof_sha256"] or not sample["complete_native_verified"]:
                raise ValueError(f"proof identity/native status mismatch: {proof}")
            measurement_path = directory / "measurements.json"
            pins[str(measurement_path)] = sha(measurement_path.read_bytes())
            measurements = load(measurement_path)
            native = next(r for r in measurements["repetitions"] if r["repetition"] == rep)
            work = evm_work(sample["shape"], native["query_indices"])
            if work["features"] != sample["features"] or not native["native_verified"]:
                raise ValueError(f"shape/query feature mismatch: {proof}")
            sections = parsed["parser_sections"]
            opened = b"".join(raw[s["offset"]:s["offset"] + s["bytes"]]
                              for s in sections if s["section"] == "input_base")
            digests = b"".join(raw[s["offset"]:s["offset"] + s["bytes"]]
                               for s in sections if s["section"] == "frontier_digests")
            if len(opened) != 4 * work["features"]["opened_base_elements"] or len(digests) < 128:
                raise ValueError("opening/frontier ledger mismatch")
            # Replay real digest pairs, not alleged native parent nodes. No root claim is made.
            count = work["features"]["merkle_hashes"]
            digest_count = len(digests) // 64
            pairs = b"".join(digests[(2*i % digest_count)*64:(2*i % digest_count+1)*64]
                             + digests[((2*i+1) % digest_count)*64:((2*i+1) % digest_count+1)*64]
                             for i in range(count))
            pins[str(proof)] = sha(raw)
            rows.append((sample, work, proof, opened, pairs))
    if not any(s[0]["profile_id"] == HELD_OUT for s in rows):
        raise ValueError("entire predeclared held-out profile missing")
    return rows, pins


def reference(keccak, component, payload, active):
    if component == "opening":
        result = 0
        for i in range(0, len(payload), 4):
            value = int.from_bytes(payload[i:i+4], "big")
            result = (result * (7 if active else 1) + value) % MODULUS
        return [result]
    left = right = 0
    for i in range(0, len(payload), 128):
        pair = payload[i:i+128]
        a, b = ((keccak(b"\x00\x41" + pair), keccak(b"\x01\x41" + pair))
                if active else (pair[:32], pair[64:96]))
        left ^= int.from_bytes(a, "big")
        right ^= int.from_bytes(b, "big")
    return [left, right]


def fit(rows):
    fits = {}
    for component, features in (("opening", ["fixed", "opened_base_elements"]),
                                ("nodes", ["fixed", "merkle_hashes"])):
        group = [r for r in rows if r["component"] == component]
        for target in ("component_kernel_gas", "parse_scan_control_kernel_gas"):
            fits[f"{component}/{target}"] = calibration(group, features, target)
        # Preserve the real rank barrier: q and opened fields are collinear for this C0 AIR.
        fits[f"{component}/full_structural_rank_diagnostic"] = calibration(group, list(FEATURES), "component_kernel_gas")
    return fits


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rpc-url", default="http://127.0.0.1:18545")
    parser.add_argument("--diagnostic-rpc-url", default="http://127.0.0.1:18546")
    parser.add_argument("--node-provenance", required=True, type=Path,
                        help="JSON with hardfork and exact node launch commands, supplied by Main")
    parser.add_argument("--solc", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    for url in (args.rpc_url, args.diagnostic_rpc_url):
        parsed_url = urlparse(url)
        if (parsed_url.scheme != "http" or parsed_url.hostname != "127.0.0.1"
                or parsed_url.port not in (18545, 18546) or parsed_url.path not in ("", "/")
                or parsed_url.username or parsed_url.password or parsed_url.query or parsed_url.fragment):
            parser.error("only Main-owned loopback ports 18545/18546 permitted")
    output = args.output.resolve()
    if output.parent != HERE / "outputs" or not output.name.startswith("resume-"):
        parser.error("output must be a new models/outputs/resume-* directory")
    output.mkdir(parents=True, exist_ok=False)
    provenance = load(args.node_provenance)
    clean_env = {k: os.environ[k] for k in ("PATH", "LANG", "LC_ALL") if k in os.environ}
    services = {service["rpc_url"]: service for service in provenance.get("services", [])}
    if any(url not in services or not services[url].get("hardfork")
           or not services[url].get("launch_args") for url in (args.rpc_url, args.diagnostic_rpc_url)):
        parser.error("node provenance must declare both services, hardforks and launch_args")
    clean_env["NO_COLOR"] = "1"
    solc = args.solc.resolve(strict=True)
    keccak_path = ROOT / "research/harness/report-generator/keccak.py"
    spec = importlib.util.spec_from_file_location("gas_keccak", keccak_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.self_test()
    keccak = module.keccak256
    samples, pins = inputs()
    dump(output / "input-pins.json", pins)
    rows, failures = [], []
    declaration = {"schema": "pqtc.r2.models.component-gas.v1", "held_out_profile": HELD_OUT,
                   "scope": "COMPONENT_GAS_ONLY_NOT_COMPLETE_VERIFIER_NOT_CRYPTOGRAPHIC_ACCEPTANCE",
                   "complete_transaction_gas": None, "full_evm_verifier_gas": None,
                   "limitations": ["No complete PQTCC10R1 EVM verifier exists in this harness.",
                                    "Opening kernel is base-field Horner at benchmark alpha 7, not extension DEEP/FRI verification.",
                                    "Node kernel replays independent frontier-digest pairs to the exact internal-node count; no MMCS topology/root authentication.",
                                    "Node memory/loop/copy costs belong to this implementation, not native verifier opcode counts.",
                                    "Controls measure parse/copy plus checksums; they are not pure parsing and are not subtracted.",
                                    "ABI intrinsic gas is harness-specific, not proof transaction calldata gas.",
                                    "No transcript, AIR, FRI folds, payout/state or complete proof parsing costs are inferred."],
                   "feature_justification": {"opening": "fixed + actual opened base elements; each element has one mul/add; query count is collinear",
                                             "nodes": "fixed + exact internal hash count; each replay executes one KeccakPair512, in chunks of at most 1024 nodes; chunk overhead remains in residuals"},
                   "node_launch_provenance": provenance, "nodes": {}, "failures": failures}
    dump(output / "declaration.json", declaration)
    try:
        for url in (args.rpc_url, args.diagnostic_rpc_url):
            client = rpc(url, "web3_clientVersion", [])
            chain = int(rpc(url, "eth_chainId", []), 16)
            if chain != 31337 or "anvil" not in client.lower():
                raise ValueError("requires disposable Anvil chain31337")
            declaration["nodes"][url] = {"client": client, "chain_id": chain,
                                        "latest_block": rpc(url, "eth_getBlockByNumber", ["latest", False])}
        if SENDER not in [a.lower() for a in rpc(args.rpc_url, "eth_accounts", [])]:
            raise ValueError("public default Anvil account unavailable")
        with tempfile.TemporaryDirectory(prefix="pqtc-r2-gas-", dir="/tmp") as temp:
            workspace = Path(temp).resolve()
            # Check only existence; never read or source any dotenv file.
            if any((ancestor / ".env").exists() for ancestor in (workspace, *workspace.parents)):
                raise ValueError("dotenv ancestry forbidden")
            (workspace / "src/libraries").mkdir(parents=True)
            (workspace / "home").mkdir()
            clean_env["HOME"] = str(workspace / "home")
            clean_env["TMPDIR"] = str(workspace)
            copied = [(HERE / "gasComponents.sol", workspace / "src/GasComponents.sol")]
            copied += [(ROOT / "contracts/src/libraries" / name, workspace / "src/libraries" / name) for name in LIBRARIES]
            for source, dest in copied:
                shutil.copyfile(source, dest)
            config = '[profile.default]\nsrc = "src"\nout = "out"\nlibs = []\nevm_version = "cancun"\noptimizer = true\noptimizer_runs = 200\nvia_ir = true\nbytecode_hash = "none"\n'
            (workspace / "foundry.toml").write_text(config)
            command = ["forge", "build", "--offline", "--use", str(solc)]
            versions = {}
            for tool in (["forge", "--version"], [str(solc), "--version"]):
                result = subprocess.run(tool, cwd=workspace, env=clean_env, capture_output=True, text=True, check=True)
                versions[tool[0]] = result.stdout
            if "0.8.30" not in versions[str(solc)]:
                raise ValueError("requires local pinned solc 0.8.30")
            build = subprocess.run(command, cwd=workspace, env=clean_env, capture_output=True, text=True)
            (output / "build.stdout.log").write_text(build.stdout)
            (output / "build.stderr.log").write_text(build.stderr)
            if build.returncode:
                raise RuntimeError("isolated offline build failed; inspect build logs")
            artifact = load(workspace / "out/GasComponents.sol/GasComponents.json")
            dump(output / "GasComponents.artifact.json", artifact)
            creation = artifact["bytecode"]["object"]
            if not creation.startswith("0x"):
                creation = "0x" + creation
            deploy_hash = rpc(args.rpc_url, "eth_sendTransaction", [{"from": SENDER, "data": creation, "gas": hex(GAS_LIMIT)}])
            deploy_receipt = receipt(args.rpc_url, deploy_hash)
            address = deploy_receipt["contractAddress"]
            runtime = bytes.fromhex(rpc(args.rpc_url, "eth_getCode", [address, "latest"])[2:])
            expected_runtime = bytes.fromhex(artifact["deployedBytecode"]["object"].removeprefix("0x"))
            if runtime != expected_runtime:
                raise ValueError("deployed runtime differs from pinned build artifact")
            source_pins = {str(source): sha(source.read_bytes()) for source, _ in copied}
            source_pins.update({str(path): sha(path.read_bytes()) for path in
                                (Path(__file__), HERE / "codec.py", HERE / "model.py", keccak_path)})
            implementation = sha(runtime)
            dump(output / "build-provenance.json", {"workspace": str(workspace), "command": command,
                 "foundry_config": config, "environment_keys": sorted(clean_env), "versions": versions,
                 "compiler_sha256": sha(solc.read_bytes()), "source_sha256": source_pins,
                 "runtime_sha256": implementation, "creation_sha256": sha(bytes.fromhex(creation[2:])),
                 "runtime_bytes": len(runtime), "address": address, "deployment_receipt": deploy_receipt,
                 "compiler_evm_target": "cancun", "node_hardfork": services[args.rpc_url]["hardfork"]})
            for sample, work, proof, opened, pairs in samples:
                for component, payload in (("opening", opened), ("nodes", pairs)):
                    observations = []
                    for active in (True, False):
                        chunks = []
                        stride = 128 * 1024 if component == "nodes" else len(payload)
                        for offset in range(0, len(payload), stride):
                            chunk = payload[offset:offset+stride]
                            data = calldata(keccak, component, chunk, active)
                            tx = {"from": SENDER, "to": address, "data": "0x" + data.hex(), "gas": hex(GAS_LIMIT)}
                            expected = reference(keccak, component, chunk, active)
                            raw = bytes.fromhex(rpc(args.rpc_url, "eth_call", [tx, "latest"])[2:])
                            values = [int.from_bytes(raw[i:i+32], "big") for i in range(0, len(raw), 32)]
                            if len(raw) % 32 or len(values) != len(expected)+1 or values[1:] != expected:
                                raise ValueError(f"independent value check failed: {sample['id']} {component} {active}")
                            tx_hash = rpc(args.rpc_url, "eth_sendTransaction", [tx])
                            measured = receipt(args.rpc_url, tx_hash)
                            intrinsic = 21000 + sum(4 if b == 0 else 16 for b in data)
                            floor = 21000 + 10 * sum(1 if b == 0 else 4 for b in data)
                            chunks.append({"offset": offset, "payload_bytes": len(chunk), "kernel_gas": values[0],
                                "independent_expected": expected, "evm_output": values[1:], "correct": True,
                                "calldata_sha256": sha(data), "calldata_bytes": len(data),
                                "legacy_intrinsic_gas": intrinsic, "eip7623_floor_gas": floor, "receipt": measured,
                                "harness_receipt_gas": int(measured["gasUsed"], 16),
                                "receipt_minus_legacy_intrinsic": int(measured["gasUsed"], 16)-intrinsic,
                                "overhead_note": "Receipt includes calldata floor where active; subtraction is not execution gas."})
                        observations.append({"active": active, "kernel_gas": sum(c["kernel_gas"] for c in chunks),
                                             "chunks": chunks})
                    row = {"proof_sha256": sample["proof_sha256"], "proof_path": str(proof),
                           "profile_id": sample["profile_id"], "relation": "C0", "codec": sample["codec"],
                           "regime": "fixed_unqualified", "implementation_id": implementation,
                           "metric_scope": f"component_{component}_gas_not_complete_verifier",
                           "measurement_status": "MEASURED", "component": component,
                           "split": "held_out" if sample["profile_id"] == HELD_OUT else "train",
                           "features": work["features"], "shape": sample["shape"],
                           "payload_sha256": sha(payload), "payload_bytes": len(payload),
                           "component_kernel_gas": observations[0]["kernel_gas"],
                           "parse_scan_control_kernel_gas": observations[1]["kernel_gas"],
                           "observations": observations, "complete_transaction_gas": None}
                    rows.append(row)
                    dump(output / "samples.json", rows)
            dump(output / "fits.json", fit(rows))
    except Exception as error:
        failures.append({"error": str(error), "measurement_status": "FAILED_NOT_A_FULL_GAS_ESTIMATE"})
        raise
    finally:
        dump(output / "declaration.json", declaration)
        dump(output / "samples.json", rows)
    print(json.dumps({"output": str(output), "component_rows": len(rows), "complete_transaction_gas": None}))


if __name__ == "__main__":
    main()
