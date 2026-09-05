#!/usr/bin/env python3
"""Execute the actual generated AIR arithmetic on a disposable local chain.
Not a proof verifier; no custody path; the instruction tape is constructor-bound.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import tempfile
import shutil
from urllib.request import Request, urlopen
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[3]
SAFE_ENV = {k: v for k, v in os.environ.items() if k in {"PATH", "HOME", "CARGO_HOME", "RUSTUP_HOME", "CARGO_TARGET_DIR", "RAYON_NUM_THREADS", "OMP_NUM_THREADS", "TMPDIR", "SDKROOT", "MACOSX_DEPLOYMENT_TARGET"}}
SAFE_ENV.update({"NO_COLOR": "1", "FOUNDRY_DISABLE_NIGHTLY_WARNING": "1"})

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--rpc-url", required=True)
    ap.add_argument("--diagnostic", action="store_true")
    args = ap.parse_args()
    parsed = urlparse(args.rpc_url)
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"} or parsed.scheme != "http" or parsed.username or parsed.password:
        raise ValueError("disposable local HTTP RPC only")
    source = args.input.resolve()
    out = args.output.resolve()
    if not any(part.startswith("resume-") for part in out.parts):
        raise ValueError("new outputs must be under resume-*")
    out.mkdir(parents=True, exist_ok=False)
    vector = json.loads((source / "air-cost-vector.json").read_text())
    program = (source / "air-program.bin").read_bytes()
    requests = []
    def rpc(method, params):
        payload = {"jsonrpc": "2.0", "id": len(requests)+1, "method": method, "params": params}
        with urlopen(Request(args.rpc_url, json.dumps(payload).encode(), {"Content-Type": "application/json"}), timeout=300) as response:
            result = json.load(response)
        requests.append({"method": method, "params": params, "response": result})
        if "error" in result:
            raise RuntimeError(json.dumps(result["error"]))
        return result["result"]
    def receipt(tx):
        deadline = time.monotonic()+120
        while time.monotonic() < deadline:
            value = rpc("eth_getTransactionReceipt", [tx])
            if value:
                return value
            time.sleep(0.1)
        raise TimeoutError("local transaction receipt")
    result = {"measurement_class": "EXECUTION_BLOCKED", "stage": "AIR-arithmetic-cost-prototype", "native_proof_verifier": False,
              "security": "SECURITY_NOT_QUALIFIED", "promotion": "NOT_AUTHORIZED", "diagnostic": args.diagnostic,
              "scope": "All compiled AIR constraints in BabyBear^4; caller-supplied periodic polynomial evaluations; no FRI, transcript, quotient identity, custody, or proof verification",
              "program_bytes": len(program), "opcode_inventory": vector["operations"], "rpc_url": args.rpc_url}
    result.update({"input_path": str(source), "program_sha256": hashlib.sha256(program).hexdigest(),
                   "vector_sha256": hashlib.sha256((source / "air-cost-vector.json").read_bytes()).hexdigest(),
                   "program_keccak256": vector["program_keccak256"],
                   "configuration": json.loads((source / "configuration.json").read_text()),
                   "tape_keccak_opcode_gas": 30+6*((len(program)+31)//32),
                   "tape_keccak_cost_scope": "KECCAK256 opcode only; memory and tape calldata separately charged"})
    isolated = tempfile.TemporaryDirectory(prefix="pqtc-r2-air-", dir="/tmp")
    work = Path(isolated.name)
    (work / "src").mkdir()
    shutil.copyfile(ROOT / "research/r2/air/evm/foundry.toml", work / "foundry.toml")
    shutil.copyfile(ROOT / "research/r2/air/evm/src/AirCost.sol", work / "src/AirCost.sol")
    try:
        if int(rpc("eth_chainId", []), 16) != 31337:
            raise ValueError("requires disposable chain31337")
        account = rpc("eth_accounts", [])[0]
        build = subprocess.run(["forge", "build", "--root", str(work)], cwd=work, env=SAFE_ENV, capture_output=True, text=True)
        result["compiler_command"] = {"argv": build.args, "cwd": str(work), "exit_status": build.returncode, "environment": SAFE_ENV}
        (out / "solidity-build.log").write_text(build.stdout+build.stderr)
        build.check_returncode()
        artifact = json.loads((work / "out/AirCost.sol/AirCost.json").read_text())
        (out / "AirCost.artifact.json").write_text(json.dumps(artifact))
        bytecode = bytes.fromhex(artifact["bytecode"]["object"].removeprefix("0x"))
        runtime = bytes.fromhex(artifact["deployedBytecode"]["object"].removeprefix("0x"))
        word = lambda n: int(n).to_bytes(32, "big")
        constructor = bytes.fromhex(vector["program_keccak256"])+word(len(vector["inputs"]))
        limit = 1_000_000_000 if args.diagnostic else 16_777_216
        deployment = receipt(rpc("eth_sendTransaction", [{"from": account, "data": "0x"+(bytecode+constructor).hex(), "gas": hex(limit)}]))
        result.update({"deployment_receipt": deployment, "initcode_bytes": len(bytecode+constructor), "runtime_bytes": len(runtime)})
        if int(deployment["status"], 16) != 1:
            raise RuntimeError("AIR evaluator deployment failed")
        selector = subprocess.check_output(["cast", "sig", "evaluate(bytes,uint256[4][],uint256[4])"], cwd=work, env=SAFE_ENV, text=True).strip()
        byte_tail = word(len(program))+program+b"\0"*((-len(program))%32)
        array_tail = word(len(vector["inputs"]))+b"".join(word(v) for item in vector["inputs"] for v in item)
        calldata = bytes.fromhex(selector.removeprefix("0x"))+word(192)+word(192+len(byte_tail))+b"".join(word(v) for v in vector["alpha"])+byte_tail+array_tail
        call = {"from": account, "to": deployment["contractAddress"], "data": "0x"+calldata.hex(), "gas": hex(limit)}
        returned = bytes.fromhex(rpc("eth_call", [call, "latest"]).removeprefix("0x"))
        expected = b"".join(word(v) for v in vector["expected"])
        if returned != expected:
            raise AssertionError("Solidity AIR result differs from independent symbolic Rust evaluation")
        controls = []
        changed_program = bytearray(calldata)
        changed_program[4+192+32] ^= 1
        changed_input = bytearray(calldata)
        input_start = 4+192+len(byte_tail)+32
        changed_input[input_start:input_start+32] = word(2013265921)
        for name, changed in (("changed-bound-tape", changed_program), ("noncanonical-input", changed_input)):
            rejected = False
            try:
                rpc("eth_call", [{**call, "data": "0x"+changed.hex()}, "latest"])
            except RuntimeError as exc:
                rejected = "revert" in str(exc).lower()
            if not rejected:
                raise AssertionError(f"arithmetic control not rejected: {name}")
            controls.append({"control": name, "rejected": True, "scope": "arithmetic evaluator, not proof verification"})
        result["negative_controls"] = controls
        evaluation = receipt(rpc("eth_sendTransaction", [call]))
        if int(evaluation["status"], 16) != 1:
            raise RuntimeError("AIR evaluation transaction failed")
        zero = calldata.count(0)
        result.update({"measurement_class": "MEASURED", "solidity_parity": True, "evaluation_receipt": evaluation,
                       "total_transaction_gas": int(evaluation["gasUsed"], 16), "constructor_gas": int(deployment["gasUsed"], 16),
                       "abi_bytes": len(calldata), "calldata_zero_bytes": zero, "calldata_nonzero_bytes": len(calldata)-zero,
                       "eip2028_data_gas": zero*4+(len(calldata)-zero)*16,
                       "product_gate": "NOT_APPLICABLE: arithmetic cost prototype, not complete withdrawal", "physical_gate": "DIAGNOSTIC_NONPROMOTION" if args.diagnostic else "local-capped-execution"})
    except Exception as exc:
        result["error"] = str(exc)
        if isinstance(exc, AssertionError):
            result["stop_reason_class"] = "reference-correctness failure"
        elif any(text in str(exc).lower() for text in ("gas", "transaction failed", "deployment failed")):
            result["stop_reason_class"] = "measured performance failure"
        else:
            result["stop_reason_class"] = "missing software/API/configuration"
    finally:
        (out / "air-cost-rpc.json").write_text(json.dumps(requests, indent=2)+"\n")
        (out / "air-cost-results.json").write_text(json.dumps(result, indent=2)+"\n")
        isolated.cleanup()
    print(json.dumps(result))
    return 0 if result["measurement_class"] == "MEASURED" else 1

if __name__ == "__main__":
    raise SystemExit(main())
