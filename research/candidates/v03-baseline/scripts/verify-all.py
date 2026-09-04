#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, json, os, re, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
CAND=ROOT/"research/candidates/v03-baseline"
BIN=CAND/"native/target/release/v03-baseline-reproducer"
PROOFS=CAND/"proofs"
PREPARED=CAND/"vectors/derived"
RUNS=ROOT/"research/runs"
SUMMARY=ROOT/"research/summaries/v03-distribution.csv"
GAS=CAND/"gas/evm"
CAP=16_777_216

def schedule(data: bytes, execution: int):
    zero=data.count(0); nonzero=len(data)-zero; tokens=zero+4*nonzero
    standard_intrinsic=21_000+4*tokens; standard_total=standard_intrinsic+execution
    rows=[]
    for name,floor in [
      ("ACTIVE_EIP7623",21_000+10*tokens),
      ("SCENARIO_EIP7976_64_PER_BYTE",21_000+64*len(data)),
      ("SCENARIO_EIP8311_96_PER_BYTE",21_000+96*len(data))]:
        total=max(standard_total,floor)
        rows.append({"name":name,"floor_gas":floor,"total_gas":total,"tx_cap_margin":CAP-total,"floor_is_binding":floor>standard_total})
    return standard_intrinsic,rows

def metric(log: str, name: str) -> int:
    matches=re.findall(rf"{re.escape(name)}:\s*([0-9]+)",log)
    if not matches: raise SystemExit(f"Foundry output lacks {name}")
    return int(matches[-1])

parser=argparse.ArgumentParser(description="Verify every retained v0.3 proof natively and through the research-only pool harness")
parser.add_argument("--native-only",action="store_true",help="skip the expensive Foundry executions")
args=parser.parse_args()
if not BIN.exists(): subprocess.run(["cargo","build","--locked","--offline","--release","--manifest-path",str(CAND/"native/Cargo.toml")],cwd=ROOT,check=True)
jobs=json.loads((PREPARED/"jobs.json").read_text())["jobs"]
if len(jobs)!=60: raise SystemExit("expected exactly 60 jobs; run generate-all.py first")
status=json.loads((CAND/"status.json").read_text())
status.update({"native_verification":"NOT_EVALUATED","evm_verification":"NOT_EVALUATED","gate_status":"NOT_EVALUATED"})
(CAND/"status.json").write_text(json.dumps(status,indent=2,sort_keys=True)+"\n")
for job in jobs:
    subprocess.run([str(BIN),"verify","--input",str(PREPARED/job["input"]),"--proof",str(PROOFS/job["run_id"])],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
status.update({"native_verification":"PASS"})
(CAND/"status.json").write_text(json.dumps(status,indent=2,sort_keys=True)+"\n")
if args.native_only:
    print("native_verified=60 evm=NOT_EVALUATED")
    raise SystemExit(0)
GAS.mkdir(parents=True,exist_ok=True)
measured={}
forge_version=subprocess.run(["forge","--version"],cwd=CAND/"evm",text=True,capture_output=True,check=True).stdout.strip().splitlines()[0]
for job in jobs:
    fixture=f"../proofs/{job['run_id']}"
    result=subprocess.run(["forge","test","--root",".","--match-test","testArbitraryGeneratedFixtureThroughCompletePoolCalls","-vvvv"],cwd=CAND/"evm",text=True,capture_output=True,env={**os.environ,"V03_FIXTURE_DIR":fixture})
    log=result.stdout+result.stderr
    (GAS/f"{job['run_id']}.trace.log").write_text(log)
    if result.returncode:
        sys.stderr.write(log); raise SystemExit(f"EVM verification failed for {job['run_id']}")
    gas_a=metric(log,"V03_POOL_A_EXECUTION_GAS"); gas_b=metric(log,"V03_POOL_B_EXECUTION_GAS")
    calldata_a=(PROOFS/job["run_id"]/"part-a.calldata").read_bytes(); calldata_b=(PROOFS/job["run_id"]/"part-b.calldata").read_bytes()
    intrinsic_a, scenarios_a=schedule(calldata_a,gas_a); intrinsic_b,scenarios_b=schedule(calldata_b,gas_b)
    measured[job["run_id"]]={"a_execution":gas_a,"b_execution":gas_b,"a_total":scenarios_a[0]["total_gas"],"b_total":scenarios_b[0]["total_gas"]}
    run_path=RUNS/f"{job['run_id']}.json"; run=json.loads(run_path.read_text())
    run["protocol"]["transaction_shape"]="OTHER"
    run["evm"].update({"measured":True,"client":"Foundry local EVM","client_version":forge_version,"execution_gas":gas_a,"standard_intrinsic_gas":intrinsic_a,"receipt_gas_used":0,"transaction_gas_limit":CAP,"gas_scenarios":scenarios_a,"component_gas":{"pool_a_execution":gas_a,"pool_b_execution":gas_b,"pool_a_standard_intrinsic":intrinsic_a,"pool_b_standard_intrinsic":intrinsic_b},"part_b_gas_scenarios":scenarios_b,"measurement_status":"PASS: complete pool A/B calls; top-level receipt fields remain NOT_EVALUATED because Foundry test execution is not a mined transaction","receipt_status":"NOT_EVALUATED","runtime_status":"NOT_EVALUATED by this command; use measure-deployment.sh","opcode_status":"NOT_EVALUATED by this command; use opcode-profile.py"})
    run["result"]["notes"].append("Complete pool-facing A/B calls verified in Foundry; deployment and opcode gates remain NOT_EVALUATED")
    run_path.write_text(json.dumps(run,indent=2,sort_keys=True)+"\n")
(GAS/"README.txt").write_text("Each trace is raw Foundry -vvvv output for an exact retained calldata pair. It preserves call-level execution and is suitable as input to client/opcode trace tooling; it is not an opcode count. Unsupported aggregate opcode counts remain NOT_EVALUATED.\n")
with SUMMARY.open(newline="") as handle: rows=list(csv.DictReader(handle))
for row in rows:
    values=measured[row["run_id"]]; row.update({"evm_a_execution_gas":values["a_execution"],"evm_b_execution_gas":values["b_execution"],"evm_a_total_gas":values["a_total"],"evm_b_total_gas":values["b_total"],"evm_status":"PASS"})
with SUMMARY.open("w",newline="") as handle:
    writer=csv.DictWriter(handle,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
status=json.loads((CAND/"status.json").read_text()); status.update({"native_verification":"PASS","evm_verification":"PASS","gate_status":"NOT_EVALUATED"}); (CAND/"status.json").write_text(json.dumps(status,indent=2,sort_keys=True)+"\n")
if (CAND/"gas/deployment-profile.log").is_file() and (CAND/"gas/deposit-profile.log").is_file():
    subprocess.run([sys.executable,str(CAND/"scripts/synthesize-measurements.py")],cwd=ROOT,check=True)
print("native_verified=60 evm_pool_A_B_verified=60 traces=60")
