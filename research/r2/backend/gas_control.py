#!/usr/bin/env python3
"""Repair only C50's pre-execution shell-array defect; standalone NON-HIDING control."""
import argparse
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlparse
from urllib.request import Request, urlopen

sys.dont_write_bytecode = True
from run import PACKAGE, ROOT, clean_env, dump

PUBLIC_ANVIL_TEST_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
SCRIPT = "script/WhirBlobNativeTxBenchmark_k22_jb100_ext5_lir4_ff4_rsv3_pow28.s.sol"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rpc-url", required=True)
    parser.add_argument("--workspace", type=Path, default=PACKAGE / "gas-work")
    parser.add_argument("--output", type=Path, default=PACKAGE / "outputs/standalone-solidity-control")
    args = parser.parse_args()
    url = urlparse(args.rpc_url)
    if url.scheme != "http" or url.hostname not in {"127.0.0.1", "localhost", "::1"} or url.username or url.password or url.query or url.fragment:
        parser.error("only unauthenticated local disposable HTTP RPC allowed")
    workspace, output = args.workspace.resolve(), args.output.resolve()
    if not all(p.is_relative_to(PACKAGE) for p in (workspace, output)):
        parser.error("workspace and outputs must remain under research/r2/backend")
    output.mkdir(parents=True, exist_ok=True)
    if (output / "results.json").exists():
        parser.error("refusing to overwrite a previous control run")
    env = clean_env()
    env["CARGO_TARGET_DIR"] = str(PACKAGE / "gas-target")
    # Upstream helper subprocesses inherit this allowlist, not account secrets or .env.
    os.environ.clear()
    os.environ.update(env)

    def rpc(method, params):
        request = Request(args.rpc_url, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(), headers={"Content-Type": "application/json"})
        with urlopen(request, timeout=20) as response:
            value = json.load(response)
        if "error" in value:
            raise RuntimeError(value["error"])
        return value["result"]

    if int(rpc("eth_chainId", []), 16) != 31337 or "anvil" not in rpc("web3_clientVersion", []).lower():
        parser.error("requires Main-owned disposable Anvil chain31337")
    result = {"classification": "STANDALONE_PLAIN_WHIR_NOT_SPARTAN_NOT_H0_NOT_HIDING",
        "specification_status": "UPSTREAM_STANDALONE_CONTROL", "correctness_evidence": "NOT_EVALUATED",
        "privacy_evidence": "NON_HIDING_CONTROL", "security_status": "SECURITY_NOT_QUALIFIED",
        "performance_evidence": "NOT_EVALUATED", "implementation_stage": "BOUNDED_HARNESS_REPAIR",
        "promotion_status": "NOT_READY_FOR_BUILD_SELECTION", "rpc_url": args.rpc_url,
        "repair": "Direct argv omits empty --tc list, replacing bash3 nounset array expansion; upstream sources unchanged",
        "original_failure": "research/candidates/C50-spartan-whir/outputs/solidity-gas/stderr.log",
        "limits": "No code-size, initcode, transaction-gas or block-gas relaxation requested",
        "license_status": "UNRESOLVED_DECLARATIONS_NOT_A_LEGAL_CONCLUSION"}
    commands = []
    isolated = None
    try:
        # Reuse the frozen exact-pin checkout helper without editing its package.
        frozen = runpy.run_path(str(ROOT / "research/candidates/C50-spartan-whir/run.py"), run_name="r2_c50_source_helper")
        source, dependencies = frozen["prepare_solidity"](workspace)
        result["dependency_pins"] = dependencies
        result["license_files"] = [str(p.relative_to(source)) for p in source.rglob("*") if p.is_file() and p.name.lower() in {"license", "license.md", "license.txt", "copying", "copying.md", "copying.txt"}]
        # Foundry can discover dotenv files above cwd even with a scrubbed env.
        # Run a disposable copy outside this repository, excluding every dotenv.
        isolated = tempfile.TemporaryDirectory(prefix="pqtc-r2-backend-gas-", dir="/tmp")
        execution_root = Path(isolated.name).resolve() / "project"
        shutil.copytree(source, execution_root, ignore=shutil.ignore_patterns(".env*", ".git", "target", "out", "cache", "broadcast"))
        source = execution_root
        if source.is_relative_to(ROOT) or not (source / "foundry.toml").is_file():
            raise RuntimeError("Foundry requires an isolated project with its own foundry.toml")
        if any((parent / ".env").exists() for parent in (source, *source.parents)):
            raise RuntimeError("Foundry execution blocked: dotenv exists in isolated cwd ancestry")
        result["dotenv_isolation"] = "Temporary project outside repository; .env* excluded; ancestors checked without reading contents"
        argv = ["forge", "script", SCRIPT, "--rpc-url", args.rpc_url, "--broadcast", "--slow", "--private-key", PUBLIC_ANVIL_TEST_KEY]
        commands.append({"argv": argv, "cwd": str(source), "public_unfunded_test_key_only": True})
        with (output / "forge.stdout.log").open("w") as out, (output / "forge.stderr.log").open("w") as err:
            completed = subprocess.run(argv, cwd=source, env=env, stdout=out, stderr=err, timeout=1800, check=False)
        result["exit_code"] = completed.returncode
        # Save actual receipts and payloads, including a partial successful deployment.
        broadcasts = []
        for path in (source / "broadcast").rglob("run-latest.json"):
            value = json.loads(path.read_text())
            target = output / (path.parent.parent.name + "-" + path.parent.name + "-broadcast.json")
            dump(target, value)
            receipts = []
            for tx in value.get("transactions", []):
                tx_hash = tx.get("hash")
                if tx_hash:
                    receipt = rpc("eth_getTransactionReceipt", [tx_hash])
                    receipts.append({"transaction_hash": tx_hash, "receipt": receipt, "transaction": rpc("eth_getTransactionByHash", [tx_hash])})
            broadcasts.append({"broadcast": target.name, "receipts": receipts})
        result["broadcasts"] = broadcasts
        result["performance_evidence"] = "ACTUAL_RECEIPTS_SEE_CONTROL_SCOPE" if broadcasts else "NOT_EVALUATED_NO_TRANSACTION_RECEIPTS"
        result["correctness_evidence"] = "UPSTREAM_SCRIPT_SUCCEEDED" if completed.returncode == 0 else "EXECUTION_BLOCKED_INSPECT_RAW_LOGS_NOT_A_GAS_FAILURE"
    except Exception as error:
        result["execution_error"] = str(error)
        result["correctness_evidence"] = "EXECUTION_BLOCKED_NOT_A_GAS_FAILURE"
    finally:
        if isolated is not None:
            isolated.cleanup()
    dump(output / "commands.json", commands)
    dump(output / "results.json", result)
    print(output / "results.json")
    return 0 if result.get("exit_code") == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
