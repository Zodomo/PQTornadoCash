#!/usr/bin/env python3
from __future__ import annotations
import csv, hashlib, json, os, platform, re, shutil, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
CAND=ROOT/"research/candidates/v03-baseline"
NATIVE=CAND/"native"
PREPARED=CAND/"vectors/derived"
PROOFS=CAND/"proofs"
RUNS=ROOT/"research/runs"
SUMMARY=ROOT/"research/summaries/v03-distribution.csv"
BIN=NATIVE/"target/release/v03-baseline-reproducer"
BASELINE="00f829001999ee66da6fd5161c4c205c07d0b937"

def call(args, **kw): return subprocess.run(args,cwd=ROOT,check=True,text=True,**kw)
def version(args):
    try: return subprocess.run(args,cwd=ROOT,text=True,capture_output=True,check=True).stdout.strip().splitlines()[0]
    except Exception: return "NOT_EVALUATED: tool unavailable"
def hardware():
    logical=os.cpu_count() or 1; physical=logical; ram=1
    if sys.platform=="darwin":
        def sysctl(name,default):
            try:return subprocess.run(["sysctl","-n",name],text=True,capture_output=True,check=True).stdout.strip()
            except Exception:return default
        physical=int(sysctl("hw.physicalcpu",str(logical))); ram=int(sysctl("hw.memsize","1")); cpu=sysctl("machdep.cpu.brand_string",platform.processor() or "unknown")
    else:
        cpu=platform.processor() or "unknown"
        try: ram=os.sysconf("SC_PAGE_SIZE")*os.sysconf("SC_PHYS_PAGES")
        except (ValueError,OSError,AttributeError): pass
    return {"hardware_id":f"{platform.node()}-{platform.machine()}","cpu_model":cpu,"physical_cores":max(1,physical),"logical_cores":max(1,logical),"ram_bytes":max(1,ram),"os":platform.platform(),"kernel":platform.release(),"architecture":platform.machine(),"cpu_features":[],"threads_used":max(1,logical),"allocator":None,"power_mode":None,"cpu_affinity":None}

def measured_run(args):
    timer=Path("/usr/bin/time")
    cmd=args; mode=None
    if timer.exists():
        mode="darwin" if sys.platform=="darwin" else "gnu"
        cmd=[str(timer),"-l" if mode=="darwin" else "-v",*args]
    started=time.perf_counter(); result=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True); wall=(time.perf_counter()-started)*1000
    if result.returncode:
        sys.stderr.write(result.stdout+result.stderr); raise subprocess.CalledProcessError(result.returncode,cmd)
    rss=None
    if mode=="darwin":
        match=re.search(r"(\d+)\s+maximum resident set size",result.stderr); rss=int(match.group(1)) if match else None
    elif mode=="gnu":
        match=re.search(r"Maximum resident set size \(kbytes\):\s*(\d+)",result.stderr); rss=int(match.group(1))*1024 if match else None
    return wall,rss

def artifact(run_dir,name,key,media,description,meta):
    value=meta[key]; data=(run_dir/name).read_bytes()
    return {"path":str((run_dir/name).relative_to(ROOT)),"bytes":value["bytes"],"media_type":media,"digests":{"sha256":hashlib.sha256(data).hexdigest(),"keccak256":value["keccak256"]},"description":description}

