#!/usr/bin/env python3
"""R2-00 executable baseline. All writes are isolated below this package.

Sequential phases: prepare, prepare-corpus, proofs, local. Main starts the
loopback Anvil process separately. No security eligibility check gates execution.
"""
import argparse
import difflib
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import tempfile
import traceback
from pathlib import Path

from instrument import byte_ledger, extend_prepare, instrument_codec
from evm import CAP, PARAMETER, POOL, SENDER, PUBLIC_TEST_KEY, RPC, attribute, intrinsic, load_prestate, number, send_signed, source_catalog, write_json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PIN = "e51a5c5ccc4f50e0beb07cdf04d7f8dd258c7997"
FOUNDRY_PIN = "4072e48705af9d93e3c0f6e29e93b5e9a40caed8"
BASELINE = Path("research/candidates/v03-baseline")
ALLOWED_ENV = {"PATH","HOME","USER","TMPDIR","LANG","LC_ALL","CARGO_HOME","RUSTUP_HOME","RAYON_NUM_THREADS","CARGO_BUILD_JOBS","NUM_JOBS","SSL_CERT_FILE","SSL_CERT_DIR"}
CHECKS = [("manifest",["python3","research/reproduction/reproduce.py","verify-manifest"]),("all-safe",["python3","research/reproduction/reproduce.py","all-safe"]),("run-records",["python3","research/run-records/reproduce.py","check"]),("report",["python3","research/report-synthesis/generate.py","--check"]),("final",["python3","research/final/generate.py","--check"])]


