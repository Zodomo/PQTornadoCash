#!/usr/bin/env python3
"""Serial local R2-08 experiments with the unchanged v0.3 cryptographic verifier.

Main invokes this runner after concurrent source preparation. Never loads .env.
The scoped constructor is an optimization, not a replacement verification path.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import shutil
import subprocess
import sys
import tempfile
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "research/r2/baseline"))
from evm import CAP, PARAMETER, SENDER, RPC, number, send_signed, source_catalog, attribute, write_json
from instrument import byte_ledger

ENV = {k: os.environ[k] for k in ("PATH", "HOME", "USER", "TMPDIR", "CARGO_HOME", "RUSTUP_HOME") if k in os.environ}
ENV.update(LC_ALL="C", RAYON_NUM_THREADS="1", CARGO_BUILD_JOBS="4", RUSTUP_TOOLCHAIN="1.97.0")
WITHDRAWAL = "((bytes32,bytes32),(bytes32,bytes32),address,address,uint256)"


def flat(digest):
    return "0x" + digest["left"].removeprefix("0x") + digest["right"].removeprefix("0x")


def word(value):
    return int(value, 16).to_bytes(32, "big") if isinstance(value, str) else value.to_bytes(32, "big")


class Experiment:
    def __init__(self, args):
        self.args = args
        self.out = args.output.resolve()
        if not self.out.is_relative_to(HERE) or not self.out.name.startswith("resume-") or self.out.exists():
            raise ValueError("--output must be a fresh resume-* directory within research/r2/operations")
        self.out.mkdir(parents=True)
        (self.out / "logs").mkdir()
        self.state = {"schema": "pqtc.r2.operations-resume.v1", "qualification": "SECURITY_NOT_QUALIFIED", "commands": [], "domains": {}, "policy_deferred": ["R2-05 typed-transcript/full-width continuation", "12/20 and 14/18 codec/verifier splits", "stronger-profile balanced split", "one-active-statement checkpoint, expiry/replacement/cleanup and censorship races"]}
        self.save()

    def save(self):
        write_json(self.out / "results.json", self.state)

    def run(self, label, argv, cwd=None, env=None, required=True, memory_limit=None):
        cwd = Path(cwd or self.workspace)
        log = self.out / "logs" / f"{len(self.state['commands']):05}-{label}"
        started = time.monotonic()
        def limit_memory():
            resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))
        result = subprocess.run([str(x) for x in argv], cwd=cwd, env={**ENV, **(env or {})}, capture_output=True, preexec_fn=limit_memory if memory_limit else None)
        log.with_suffix(".stdout").write_bytes(result.stdout)
        log.with_suffix(".stderr").write_bytes(result.stderr)
        self.state["commands"].append({"label": label, "argv": [str(x) for x in argv], "cwd": str(cwd), "exit_status": result.returncode, "wall_seconds": time.monotonic() - started, "stdout": str(log.with_suffix(".stdout")), "stderr": str(log.with_suffix(".stderr"))})
        self.save()
        if required and result.returncode:
            raise RuntimeError(f"{label}: exit {result.returncode}; retained {log}.stderr")
        return result

    def domain(self, name, function):
        try:
            result = function()
            self.state["domains"][name] = {"status": "EXECUTED", "result": result}
        except Exception as exc:
            self.state["domains"][name] = {"status": "ERROR", "error": str(exc), "traceback": traceback.format_exc()}
        self.save()

    def calldata(self, signature, *arguments):
        return bytes.fromhex(self.run("abi", ["cast", "calldata", signature, *arguments]).stdout.decode().strip().removeprefix("0x"))

    def call(self, address, signature, *arguments):
        data = self.calldata(signature, *arguments)
        return self.rpc.call("eth_call", [{"to": address, "data": "0x" + data.hex()}, "latest"])

    def transaction(self, label, data, to=None, value=0, cap=CAP, trace=True):
        self.rpc.call("anvil_setNextBlockBaseFeePerGas", ["0x0"])
        def signing_run(name, argv):
            if value:
                argv += ["--value", str(value)]
            return self.run(name, argv)
        # Full traces are retained for frontier indices, creates, and proof/state tests.
        # Non-frontier deposits still retain exact signed bytes, payload and mined receipt.
        if trace:
            result = send_signed(self.rpc, signing_run, self.out / label, label, data, to, cap)
            if result.get("admission") == "MINED":
                result["gas_ledger"] = attribute(self.out / label, self.rpc, self.catalog, "R2ScopedPool" if label == "create-R2ScopedPool" else None)
        else:
            from evm import PUBLIC_TEST_KEY, intrinsic
            directory = self.out / label
            directory.mkdir()
            nonce = number(self.rpc.call("eth_getTransactionCount", [SENDER, "pending"]))
            argv = ["cast", "mktx", to, "0x" + data.hex(), "--legacy", "--gas-limit", str(cap), "--gas-price", "0", "--nonce", str(nonce), "--chain", "31337", "--private-key", PUBLIC_TEST_KEY, "--no-proxy"]
            signed = signing_run(label + "-sign", argv).stdout.decode().strip()
            (directory / "signed.rlp").write_bytes(bytes.fromhex(signed.removeprefix("0x")))
            (directory / "calldata.bin").write_bytes(data)
            write_json(directory / "request.json", {"nonce": nonce, "sender": SENDER, "target": to, "value": value, "gas_limit": cap, "intrinsic": intrinsic(data), "rpc": self.rpc.url})
            try:
                tx = self.rpc.call("eth_sendRawTransaction", [signed])
                receipt = self.rpc.call("eth_getTransactionReceipt", [tx])
                if receipt is None:
                    raise RuntimeError("expected automining disposable Anvil")
                write_json(directory / "receipt.json", receipt)
                result = {"admission": "MINED", "success": number(receipt["status"]) == 1, "gas_used": number(receipt["gasUsed"]), "transaction_hash": tx, "gas_limit": cap, "trace": "not collected for non-frontier deposit"}
            except RuntimeError as exc:
                result = {"admission": "REJECTED", "error": str(exc), "gas_limit": cap}
        result["value_wei"] = value
        write_json(self.out / label / "result.json", result)
        return result

    def prepare(self):
        self.workspace = Path(tempfile.mkdtemp(prefix="pqtc-r2-operations-resume-", dir="/tmp"))
        self.rpc = RPC(self.args.rpc)
        snapshot = self.rpc.call("evm_snapshot", [])
        try:
            self.rpc.call("anvil_setNonce", [SENDER, "0x0"])
            addresses = {}
            for nonce, name in enumerate(("PQTCAirStageVerifier", "PQTCQueryVerifier", "PQTCVerificationRegistry", "R2ScopedPool", "recipient", "relayer")):
                raw = self.run("predict-" + name, ["cast", "compute-address", SENDER, "--nonce", str(nonce), "--json"]).stdout
                addresses[name] = json.loads(raw)["address"].lower()
            inputs = self.out / "inputs"
            self.run("native-scoped-history", [self.args.history_binary.resolve(), "--pool", addresses["R2ScopedPool"], "--parameter", PARAMETER, "--recipient", addresses["recipient"], "--relayer", addresses["relayer"], "--notes", "4096", "--retain-every", "16", "--output", inputs])
            generated = self.out / "R2ScopedPool.sol"
            self.run("scoped-source", [sys.executable, HERE / "make_pool.py", "--inputs", inputs / "manifest.json", "--output", generated])
            shutil.copytree(ROOT / "contracts/src", self.workspace / "src")
            text = generated.read_text()
            for library in ("Digest512", "P2BB512", "PQTCApplicationHash"):
                relative = os.path.relpath(ROOT / f"contracts/src/libraries/{library}.sol", generated.parent)
                text = text.replace('"' + relative + '"', f'"./libraries/{library}.sol"')
            (self.workspace / "src/R2ScopedPool.sol").write_text(text)
            shutil.copy2(HERE / "solidity/PayoutReceiver.sol", self.workspace / "src/PayoutReceiver.sol")
            (self.workspace / "foundry.toml").write_text('[profile.default]\nsrc="src"\nout="out"\ncache_path="cache"\nsolc_version="0.8.30"\nevm_version="prague"\noptimizer=true\noptimizer_runs=1\nvia_ir=true\n')
            write_json(self.out / "source-hashes.json", {str(p.relative_to(self.workspace)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((self.workspace / "src").rglob("*.sol"))})
            self.run("foundry-build", ["forge", "build", "--root", ".", "--build-info", "--ast"])
            self.state.update(workspace=str(self.workspace), addresses=addresses, inputs=str(inputs), compiler="solc0.8.30/prague/viaIR/runs1", chain="Osaka/31337/cap16777216", generator="scope is recomputed on-chain; both digest halves, address, denomination and chain are checked")
        finally:
            if not self.rpc.call("evm_revert", [snapshot]):
                raise RuntimeError("could not restore preparation snapshot")
        self.save()

    def deployments(self):
        deployed = {}
        rows = []
        for name in ("PQTCAirStageVerifier", "PQTCQueryVerifier", "PQTCVerificationRegistry", "R2ScopedPool", "recipient", "relayer"):
            contract = "PayoutReceiver" if name in ("recipient", "relayer") else name
            artifact = json.loads((self.workspace / "out" / (contract + ".sol") / (contract + ".json")).read_text())
            code = bytes.fromhex(artifact["bytecode"]["object"].removeprefix("0x"))
            if name == "PQTCVerificationRegistry":
                code += word(deployed["PQTCAirStageVerifier"]) + word(deployed["PQTCQueryVerifier"]) + bytes.fromhex(PARAMETER)
            if name == "R2ScopedPool":
                code += word(10**18) + bytes.fromhex(PARAMETER) + word(deployed["PQTCVerificationRegistry"])
            result = self.transaction("create-" + name, code)
            result.update(initcode_bytes=len(code), compiled_runtime_bytes=len(bytes.fromhex(artifact["deployedBytecode"]["object"].removeprefix("0x"))), initcode_limit_bytes=49152, runtime_limit_bytes=24576)
            rows.append(result)
            write_json(self.out / "deployments.json", rows)
            if not result.get("success"):
                raise RuntimeError(f"actual capped CREATE failed for {name}")
            deployed[name] = result["contract_address"].lower()
            if deployed[name] != self.addresses[name]:
                raise ValueError("predicted CREATE address mismatch")
        self.deployed = deployed
        return rows

    def deposits(self):
        if not hasattr(self, "deployed"):
            raise RuntimeError("dependency CREATE failed; no forged/etched pool fallback")
        pool = self.addresses["R2ScopedPool"]
        if self.call(pool, "scope()") != flat(self.manifest["scope"]):
            raise ValueError("mined pool scope mismatch")
        for level, zero in enumerate(self.manifest["zeros"]):
            if self.call(pool, "zero(uint8)", str(level)) != flat(zero):
                raise ValueError(f"scoped zero mismatch at {level}")
        rows = []
        frontier = {0, 1, 2, 4095} | {2**k + delta for k in range(1, 12) for delta in (-1, 0, 1)}
        for row in self.manifest["deposits"]:
            index, commitment = row["leafIndex"], row["commitment"]
            data = self.calldata("deposit((bytes32,bytes32))", f'({commitment["left"]},{commitment["right"]})')
            result = self.transaction(f"deposit-{index:04}", data, pool, value=10**18, trace=index in frontier)
            rows.append({"index": index, "frontier": index in frontier, "success": result.get("success", False), "gas_used": result.get("gas_used"), "gas_limit": CAP})
            write_json(self.out / "deposits.json", rows)
            if not result.get("success"):
                raise RuntimeError(f"deposit {index} failed; remaining indices require its mined state")
            if self.call(pool, "currentRoot()") != flat(row["root"]) or number(self.call(pool, "nextIndex()")) != index + 1:
                raise ValueError(f"actual deposited root/index mismatch at {index}")
        self.mined = True
        return {"mined_deposits": len(rows), "frontier_indices": sorted(frontier), "native_corpus_is_mined_state": False, "every_mined_root_compared": True}

    def fixture_input(self, case):
        source = self.inputs / f'note-{case["leafIndex"]:03}'
        destination = self.out / "proof-inputs" / source.name
        if destination.exists():
            return destination
        destination.mkdir(parents=True)
        for name in ("statement.json", "witness.json"):
            shutil.copy2(source / name, destination / name)
        write_json(destination / "derived-case.json", {"source": str(source), "synthetic": True, "funded": False, "kind": "actual-sequential-native-deposit"})
        write_json(destination / "mapping.json", {"mapping": "unchanged native-generated relation inputs; EVM metadata field-name adapter only"})
        write_json(destination / "evm.json", {"pool_address": self.addresses["R2ScopedPool"], "denomination_wei": self.manifest["denominationWei"], "scope": flat(case["scope"]), "root": flat(case["root"]), "nullifier_hash": flat(case["nullifierHash"]), "recipient": case["recipient"], "relayer": case["relayer"], "fee": case["feeWei"]})
        return destination

    def balances(self):
        return {key: number(self.rpc.call("eth_getBalance", [self.addresses[key], "latest"])) for key in ("R2ScopedPool", "recipient", "relayer")}

    def sequence(self, fixture, label, one_call=False, expect_success=True, cap=CAP):
        pool = self.addresses["R2ScopedPool"]
        statement = json.loads((fixture / "evm.json").read_text())
        metadata = json.loads((fixture / "proof-metadata.json").read_text())
        before = self.balances()
        if one_call:
            # Canonical ABI for a tuple of seven static words followed by two bytes values.
            a, b = [(fixture / f"part-{part}.pqtc").read_bytes() for part in ("a", "b")]
            prefix = (fixture / "part-a.calldata").read_bytes()[4:4 + 7 * 32]
            dynamic = lambda raw: word(len(raw)) + raw + bytes((-len(raw)) % 32)
            selector = self.run("onecall-selector", ["cast", "sig", f"withdrawOneCall({WITHDRAWAL},bytes,bytes)"]).stdout.decode().strip()
            data = bytes.fromhex(selector.removeprefix("0x")) + prefix + word(9 * 32) + word(9 * 32 + len(dynamic(a))) + dynamic(a) + dynamic(b)
            results = [self.transaction(label + "-onecall", data, pool, cap=cap)]
        else:
            results = []
            for part in ("a", "b"):
                result = self.transaction(label + "-" + part, (fixture / f"part-{part}.calldata").read_bytes(), pool, cap=cap)
                results.append(result)
                if not result.get("success"):
                    break
        after = self.balances()
        nullifier = statement["nullifier_hash"].removeprefix("0x")
        spent = number(self.call(pool, "nullifiers(bytes32,bytes32)", "0x" + nullifier[:64], "0x" + nullifier[64:])) != 0
        checkpoint = self.call(self.addresses["PQTCVerificationRegistry"], "checkpoint(bytes32)", metadata["verification_id"])
        success = all(row.get("success") for row in results) and (one_call or len(results) == 2)
        fee = int(statement["fee"])
        expected = {"R2ScopedPool": -10**18, "recipient": 10**18 - fee, "relayer": fee} if success else dict.fromkeys(before, 0)
        deltas = {key: after[key] - before[key] for key in before}
        state = {"success": success, "expected_success": expect_success, "spent": spent, "checkpoint": checkpoint, "balance_deltas": deltas, "expected_deltas": expected, "physical_cap": CAP, "original_target": 15_000_000, "route": "one-call-unchanged-A-plus-B-atomic" if one_call else "frozen-16/16", "transactions": results}
        state.update(declared_gas_limit=cap, diagnostic_only=cap > CAP)
        write_json(self.out / (label + "-state.json"), state)
        if success and (not spent or number(checkpoint) != 0) or deltas != expected:
            raise ValueError("nullifier/checkpoint/payment atomicity failed")
        if expect_success and not success:
            return state  # A physical cap failure is a measured result, not a fabricated success.
        if not expect_success and success:
            raise ValueError("negative payout/proof unexpectedly succeeded")
        return state

    def workload(self):
        cases = self.manifest["cases"]
        # Predeclared 30 fixed + 70 distinct real insertion witnesses, spanning all 4096 deposits.
        varied = [cases[1 + i * (len(cases) - 2) // 69] for i in range(70)]
        jobs = [("fixed", cases[0])] * 30 + [("varied", case) for case in varied]
        seen, rows = set(), []
        self.fixtures = []
        for index, (kind, case) in enumerate(jobs):
            fixture = self.out / "proofs" / f"fresh-{index:03}"
            row = {"index": index, "kind": kind, "leaf_index": case["leafIndex"], "fixture": str(fixture)}
            try:
                source = self.fixture_input(case)
                result = self.run(f"prove-{index:03}", ["/usr/bin/time", "-l", self.args.prover.resolve(), "prove", "--input", source, "--out", fixture])
                rss = re.search(rb"(\d+)\s+maximum resident set size", result.stderr)
                metadata = json.loads((fixture / "proof-metadata.json").read_text())
                if not metadata["native_verified"] or not metadata["codec_roundtrip_verified"] or metadata["proof_id"] in seen or metadata["entropy_source"] != "operating-system entropy through pqtc_stark::withdrawal_config_from_os_entropy; no caller seed":
                    raise ValueError("fresh OS-entropy/native/codec gate failed")
                seen.add(metadata["proof_id"])
                self.run(f"verify-{index:03}", [self.args.prover.resolve(), "verify", "--input", fixture, "--proof", fixture])
                spans = fixture / "canonical-spans.jsonl"
                self.run(f"ledger-{index:03}", [self.args.instrumented_prover.resolve(), "verify", "--input", fixture, "--proof", fixture], env={"R2_CODEC_LEDGER": str(spans)})
                write_json(fixture / "byte-ledger.json", byte_ledger(fixture, spans))
                row.update(status="NATIVE_AND_CODEC_VERIFIED", proof_id=metadata["proof_id"], prove_ms=metadata["prove_ms"], rss_bytes=int(rss[1]) if rss else None, unique_queries=metadata["unique_query_indices"], raw_bytes=metadata["raw_proof_bytes"])
                self.fixtures.append(fixture)
                if self.mined:
                    snapshot = self.rpc.call("evm_snapshot", [])
                    try:
                        row["capped"] = self.sequence(fixture, f"fresh-{index:03}")
                    finally:
                        if not self.rpc.call("evm_revert", [snapshot]):
                            raise RuntimeError("workload snapshot restoration failed")
                else:
                    row["capped"] = {"status": "BLOCKED_BY_MINED_DEPLOYMENT_OR_DEPOSIT_FAILURE"}
            except Exception as exc:
                row.update(status="ERROR", error=str(exc), traceback=traceback.format_exc())
            rows.append(row)
            write_json(self.out / "workload.json", rows)
        distributions = {}
        for kind in ("fixed", "varied"):
            values = sorted(row["prove_ms"] for row in rows if row["kind"] == kind and "prove_ms" in row)
            distributions[kind] = {"n": len(values), "p50_ms": values[math.ceil(len(values) * .5) - 1] if values else None, "p95_ms": values[math.ceil(len(values) * .95) - 1] if values else None}
        attempts = [row["capped"] for row in rows if "capped" in row and "success" in row["capped"]]
        return {"requested": 100, "distinct_native_verified": len(seen), "distributions": distributions, "capped_complete_attempts": len(attempts), "capped_failures": sum(not row["success"] for row in attempts), "sampled_max_is_not_worst_case_theorem": True}

    def adversaries(self):
        if not self.mined or not self.fixtures:
            raise RuntimeError("requires actual mined deposits and at least one fresh verified proof")
        fixture = self.fixtures[0]
        pool = self.addresses["R2ScopedPool"]
        rows = {}
        for scenario in ("onecall", "recipient-reject", "relayer-reject", "recipient-reenter", "relayer-reenter", "replay", "malformed-a", "malformed-b"):
            snapshot = self.rpc.call("evm_snapshot", [])
            try:
                if scenario == "onecall":
                    rows[scenario] = self.sequence(fixture, scenario, one_call=True)
                elif scenario.startswith(("recipient-", "relayer-")):
                    receiver, mode = scenario.split("-")
                    config = self.calldata("configure(bool,bool,address)", str(mode == "reject").lower(), str(mode == "reenter").lower(), pool)
                    result = self.transaction(scenario + "-configure", config, self.addresses[receiver])
                    if not result.get("success"):
                        raise RuntimeError("receiver configuration failed")
                    rows[scenario] = self.sequence(fixture, scenario, expect_success=mode != "reject")
                    if mode == "reenter" and rows[scenario]["success"]:
                        selector = self.run("guard-selector", ["cast", "sig", "ReentrantCall()"]).stdout.decode().strip()
                        if not self.call(self.addresses[receiver], "reentryError()").startswith(selector):
                            raise ValueError("receiver did not observe exact reentrancy guard")
                    if mode == "reject":
                        if rows[scenario]["spent"] or number(rows[scenario]["checkpoint"]) == 0 or len(rows[scenario]["transactions"]) != 2 or not rows[scenario]["transactions"][0].get("success"):
                            raise RuntimeError("payout rollback not reached: valid part A must succeed, B must fail, checkpoint survive and nullifier remain unspent")
                        if any(number(self.call(self.addresses[key], "payments()")) for key in ("recipient", "relayer")):
                            raise ValueError("failed payout retained receiver state")
                        balances_before_retry = self.balances()
                        config = self.calldata("configure(bool,bool,address)", "false", "false", pool)
                        self.transaction(scenario + "-recover-config", config, self.addresses[receiver])
                        retry = self.transaction(scenario + "-retry-b", (fixture / "part-b.calldata").read_bytes(), pool)
                        if not retry.get("success"):
                            raise RuntimeError("valid B retry failed after receiver recovery")
                        statement = json.loads((fixture / "evm.json").read_text())
                        nullifier = statement["nullifier_hash"].removeprefix("0x")
                        identifier = json.loads((fixture / "proof-metadata.json").read_text())["verification_id"]
                        spent = number(self.call(pool, "nullifiers(bytes32,bytes32)", "0x" + nullifier[:64], "0x" + nullifier[64:])) != 0
                        cleared = number(self.call(self.addresses["PQTCVerificationRegistry"], "checkpoint(bytes32)", identifier)) == 0
                        deltas = {key: value - balances_before_retry[key] for key, value in self.balances().items()}
                        fee = int(statement["fee"])
                        if not spent or not cleared or deltas != {"R2ScopedPool": -10**18, "recipient": 10**18 - fee, "relayer": fee}:
                            raise ValueError("recovered B did not atomically clear checkpoint, spend nullifier and pay")
                        retry.update(nullifier_spent=spent, checkpoint_cleared=cleared, balance_deltas=deltas)
                        rows[scenario]["recovery"] = retry
                elif scenario == "replay":
                    control = self.sequence(fixture, "replay-control")
                    if not control["success"]:
                        raise RuntimeError("positive complete control failed before replay")
                    before = self.balances()
                    repeated = self.transaction("replayed-b", (fixture / "part-b.calldata").read_bytes(), pool)
                    if repeated.get("success") or self.balances() != before:
                        raise ValueError("replay accepted or moved balance")
                    rows[scenario] = repeated
                else:
                    part = scenario[-1]
                    if part == "b":
                        prefix = self.transaction("malformed-b-valid-a", (fixture / "part-a.calldata").read_bytes(), pool)
                        if not prefix.get("success"):
                            raise RuntimeError("valid prefix failed before malformed B")
                    data = bytearray((fixture / f"part-{part}.calldata").read_bytes())
                    # Flip the canonical part terminator, not ABI padding.
                    raw = (fixture / f"part-{part}.pqtc").read_bytes()
                    offset = int.from_bytes(data[4 + (7 if part == "a" else 8) * 32:4 + (8 if part == "a" else 9) * 32], "big")
                    data[4 + offset + 32 + len(raw) - 1] ^= 1
                    before = self.balances()
                    result = self.transaction(scenario, bytes(data), pool)
                    if result.get("success") or self.balances() != before:
                        raise ValueError("malformed proof accepted or moved funds")
                    rows[scenario] = result
            except Exception as exc:
                rows[scenario] = {"status": "ERROR", "error": str(exc), "traceback": traceback.format_exc()}
            finally:
                if not self.rpc.call("evm_revert", [snapshot]):
                    raise RuntimeError("adversary snapshot restoration failed")
            write_json(self.out / "adversaries.json", rows)
        return rows

    def resource_control(self):
        source = self.fixture_input(self.manifest["cases"][0])
        destination = self.out / "constrained-memory-proof"
        limit = self.args.memory_limit_mib * 1024 * 1024
        result = self.run("constrained-memory", ["/usr/bin/time", "-l", self.args.prover.resolve(), "prove", "--input", source, "--out", destination], required=False, memory_limit=limit)
        record = {"limit_bytes": limit, "limit_kind": "RLIMIT_AS virtual address space, not resident-set hard limit", "exit_status": result.returncode, "sample_count": 1, "separate_from_100_proof_distribution": True}
        if result.returncode == 0:
            self.run("constrained-memory-verify", [self.args.prover.resolve(), "verify", "--input", destination, "--proof", destination])
            record["metadata"] = json.loads((destination / "proof-metadata.json").read_text())
        write_json(self.out / "constrained-memory.json", record)
        return record

    def high_gas_control(self):
        if not self.args.diagnostic_rpc:
            return {"status": "NOT_REQUESTED", "reason": "Supply separate loopback --diagnostic-rpc for non-cap-feasibility control"}
        if not self.mined or not self.fixtures:
            raise RuntimeError("requires actual mined deposits and fresh proof; no fabricated verifier fallback")
        if self.args.diagnostic_rpc == self.rpc.url:
            raise ValueError("diagnostic and capped endpoints must differ")
        capped, diagnostic = self.rpc, RPC(self.args.diagnostic_rpc)
        snapshot = diagnostic.call("evm_snapshot", [])
        try:
            diagnostic.call("anvil_loadState", [capped.call("anvil_dumpState", [])])
            diagnostic.call("evm_setBlockGasLimit", [hex(60_000_000)])
            self.rpc = diagnostic
            return self.sequence(self.fixtures[0], "high-gas-diagnostic", one_call=True, cap=48_000_000)
        finally:
            self.rpc = capped
            if not diagnostic.call("evm_revert", [snapshot]):
                raise RuntimeError("diagnostic snapshot restoration failed")

    def deposit_guards(self):
        if not self.mined:
            raise RuntimeError("requires actual mined deposit state")
        pool = self.addresses["R2ScopedPool"]
        first = self.manifest["deposits"][0]["commitment"]
        duplicate = f'({first["left"]},{first["right"]})'
        cases = {"incorrect-value": (duplicate, 0), "duplicate": (duplicate, 10**18), "zero": ("(0x" + "00" * 32 + ",0x" + "00" * 32 + ")", 10**18), "noncanonical": ("(0x" + "ff" * 32 + ",0x" + "ff" * 32 + ")", 10**18)}
        root, index, balances = self.call(pool, "currentRoot()"), self.call(pool, "nextIndex()"), self.balances()
        rows = {}
        for name, (commitment, value) in cases.items():
            result = self.transaction("deposit-guard-" + name, self.calldata("deposit((bytes32,bytes32))", commitment), pool, value=value)
            if result.get("success") or self.call(pool, "currentRoot()") != root or self.call(pool, "nextIndex()") != index or self.balances() != balances:
                raise ValueError("invalid deposit accepted or changed state")
            rows[name] = result
        return rows

    def execute(self):
        prepared = json.loads((self.args.prepared / "results.json").read_text())
        self.workspace = Path(prepared["workspace"])
        if not self.workspace.resolve().is_relative_to(Path("/tmp").resolve()):
            raise ValueError("Foundry workspace must be isolated in /tmp")
        for path, expected in json.loads((self.args.prepared / "source-hashes.json").read_text()).items():
            if hashlib.sha256((self.workspace / path).read_bytes()).hexdigest() != expected:
                raise ValueError("prepared Solidity source changed before execution")
        self.addresses = prepared["addresses"]
        self.inputs = Path(prepared["inputs"])
        self.manifest = json.loads((self.inputs / "manifest.json").read_text())
        self.catalog = source_catalog(self.workspace / "out", self.workspace)
        self.rpc = RPC(self.args.rpc)
        latest = self.rpc.call("eth_getBlockByNumber", ["latest", False])
        if number(latest["gasLimit"]) != CAP:
            raise ValueError("requires capped Osaka node with block gas limit 16777216")
        self.state.update(prepared=str(self.args.prepared.resolve()), source_hashes=str(self.args.prepared.resolve() / "source-hashes.json"), rpc=self.rpc.url, workspace=str(self.workspace))
        self.mined, self.fixtures = False, []
        snapshot = self.rpc.call("evm_snapshot", [])
        try:
            self.rpc.call("anvil_setNonce", [SENDER, "0x0"])
            self.rpc.call("anvil_setBalance", [SENDER, hex(10000 * 10**18)])
            if any(self.rpc.call("eth_getCode", [address, "latest"]) != "0x" for address in self.addresses.values()):
                raise ValueError("predicted CREATE addresses occupied; use a fresh disposable node")
            self.domain("scoped-constructor-and-dependencies", self.deployments)
            self.domain("frontier-deposits", self.deposits)
            self.domain("deposit-rejection-state", self.deposit_guards)
            self.domain("fresh-100-fixed-varied", self.workload)
            self.domain("onecall-and-state-adversaries", self.adversaries)
            self.domain("constrained-memory", self.resource_control)
            self.domain("onecall-high-gas-diagnostic", self.high_gas_control)
        finally:
            if not self.rpc.call("evm_revert", [snapshot]):
                raise RuntimeError("failed to restore complete disposable experiment snapshot")
        self.save()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "execute"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--rpc", default="http://127.0.0.1:18545")
    parser.add_argument("--diagnostic-rpc")
    parser.add_argument("--memory-limit-mib", type=int, default=1024)
    parser.add_argument("--prepared", type=Path)
    parser.add_argument("--history-binary", type=Path, default=HERE / "target/release/pqtc-r2-operations")
    parser.add_argument("--prover", type=Path, default=ROOT / "research/r2/baseline/outputs/r2-main/target-clean/release/v03-baseline-reproducer")
    parser.add_argument("--instrumented-prover", type=Path, default=ROOT / "research/r2/baseline/outputs/r2-main/target-instrumented/release/v03-baseline-reproducer")
    args = parser.parse_args()
    if args.memory_limit_mib <= 0:
        parser.error("--memory-limit-mib must be positive")
    if args.phase == "execute" and args.prepared is None:
        parser.error("execute requires --prepared")
    experiment = Experiment(args)
    experiment.domain(args.phase, experiment.prepare if args.phase == "prepare" else experiment.execute)
    print(experiment.out / "results.json")
    if any(domain["status"] == "ERROR" for domain in experiment.state["domains"].values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