def run_record(job,run_dir,meta,wall,rss,hw,tools):
    evm=json.loads((run_dir/"evm.json").read_text())
    case_id=job.get("case_id","fixed-baseline")
    artifacts=[
      artifact(run_dir,"statement.json","statement","application/json","Exact v0.3 public statement input",meta),
      artifact(run_dir,"witness.json","witness","application/json","Exact synthetic benchmark private witness; never production material",meta),
      artifact(run_dir,"derived-case.json","derived_case","application/json","Candidate derivation with original semantic source case",meta),
      artifact(run_dir,"mapping.json","mapping","application/json","Explicit rejection-sampling record",meta),
      artifact(run_dir,"part-a.pqtc","part_a","application/octet-stream","Canonical proof part A",meta),
      artifact(run_dir,"part-b.pqtc","part_b","application/octet-stream","Canonical proof part B",meta),
      artifact(run_dir,"part-a.calldata","calldata_a","application/vnd.ethereum.calldata","Exact beginWithdrawal calldata for the fixed research harness address",meta),
      artifact(run_dir,"part-b.calldata","calldata_b","application/vnd.ethereum.calldata","Exact withdraw calldata including consumer-bound verification ID",meta),
    ]
    null_reason="NOT_EVALUATED: EVM execution is performed by verify-all.sh after proof generation; schema-required numeric fields use zero only as an explicit unmeasured sentinel"
    scenarios=[{"name":name,"floor_gas":0,"total_gas":0,"tx_cap_margin":0,"floor_is_binding":False} for name in ["ACTIVE_EIP7623","SCENARIO_EIP7976_64_PER_BYTE","SCENARIO_EIP8311_96_PER_BYTE"]]
    return {
      "schema_version":"1","run_id":job["run_id"],"candidate_id":"C00/v03-baseline","spike_id":"SP-00","timestamp_utc":datetime.now(timezone.utc).isoformat(),
      "git":{"repository":str(ROOT),"commit":BASELINE,"dirty":bool(subprocess.run(["git","status","--porcelain","--untracked-files=no"],cwd=ROOT,text=True,capture_output=True,check=True).stdout.strip()),"branch_or_tag":"pqtc-v0.3-research-baseline","submodules":{}},
      "toolchain":{**tools,"plonky3_commit":"3152b14a89067c83775a8076cc262ffc48a1fd7c"},"hardware":hw,
      "protocol":{"semantic_version":"3","asset":"native ETH","denomination_wei":evm["denomination_wei"],"tree_depth":20,"tree_arity":2,"case_id":case_id,"transaction_shape":"NATIVE_ONLY","semantic_source_kind":job["kind"]},
      "application_hash":{"candidate":"P2BB512-v1","family":"Poseidon2","field":"BabyBear","mode":"rate-4 sponge","state_width":16,"rate":4,"capacity":12,"digest_fields":16,"digest_bytes":64,"domain_scheme":"v0.3 typed tags plus byte/element length and aux","review_status":"independent structural cryptanalysis outstanding"},
      "relation":{"kind":"AIR","logical_rows":256,"padded_rows":256,"trace_width":190,"constraint_count":1186,"max_degree":7,"quotient_chunks":16,"batched_functions":210,"base_degree_bits":8,"hiding_degree_bits":9,"active_rows":244,"padding_rows":12,"nonzero_count_status":"NOT_EVALUATED: frozen AIR does not expose this count"},
      "proof_system":{"name":"Plonky3 hiding two-adic FRI STARK q32","base_field":"BabyBear","challenge_field":"degree-4 BabyBear extension","challenge_field_bits":120,"pcs_or_ldt":"hiding two-adic FRI","hiding":True,"hiding_construction":"four random codewords and eight MMCS salt fields per leaf","trusted_setup":False,"classical_wrapper":False,"query_count":32,"log_blowup":4,"fold_schedule":"nine binary rounds","final_polynomial_length":1,"commit_grinding_bits_configured":16,"query_grinding_bits_configured":16,"random_codewords":4,"salt_fields":8,"transcript":"KeccakPair512","mmcs_digest_bytes":64},
      "security":{"classification":"PQ_ORIENTED_RESEARCH","terms":[
        {"name":"FRI random-words","model":"generated v0.3 conjecture","formula_source":"parameters/sepolia-v0.3/security-analysis.json","classical_bits":107,"quantum_bits":None,"proven_or_conjectural":"CONJECTURAL","multi_target_count_log2":None,"binding":False,"omitted_terms":["unbounded multi-target proof volume"],"notes":["Not a proven 100-bit claim"]},
        {"name":"FRI best proven","model":"list decoding","formula_source":"parameters/sepolia-v0.3/security-analysis.json","classical_bits":56,"quantum_bits":None,"proven_or_conjectural":"PROVEN","multi_target_count_log2":None,"binding":True,"omitted_terms":[],"notes":["Unique-decoding bound is 37 bits"]}],
        "lowest_accepted_bits":56,"qrom_status":"No complete QROM proof for custom transcript/composition","zk_status":"Hiding enabled; full independent ZK proof outstanding","external_review":None},
      "prover":{"success":True,"cold_or_warm":"WARM","wall_ms":wall,"cpu_ms":None,"peak_rss_bytes":rss,"native_verify_ms":meta["native_verify_ms"],"proof_only_ms":meta["prove_ms"],"peak_rss_status":None if rss is not None else "NOT_EVALUATED: /usr/bin/time RSS unsupported on this platform"},
      "proof_bytes":{"raw_proof_bytes":meta["raw_proof_bytes"],"abi_calldata_bytes":meta["abi_calldata_bytes"],"zero_bytes":meta["zero_bytes"],"nonzero_bytes":meta["nonzero_bytes"],"unique_query_indices":meta["unique_query_indices"],"sections":meta["sections"],"frontier_status":meta["frontier_status"],"calldata_zero_bytes":meta["calldata_zero_bytes"],"calldata_nonzero_bytes":meta["calldata_nonzero_bytes"]},
      "evm":{"measured":False,"client":"NOT_EVALUATED","client_version":"NOT_EVALUATED","chain_config_hash":None,"execution_gas":0,"standard_intrinsic_gas":0,"receipt_gas_used":0,"transaction_gas_limit":0,"gas_scenarios":scenarios,"runtime_bytes":0,"initcode_bytes":0,"deployment_gas":0,"component_gas":{},"opcode_counts":{},"transaction_hash":None,"receipt_block":None,"measurement_status":null_reason},
      "artifacts":artifacts,"result":{"success":True,"gate_status":"NOT_EVALUATED","failure_reason":None,"confounders":["EVM and deployment measurements have not run","valid-proof maximum frontier/gas is unproven"],"notes":["Native proof and codec round trip verified","OS hiding entropy used","Synthetic benchmark secrets are intentionally published and must never be reused"]}
    }