class Runner:
    def __init__(self, run_id):
        if not run_id or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in run_id):
            raise ValueError("run ID must be a path-free identifier")
        self.out = HERE/"outputs"/run_id
        self.out.mkdir(parents=True,exist_ok=True)
        workspace_file = self.out/"workspaces.json"
        if workspace_file.exists():
            self.workspace = Path(json.loads(workspace_file.read_text())["root"])
        else:
            self.workspace = Path(tempfile.mkdtemp(prefix="pqtc-r2-baseline-"+run_id+"-",dir="/tmp"))
            write_json(workspace_file,{"root":str(self.workspace),"reason":"Foundry cwd outside repository prevents ancestor .env discovery; no .env copied","retention":"Keep for exact source/build reproduction; all experiment outputs remain under research/r2/baseline"})
        self.clean = self.workspace/"checkout"
        self.fork = self.workspace/"instrumented"
        self.logs = self.out/"logs"
        self.logs.mkdir(exist_ok=True)
        self.env = {key:value for key,value in os.environ.items() if key in ALLOWED_ENV}
        self.env.update({"PQTC_REPRODUCTION_NO_LIVE_CHAIN":"1","CARGO_INCREMENTAL":"0","RUSTUP_TOOLCHAIN":"1.97.0"})
        self.state = json.loads((self.out/"results.json").read_text()) if (self.out/"results.json").exists() else {"work_package":"R2-00","candidate_id":"R2-C0","public_commit":PIN,"specification_status":"exact frozen H0 relation","correctness_evidence":"untested","privacy_evidence":"configured hiding; synthetic unfunded witnesses","security_status":"SECURITY_NOT_QUALIFIED","performance_evidence":"unknown","implementation_stage":"native proof and local EVM executable paths","promotion_status":"NO_DEPLOYMENT_AUTHORIZED","decision":"CONTINUE_EXPERIMENT","commands":[],"phases":{}}
        self.save()

    def save(self):
        write_json(self.out/"results.json",self.state)

    def run(self,label,argv,cwd=None,env=None,required=True):
        cwd = Path(cwd or self.clean).resolve()
        if Path(str(argv[0])).name in {"forge","cast","anvil"}:
            if cwd.is_relative_to(ROOT):
                raise ValueError("Foundry execution cwd must be outside original repository")
            if any((ancestor/".env").exists() for ancestor in (cwd,*cwd.parents)):
                raise ValueError("Foundry dotenv discovery blocked; no .env contents were read")
        index = len(self.state["commands"])
        prefix = self.logs/f"{index:04d}-{label}"
        actual_env = {**self.env,**(env or {})}
        started = time.time()
        try:
            result = subprocess.run([str(x) for x in argv],cwd=cwd,env=actual_env,capture_output=True,check=False)
        except OSError as exc:
            result = subprocess.CompletedProcess(argv,127,b"",str(exc).encode())
        prefix.with_suffix(".stdout").write_bytes(result.stdout)
        prefix.with_suffix(".stderr").write_bytes(result.stderr)
        record = {"label":label,"argv":[str(x) for x in argv],"cwd":str(cwd),"environment":actual_env,"started_unix":started,"wall_seconds":time.time()-started,"exit_status":result.returncode,"stdout":str(prefix.with_suffix('.stdout')),"stderr":str(prefix.with_suffix('.stderr')),"stdout_sha256":hashlib.sha256(result.stdout).hexdigest(),"stderr_sha256":hashlib.sha256(result.stderr).hexdigest()}
        self.state["commands"].append(record)
        self.save()
        if required and result.returncode:
            raise RuntimeError(f"{label}: exit {result.returncode}; see {prefix}.stderr")
        return result

    def target(self,instrumented=False):
        return self.out/("target-instrumented" if instrumented else "target-clean")

    def binary(self,instrumented=False):
        return self.target(instrumented)/"release/v03-baseline-reproducer"

    def checks(self,checkout,prefix):
        return [{"name":name,"classification":"METADATA_ONLY; no cryptographic verification","exit_status":self.run(prefix+"-"+name,argv,cwd=checkout,required=False).returncode} for name,argv in CHECKS]

    def clone(self,path,commit):
        self.run("clone",["git","clone","--no-hardlinks","--no-checkout",str(ROOT),str(path)],cwd=HERE)
        self.run("checkout",["git","checkout","--detach",commit],cwd=path)

    def prepare(self):
        if self.clean.exists() or self.fork.exists():
            raise ValueError("prepare requires a new run ID; existing outputs are never overwritten")
        self.clone(self.clean,PIN)
        self.run("submodules",["git","submodule","update","--init","--recursive"],cwd=self.clean)
        inventory = {"platform":platform.platform(),"machine":platform.machine(),"python":sys.version,"cpu_count":os.cpu_count(),"tools":{}}
        for name,argv in [("rustc",["rustc","--version","--verbose"]),("cargo",["cargo","--version"]),("forge",["forge","--version"]),("cast",["cast","--version"]),("anvil",["anvil","--version"])]:
            output = self.run("inventory-"+name,argv).stdout.decode()
            inventory["tools"][name] = output
        write_json(self.out/"environment.json",inventory)
        self.state["handoff_checks"] = self.checks(self.clean,"public")
        self.epochs()
        # A separate disposable parent checkout actually recreates the deletion.
        parent = self.run("cleanup-parent",["git","rev-parse",PIN+"^"]).stdout.decode().strip()
        cleanup = self.out/"cleanup-exclusion"
        self.clone(cleanup,parent)
        before = self.checks(cleanup,"cleanup-before")
        deleted = []
        for relative in ("old_plans/pq-tornado-classic-engineering-plan.md","old_reports/ENGINEERING_REPORT.md"):
            path = cleanup/relative
            deleted.append({"path":relative,"existed_before":path.is_file(),"sha256_before":hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None})
            if path.is_file():
                path.unlink()
        after = self.checks(cleanup,"cleanup-after")
        write_json(self.out/"cleanup-exclusion.json",{"parent_commit":parent,"deleted":deleted,"before":before,"after":after,"observed_same_exit_statuses":[x["exit_status"] for x in before] == [x["exit_status"] for x in after],"public_checkout_checks":self.state["handoff_checks"]})
        if "rustc 1.97.0" not in inventory["tools"]["rustc"]:
            raise ValueError("pinned Rust 1.97.0 required")
        for tool in ("forge","cast","anvil"):
            if FOUNDRY_PIN not in inventory["tools"][tool] or "1.7.1" not in inventory["tools"][tool]:
                raise ValueError(f"pinned Foundry 1.7.1/{FOUNDRY_PIN} required for {tool}")
        self.run("clean-rust-build",["cargo","build","--locked","--release","--manifest-path",BASELINE/"native/Cargo.toml"],env={"CARGO_TARGET_DIR":str(self.target())})
        self.run("clean-foundry-build",["forge","build","--root",".","--build-info","--ast"],cwd=self.clean/BASELINE/"evm")
        self.fork.mkdir()
        for name in ("Cargo.toml","Cargo.lock","rust-toolchain.toml"):
            shutil.copy2(self.clean/name,self.fork/name)
        for name in ("crates","contracts","lib"):
            shutil.copytree(self.clean/name,self.fork/name,ignore=shutil.ignore_patterns("target","out","cache",".git"))
        for name in ("native","evm"):
            shutil.copytree(self.clean/BASELINE/name,self.fork/BASELINE/name,ignore=shutil.ignore_patterns("target","out","cache"))
        codec = self.fork/"crates/pqtc-stark/src/codec.rs"
        native = self.fork/BASELINE/"native/src/main.rs"
        patches = []
        for path,transform in [(codec,instrument_codec),(native,extend_prepare)]:
            original = path.read_text()
            changed = transform(original)
            path.write_text(changed)
            patches.extend(difflib.unified_diff(original.splitlines(True),changed.splitlines(True),fromfile=str(path.relative_to(self.fork)),tofile=str(path.relative_to(self.fork))))
        (self.out/"instrumentation.patch").write_text("".join(patches))
        # Only the disposable harness filesystem permissions change. Verifier,
        # pool, optimizer settings and constructor semantics remain frozen.
        config = self.fork/BASELINE/"evm/foundry.toml"
        text = config.read_text()
        text = text.replace('{ access = "read", path = "../proofs" }', '{ access = "read", path = '+json.dumps(str(self.out))+' }')
        text = text.replace('{ access = "write", path = "../gas" }', '{ access = "write", path = '+json.dumps(str(self.out))+' }')
        config.write_text(text)
        self.run("instrumented-rust-build",["cargo","build","--locked","--release","--manifest-path",BASELINE/"native/Cargo.toml"],cwd=self.fork,env={"CARGO_TARGET_DIR":str(self.target(True))})
        self.run("harness-foundry-build",["forge","build","--root",".","--build-info","--ast"],cwd=self.fork/BASELINE/"evm")
        self.state["pins"] = {"rust":"1.97.0","foundry":"1.7.1/"+FOUNDRY_PIN,"solc":"0.8.30","evm":"prague","optimizer_runs":1,"via_ir":True,"upstream_dependencies":"unchanged copied Cargo.lock; --locked; separate clean/instrumented targets","isolation":"fresh source checkouts and targets, sanitized environment; existing download caches may be reused"}

    def epochs(self):
        paths = ["research/final","research/report-synthesis","research/runs","research/reproduction","contracts/src","crates/pqtc-stark"]
        mapping = []
        for path in paths:
            observed = self.run("epoch",["git","log","-1","--format=%H %cI %s",PIN,"--",path]).stdout.decode().strip()
            mapping.append({"path":path,"last_touch_at_public_commit":observed,"meaning":"path history, not assertion every contained measurement was generated at this commit"})
        self.run("public-cleanup-diff",["git","show","--format=fuller","--stat",PIN])
        source_epochs = []
        for path in sorted((self.clean/"research/runs").glob("v03-*.json")):
            record = json.loads(path.read_text())
            source_epochs.append({"artifact":str(path.relative_to(self.clean)),"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"git":record.get("git"),"source":record.get("source"),"timestamp_utc":record.get("timestamp_utc")})
        if len(source_epochs) != 60:
            raise ValueError("retained 60-run evidence set is incomplete")
        write_json(self.out/"epoch-map.json",{"public_review":PIN,"path_epochs":mapping,"retained_measurement_epochs":source_epochs,"report_source_note":"Source epochs are read from original records; public cleanup/reproduction epochs are not retroactively substituted."})

    def prepare_corpus(self):
        corpus = ROOT/"research/r2/corpus/semantic-cases.json"
        destination = ROOT/"research/r2/corpus/h0"
        if destination.exists():
            raise ValueError("h0 corpus already exists; no overwrite")
        source = json.loads(corpus.read_text())
        self.run("prepare-full-corpus",[self.binary(True),"prepare","--corpus",corpus,"--out",destination],cwd=self.fork)
        write_json(destination/"r2-provenance.json",{"synthetic":True,"funded":False,"source":str(corpus),"sha256":hashlib.sha256(corpus.read_bytes()).hexdigest(),"included_cases":[c["caseId"] for c in source["cases"] if c["treeDepth"] == 20],"excluded_cases":[{"case_id":c["caseId"],"reason":"frozen H0 relation requires depth20","tree_depth":c["treeDepth"]} for c in source["cases"] if c["treeDepth"] != 20],"mapping":"unchanged frozen rejection mapper; no modular reduction of arbitrary 256-bit secrets","secret_entropy_bits":"8*log2(2013265921), about 247.25 per canonical secret; deterministic synthetic seeds are public"})
        self.state["corpus"] = str(destination)

    def verify_fixture(self,fixture,label):
        self.run(label+"-native",[self.binary(),"verify","--input",fixture,"--proof",fixture])
        spans = fixture/"canonical-spans.jsonl"
        if spans.exists():
            raise ValueError("refusing duplicate parser ledger output")
        self.run(label+"-canonical-ledger",[self.binary(True),"verify","--input",fixture,"--proof",fixture],cwd=self.fork,env={"R2_CODEC_LEDGER":str(spans)})
        ledger = byte_ledger(fixture,spans)
        ledger["provenance"] = {"frozen_codec_sha256":hashlib.sha256((self.clean/"crates/pqtc-stark/src/codec.rs").read_bytes()).hexdigest(),"instrumentation_patch_sha256":hashlib.sha256((self.out/"instrumentation.patch").read_bytes()).hexdigest(),"canonical_decode_and_native_verify_log":self.state["commands"][-1]["stdout"]}
        envelopes = {}
        for nonce,part in enumerate(("a","b")):
            calldata = (fixture/f"part-{part}.calldata").read_bytes()
            signed = self.run(label+"-unbroadcast-envelope-"+part,["cast","mktx",POOL,"0x"+calldata.hex(),"--legacy","--gas-limit",str(CAP),"--gas-price","0","--nonce",str(nonce),"--chain","31337","--private-key",PUBLIC_TEST_KEY,"--no-proxy"]).stdout.decode().strip()
            raw = bytes.fromhex(signed.removeprefix("0x"))
            (fixture/f"part-{part}.signed-unbroadcast.rlp").write_bytes(raw)
            sections = {**ledger["parts"][part]["abi_sections"],"rlp_envelope":len(raw)-len(calldata)}
            if sum(sections.values()) != len(raw):
                raise ValueError("signed transaction byte sections do not sum")
            envelopes[part] = {"signed_bytes":len(raw),"sections":sections,"broadcast":False,"nonce":nonce,"chain_id":31337,"intrinsic":intrinsic(calldata)}
        ledger["transaction_envelope"] = {"measurement_class":"MEASURED","bytes":sum(row["signed_bytes"] for row in envelopes.values()),"parts":envelopes,"note":"Actual public-test-key signed legacy RLP, retained unbroadcast; not a receipt or cap-feasibility claim"}
        write_json(fixture/"byte-ledger.json",ledger)
        self.run(label+"-complete-evm",["forge","test","--root",".","--match-test","testArbitraryGeneratedFixtureThroughCompletePoolCalls","-vvvv"],cwd=self.fork/BASELINE/"evm",env={"V03_FIXTURE_DIR":str(fixture)})
        return {"fixture":str(fixture),"native_verified":True,"canonical_decoder_verified":True,"complete_foundry_pool_calls":True,"raw_bytes":ledger["raw_bytes"],"abi_bytes":ledger["abi_bytes"]}

    def proofs(self):
        proofs = self.out/"proofs"
        proofs.mkdir(exist_ok=False)
        retained = proofs/"retained-v03-fixed-01"
        shutil.copytree(self.clean/BASELINE/"proofs/v03-fixed-01",retained)
        rows = [self.verify_fixture(retained,"retained")]
        corpus = ROOT/"research/r2/corpus/h0"
        if not corpus.is_dir():
            raise ValueError("run prepare-corpus first")
        jobs = json.loads((corpus/"jobs.json").read_text())["jobs"]
        varied = [job for job in jobs if job["kind"] == "semantic-corpus"][:5]
        if len(varied) != 5:
            raise ValueError("five varied depth20 witnesses required")
        selected = [{"input":"fixed","kind":"fixed-baseline"} for _ in range(5)] + varied
        seen = set()
        retained_ids = {json.loads(path.read_text())["proof_id"] for path in (self.clean/BASELINE/"proofs").glob("*/proof-metadata.json")}
        for i,job in enumerate(selected):
            fixture = proofs/f"fresh-{i+1:02d}"
            self.run(f"fresh-{i+1:02d}-prove",[self.binary(),"prove","--input",corpus/job["input"],"--out",fixture])
            metadata = json.loads((fixture/"proof-metadata.json").read_text())
            proof_id = metadata["proof_id"]
            if proof_id in seen or proof_id in retained_ids or not metadata["native_verified"] or not metadata["codec_roundtrip_verified"] or metadata["entropy_source"] != "operating-system entropy through pqtc_stark::withdrawal_config_from_os_entropy; no caller seed":
                raise ValueError("fresh OS-randomized proof/native verification gate failed")
            seen.add(proof_id)
            row = self.verify_fixture(fixture,f"fresh-{i+1:02d}")
            row.update({"kind":job["kind"],"input":str(corpus/job["input"]),"proof_id":proof_id,"synthetic":True,"funded":False})
            rows.append(row)
            self.state["proofs"] = rows
            self.save()
        self.state.update({"correctness_evidence":"integrated-tested: canonical native decode plus complete local Foundry pool calls","performance_evidence":"measured fresh proofs and complete Foundry calls; capped receipts separate","fresh_distinct_proofs":len(seen)})
        self.run("unrestricted-internal-deployment",["forge","test","--root",".","--match-test","testDeploymentInitcodeRuntimeAndCodeDepositGas","-vvvv"],cwd=self.fork/BASELINE/"evm")

    def local(self,rpc_url,fixture_name,diagnostic_url=None,local_id=None):
        rpc = RPC(rpc_url)
        label = local_id or fixture_name
        if any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in label):
            raise ValueError("local measurement ID must be a path-free identifier")
        out = self.out/"local"/label
        out.mkdir(parents=True,exist_ok=False)
        fork_evm = self.fork/BASELINE/"evm"
        catalog = source_catalog(fork_evm/"out",fork_evm)
        fixture = self.out/"proofs"/fixture_name
        if not fixture.is_dir():
            raise ValueError("selected fixture was not generated/retained by this run")
        prestate = out/"foundry-prestate.json"
        self.run("export-prestate",["forge","test","--root",".","--match-test","testExportFixturePrestate","-vv"],cwd=fork_evm,env={"V03_FIXTURE_DIR":str(fixture),"V03_PRESTATE_OUT":str(prestate)})
        # Snapshot isolates all test funding, etched fixtures and signed CREATEs.
        snapshot = rpc.call("evm_snapshot",[])
        try:
            rpc.call("anvil_setNextBlockBaseFeePerGas",["0x0"])
            rpc.call("anvil_setBalance",[SENDER,hex(100*10**18)])
            deployment_snapshot = rpc.call("evm_snapshot",[])
            deployments = []
            deployed = {}
            for contract in ("PQTCAirStageVerifier","PQTCQueryVerifier","PQTCVerificationRegistry","PQTCClassicPool"):
                matches = [a for a in catalog if a["contract"] == contract and a["kind"] == "bytecode"]
                if not matches:
                    raise ValueError(f"missing exact compiled {contract}")
                code = matches[-1]["code"]
                def word(address): return bytes.fromhex(address.removeprefix("0x").zfill(64))
                if contract == "PQTCVerificationRegistry":
                    code += word(deployed["PQTCAirStageVerifier"])+word(deployed["PQTCQueryVerifier"])+bytes.fromhex(PARAMETER)
                if contract == "PQTCClassicPool":
                    code += (10**18).to_bytes(32,"big")+bytes.fromhex(PARAMETER)+word(deployed["PQTCVerificationRegistry"])
                tx_out = out/("create-"+contract)
                result = send_signed(rpc,self.run,tx_out,"create-"+contract,code)
                runtime = [a for a in catalog if a["contract"] == contract and a["kind"] == "deployedBytecode"][-1]["code"]
                result["compiled_runtime_bytes"] = len(runtime)
                result["required_code_deposit_gas"] = len(runtime)*200
                result["initcode_bytes"] = len(code)
                result["initcode_limit_bytes"] = 49152
                result["runtime_limit_bytes"] = 24576
                if result.get("admission") == "MINED":
                    result["gas_ledger"] = attribute(tx_out,rpc,catalog,contract)
                deployments.append(result)
                write_json(out/"deployment-results.json",deployments)
                if not result.get("success"):
                    if contract != "PQTCClassicPool":
                        raise RuntimeError(f"dependency CREATE failed: {contract}; receipt retained")
                else:
                    deployed[contract] = result["contract_address"]
            if not rpc.call("evm_revert",[deployment_snapshot]):
                raise RuntimeError("failed to restore pre-deployment snapshot")
            load_prestate(rpc,prestate)
            rpc.call("anvil_setNextBlockBaseFeePerGas",["0x0"])
            transactions = self.sequence(rpc,out,fixture,catalog,"capped",CAP)
            unrestricted = []
            if diagnostic_url:
                if diagnostic_url == rpc_url:
                    raise ValueError("diagnostic endpoint must be distinct from capped endpoint")
                diagnostic = RPC(diagnostic_url)
                diagnostic_snapshot = diagnostic.call("evm_snapshot",[])
                try:
                    load_prestate(diagnostic,prestate)
                    diagnostic.call("anvil_setNextBlockBaseFeePerGas",["0x0"])
                    if not deployments[-1].get("success"):
                        constructor_snapshot = diagnostic.call("evm_snapshot",[])
                        original_create = out/"create-PQTCClassicPool"
                        request = json.loads((original_create/"request.json").read_text())
                        nonce = request["nonce"]
                        diagnostic.call("anvil_setNonce",[SENDER,hex(nonce)])
                        diagnostic_create = out/"create-PQTCClassicPool-high-gas-control"
                        diagnostic_result = send_signed(diagnostic,self.run,diagnostic_create,"constructor-high-gas-control",(original_create/"calldata.bin").read_bytes(),cap=48_000_000)
                        if diagnostic_result.get("admission") == "MINED":
                            diagnostic_result["gas_ledger"] = attribute(diagnostic_create,diagnostic,catalog,"PQTCClassicPool")
                        write_json(out/"constructor-diagnostic.json",{"result":diagnostic_result,"same_sender_nonce_chain_and_initcode":True,"physical_cap_feasibility":False,"purpose":"Complete constructor hashing/storage/code-deposit decomposition after capped failure"})
                        if not diagnostic.call("evm_revert",[constructor_snapshot]):
                            raise RuntimeError("failed to restore constructor diagnostic snapshot")
                    unrestricted = self.sequence(diagnostic,out,fixture,catalog,"high-gas-control",48_000_000)
                finally:
                    if not diagnostic.call("evm_revert",[diagnostic_snapshot]):
                        raise RuntimeError("failed to restore diagnostic snapshot")
            write_json(out/"transaction-results.json",{"capped":transactions,"high_gas_measurement_control":unrestricted,"control_is_cap_feasibility":False,"diagnostic_endpoint":diagnostic_url,"fixture_setup":"Foundry-exported etched ResearchFixturePool and synthetic balance; not evidence of deployability","constructor_measurement":"Separate actual top-level CREATE transactions with unchanged PQTCClassicPool constructor"})
            self.state.setdefault("local",{})[fixture_name] = str(out/"transaction-results.json")
        finally:
            if not rpc.call("evm_revert",[snapshot]):
                raise RuntimeError("failed to restore disposable local snapshot")

    def sequence(self,rpc,out,fixture,catalog,route,cap):
        statement = json.loads((fixture/"evm.json").read_text())
        addresses = {POOL,statement["recipient"],statement["relayer"]}
        before = {address:number(rpc.call("eth_getBalance",[address,"latest"])) for address in addresses}
        transactions = []
        for part in ("a","b"):
            tx_out = out/("part-"+part+"-"+route)
            result = send_signed(rpc,self.run,tx_out,"part-"+part+"-"+route,(fixture/f"part-{part}.calldata").read_bytes(),POOL,cap=cap)
            if result.get("admission") == "MINED":
                result["gas_ledger"] = attribute(tx_out,rpc,catalog)
            transactions.append(result)
            write_json(out/(route+"-transactions.json"),transactions)
            if not result.get("success"):
                break
        if len(transactions)==2 and all(x.get("success") for x in transactions):
            nullifier = statement["nullifier_hash"].removeprefix("0x")
            state = self.run("nullifier-after-"+route,["cast","call",POOL,"nullifiers(bytes32,bytes32)(bool)","0x"+nullifier[:64],"0x"+nullifier[64:],"--rpc-url",rpc.url,"--no-proxy"]).stdout.decode().strip()
            after = {address:number(rpc.call("eth_getBalance",[address,"latest"])) for address in addresses}
            expected = {address:0 for address in addresses}
            denomination,fee = int(statement["denomination_wei"]),int(statement["fee"])
            expected[POOL] -= denomination
            expected[statement["recipient"]] += denomination-fee
            expected[statement["relayer"]] += fee
            deltas = {address:after[address]-before[address] for address in addresses}
            registry = self.run("registry-address-"+route,["cast","call",POOL,"verificationRegistry()(address)","--rpc-url",rpc.url,"--no-proxy"]).stdout.decode().strip()
            verification_id = json.loads((fixture/"proof-metadata.json").read_text())["verification_id"]
            checkpoint = self.run("checkpoint-after-"+route,["cast","call",registry,"checkpoint(bytes32)(address,bytes32,bytes32,bytes32)",verification_id,"--rpc-url",rpc.url,"--no-proxy"]).stdout.decode().strip()
            checkpoint_cleared = all(int(value,16)==0 for value in checkpoint.split())
            write_json(out/(route+"-state.json"),{"nullifier_spent":state,"balance_before":before,"balance_after":after,"balance_deltas":deltas,"expected_deltas":expected,"checkpoint_raw":checkpoint,"checkpoint_cleared":checkpoint_cleared})
            if state != "true" or deltas != expected or not checkpoint_cleared:
                raise ValueError("complete transaction state/payout/checkpoint transition failed")
        return transactions

    def hashes(self):
        entries = []
        for path in sorted(self.out.rglob("*")):
            rel = path.relative_to(self.out)
            if not path.is_file() or any(part in {"checkout","cleanup-exclusion","instrumented","target-clean","target-instrumented"} for part in rel.parts) or path.name in {"artifact-hashes.json","results.json"}:
                continue
            digest = hashlib.sha256()
            with path.open("rb") as file:
                for block in iter(lambda:file.read(1024*1024),b""):
                    digest.update(block)
            entries.append({"path":str(rel),"bytes":path.stat().st_size,"sha256":digest.hexdigest()})
        write_json(self.out/"artifact-hashes.json",entries)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase",choices=("prepare","prepare-corpus","proofs","local"))
    parser.add_argument("--run-id",required=True)
    parser.add_argument("--rpc-url")
    parser.add_argument("--diagnostic-rpc-url")
    parser.add_argument("--fixture",default="retained-v03-fixed-01")
    parser.add_argument("--local-id")
    args = parser.parse_args()
    runner = Runner(args.run_id)
    if runner.state["phases"].get(args.phase) == "COMPLETE" and args.phase != "local":
        raise SystemExit("phase already complete; retained outputs are immutable")
    try:
        if args.phase == "local":
            if not args.rpc_url: raise ValueError("local phase requires --rpc-url")
            runner.local(args.rpc_url,args.fixture,args.diagnostic_rpc_url,args.local_id)
        else:
            getattr(runner,args.phase.replace("-","_"))()
        runner.state["phases"][args.phase] = "COMPLETE"
    except Exception as exc:
        runner.state["phases"][args.phase] = "EXECUTION_BLOCKED"
        runner.state.setdefault("errors",[]).append({"phase":args.phase,"error":str(exc),"traceback":traceback.format_exc(),"security_qualification_was_not_execution_gate":True})
        raise
    finally:
        runner.save()
        runner.hashes()
    print(runner.out/"results.json")


if __name__ == "__main__":
    main()