def main():
    call([sys.executable,str(CAND/"scripts/verify-report-inventory.py")])
    status=json.loads((CAND/"status.json").read_text())
    status.update({"parameter_regeneration":"PASS","proof_generation":"NOT_EVALUATED","native_verification":"NOT_EVALUATED","evm_verification":"NOT_EVALUATED","gate_status":"NOT_EVALUATED"})
    (CAND/"status.json").write_text(json.dumps(status,indent=2,sort_keys=True)+"\n")
    call(["cargo","build","--locked","--offline","--release","--manifest-path",str(NATIVE/"Cargo.toml")])
    if PREPARED.exists(): shutil.rmtree(PREPARED)
    call([str(BIN),"prepare","--corpus",str(ROOT/"research/common-corpus/semantic-cases.json"),"--out",str(PREPARED)])
    jobs=json.loads((PREPARED/"jobs.json").read_text())["jobs"]
    PROOFS.mkdir(parents=True,exist_ok=True); RUNS.mkdir(parents=True,exist_ok=True); SUMMARY.parent.mkdir(parents=True,exist_ok=True)
    for old in PROOFS.glob("v03-*"): shutil.rmtree(old)
    for old in RUNS.glob("v03-*.json"): old.unlink()
    hw=hardware(); tools={"rustc":version(["rustc","--version"]),"cargo":version(["cargo","--version"]),"solc":version(["solc","--version"]),"foundry":version(["forge","--version"]),"node":version(["node","--version"]),"package_manager":version(["pnpm","--version"]),"evm_revision":"Prague","rustflags":[],"solc_optimizer_runs":1,"via_ir":True,"container_image_digest":None}
    rows=[]; fixed_digests=set()
    for job in jobs:
        input_dir=PREPARED/job["input"]; run_dir=PROOFS/job["run_id"]
        if run_dir.exists(): shutil.rmtree(run_dir)
        wall,rss=measured_run([str(BIN),"prove","--input",str(input_dir),"--out",str(run_dir)])
        meta=json.loads((run_dir/"proof-metadata.json").read_text())
        if job["kind"]=="fixed-baseline":
            fingerprint=hashlib.sha256((run_dir/"part-a.pqtc").read_bytes()+(run_dir/"part-b.pqtc").read_bytes()).hexdigest()
            if fingerprint in fixed_digests: raise SystemExit("fresh hiding proofs collided byte-for-byte")
            fixed_digests.add(fingerprint)
        record=run_record(job,run_dir,meta,wall,rss,hw,tools)
        (RUNS/f"{job['run_id']}.json").write_text(json.dumps(record,indent=2,sort_keys=True)+"\n")
        rows.append({"candidate_id":"C00/v03-baseline","run_id":job["run_id"],"kind":job["kind"],"case_id":job.get("case_id","fixed-baseline"),"prove_wall_ms":f"{wall:.6f}","proof_only_ms":f"{meta['prove_ms']:.6f}","native_verify_ms":f"{meta['native_verify_ms']:.6f}","peak_rss_bytes":"" if rss is None else rss,"raw_proof_bytes":meta["raw_proof_bytes"],"abi_calldata_bytes":meta["abi_calldata_bytes"],"zero_bytes":meta["zero_bytes"],"nonzero_bytes":meta["nonzero_bytes"],"unique_query_indices":meta["unique_query_indices"],"frontier_digests":"NOT_EVALUATED","evm_a_execution_gas":"","evm_b_execution_gas":"","evm_a_total_gas":"","evm_b_total_gas":"","evm_status":"NOT_EVALUATED"})
    if len(fixed_digests)!=30: raise SystemExit("fixed proof count/freshness check failed")
    with SUMMARY.open("w",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    status=json.loads((CAND/"status.json").read_text())
    status.update({"parameter_regeneration":"PASS","proof_generation":"PASS","native_verification":"PASS","evm_verification":"NOT_EVALUATED","gate_status":"NOT_EVALUATED"})
    (CAND/"status.json").write_text(json.dumps(status,indent=2,sort_keys=True)+"\n")
    print("generated=60 fixed_fresh=30 corpus_distinct=30 native_verified=60 evm=NOT_EVALUATED")
if __name__=="__main__": main()
