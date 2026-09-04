#!/usr/bin/env python3
"""Deterministically reconcile retained v0.3 runs, traces, and deployment logs."""
from __future__ import annotations
import collections, csv, json, math, re, statistics
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
CAND=ROOT/"research/candidates/v03-baseline"
RUNS=ROOT/"research/runs"
SUMMARY=ROOT/"research/summaries/v03-distribution.csv"
TRACE_DIR=CAND/"gas/evm"
DEPLOY_LOG=CAND/"gas/deployment-profile.log"
OUT=CAND/"gas/measured-summary.json"
DEPOSIT_LOG=CAND/"gas/deposit-profile.log"
CAP=16_777_216
EIP170=24_576
EIP3860=49_152
REPORT={"a_execution":14_891_070,"a_total":16_539_302,"b_execution":12_356_373,"b_total":14_105_909,"deposit_execution":13_991_021}
FIELDS={"prove_wall_ms":"prove_wall_ms","proof_only_ms":"proof_only_ms","native_verify_ms":"native_verify_ms","peak_rss_bytes":"peak_rss_bytes","raw_proof_bytes":"raw_proof_bytes","abi_calldata_bytes":"abi_calldata_bytes","zero_bytes":"zero_bytes","nonzero_bytes":"nonzero_bytes","unique_query_indices":"unique_query_indices","a_execution":"evm_a_execution_gas","b_execution":"evm_b_execution_gas","a_total":"evm_a_total_gas","b_total":"evm_b_total_gas"}

def percentile(values:list[float],p:float)->float:
    ordered=sorted(values)
    if len(ordered)==1:return ordered[0]
    position=(len(ordered)-1)*p; lower=math.floor(position); upper=math.ceil(position)
    return ordered[lower] if lower==upper else ordered[lower]+(ordered[upper]-ordered[lower])*(position-lower)

def distribution(values:list[float|int])->dict:
    numbers=[float(v) for v in values]
    def clean(value:float): return int(value) if value.is_integer() else value
    return {"count":len(numbers),"min":clean(min(numbers)),"max":clean(max(numbers)),"mean":clean(statistics.fmean(numbers)),"stddev":clean(statistics.pstdev(numbers)),"p50":clean(percentile(numbers,.50)),"p90":clean(percentile(numbers,.90)),"p95":clean(percentile(numbers,.95)),"p99":clean(percentile(numbers,.99))}

def trace_metric(text:str,name:str)->int:
    found=re.findall(rf"{re.escape(name)}:\s*([0-9]+)",text)
    if len(found)!=1: raise SystemExit(f"expected one {name}, found {len(found)}")
    return int(found[0])

def parse_deployment(text:str)->dict:
    names=re.findall(r"V03_DEPLOY_CONTRACT:\s*(\w+)",text)
    metrics={label:[int(v) for v in re.findall(rf"{label}:\s*([0-9]+)",text)] for label in ["V03_DEPLOY_INITCODE_BYTES","V03_DEPLOY_RUNTIME_BYTES","V03_DEPLOY_CODE_DEPOSIT_GAS","V03_DEPLOY_OBSERVED_NEW_EXPRESSION_GAS","V03_DEPLOY_CONSTRUCTOR_EXECUTION_GAS_NOT_SEPARATELY_OBSERVABLE"]}
    if len(names)!=4 or any(len(v)!=4 for v in metrics.values()): raise SystemExit("deployment log does not contain four complete records")
    records={}
    for index,name in enumerate(names):
        initcode=metrics["V03_DEPLOY_INITCODE_BYTES"][index]; runtime=metrics["V03_DEPLOY_RUNTIME_BYTES"][index]; deposit=metrics["V03_DEPLOY_CODE_DEPOSIT_GAS"][index]; observed=metrics["V03_DEPLOY_OBSERVED_NEW_EXPRESSION_GAS"][index]
        if deposit!=runtime*200: raise SystemExit(f"{name} code-deposit gas mismatch")
        records[name]={"initcode_bytes":initcode,"runtime_bytes":runtime,"code_deposit_gas":deposit,"observed_internal_new_expression_gas":observed,"constructor_execution_gas":None,"constructor_execution_status":"NOT_SEPARATELY_OBSERVABLE","eip170_runtime_limit":EIP170,"eip170_status":"PASS" if runtime<=EIP170 else "FAIL","eip3860_initcode_limit":EIP3860,"eip3860_status":"PASS" if initcode<=EIP3860 else "FAIL","eip3860_initcode_word_gas":2*math.ceil(initcode/32),"internal_new_vs_eip7825_margin":CAP-observed,"top_level_deployment_status":"NOT_EVALUATED: no creation transaction/receipt and initcode zero/nonzero byte distribution is absent"}
    return records

def replace_section(text:str,heading:str,next_heading:str,body:str)->str:
    start=text.index(heading); end=text.index(next_heading,start)
    return text[:start]+heading+"\n\n"+body.rstrip()+"\n\n"+text[end:]

run_paths=sorted(RUNS.glob("v03-*.json"))
trace_paths=sorted(TRACE_DIR.glob("v03-*.trace.log"))
if len(run_paths)!=60 or len(trace_paths)!=60: raise SystemExit(f"expected 60 runs/traces, got {len(run_paths)}/{len(trace_paths)}")
if {p.stem for p in run_paths}!={p.name.removesuffix(".trace.log") for p in trace_paths}: raise SystemExit("run/trace ID sets differ")
deploy=parse_deployment(DEPLOY_LOG.read_text())
pool_deploy=deploy["PQTCClassicPool"]
records=[]
deposit_text=DEPOSIT_LOG.read_text()
deposit_matches=re.findall(r"deposit execution gas:\s*([0-9]+)",deposit_text)
if "[PASS] testDepositFitsOneTransactionGasGate()" not in deposit_text or deposit_matches!=[str(REPORT["deposit_execution"])]: raise SystemExit("deposit profile does not match the report's exact passing measurement")
t8n_paths=sorted((CAND/"gas/t8n").glob("*/evidence.json"))
t8n_evidence=[json.loads(path.read_text()) for path in t8n_paths]
for evidence in t8n_evidence:
    if len(evidence.get("receipts",[]))!=2 or any(receipt.get("status")!=1 for receipt in evidence["receipts"]) or not evidence.get("opcode_profiles"): raise SystemExit(f"incomplete t8n evidence: {evidence.get('run_id')}")
t8n_failure_paths=sorted((CAND/"gas/t8n").glob("*/failure-evidence.json"))
t8n_failures=[json.loads(path.read_text()) for path in t8n_failure_paths]
for evidence in t8n_failures:
    if evidence.get("outcome")!="FAIL" or not any(receipt.get("status")!=1 for receipt in evidence.get("receipts",[])): raise SystemExit(f"invalid t8n failure evidence: {evidence.get('run_id')}")
raw_opcode_status="PASS_T8N_SIMULATION" if t8n_evidence else "NOT_EVALUATED"
second_client_status="PASS_T8N_SIMULATION_NOT_MINED" if t8n_evidence else "NOT_EVALUATED"
opcode_totals=collections.Counter()
for evidence in t8n_evidence:
    for profile in evidence["opcode_profiles"]: opcode_totals.update(profile["opcode_counts"])
for path in run_paths:
    run=json.loads(path.read_text()); run_id=run["run_id"]
    if run["candidate_id"]!="C00/v03-baseline": raise SystemExit(f"candidate mismatch: {path}")
    trace=(TRACE_DIR/f"{run_id}.trace.log").read_text()
    if "[PASS] testArbitraryGeneratedFixtureThroughCompletePoolCalls()" not in trace: raise SystemExit(f"missing Foundry PASS: {run_id}")
    a=trace_metric(trace,"V03_POOL_A_EXECUTION_GAS"); b=trace_metric(trace,"V03_POOL_B_EXECUTION_GAS")
    ia=trace_metric(trace,"V03_POOL_A_STANDARD_INTRINSIC_GAS"); ib=trace_metric(trace,"V03_POOL_B_STANDARD_INTRINSIC_GAS")
    if a!=run["evm"]["component_gas"]["pool_a_execution"] or b!=run["evm"]["component_gas"]["pool_b_execution"] or ia!=run["evm"]["component_gas"]["pool_a_standard_intrinsic"] or ib!=run["evm"]["component_gas"]["pool_b_standard_intrinsic"]: raise SystemExit(f"run/trace gas mismatch: {run_id}")
    a_total=run["evm"]["gas_scenarios"][0]["total_gas"]; b_total=run["evm"]["part_b_gas_scenarios"][0]["total_gas"]
    run["evm"].update({"runtime_bytes":pool_deploy["runtime_bytes"],"initcode_bytes":pool_deploy["initcode_bytes"],"deployment_gas":0,"deployment_gas_status":pool_deploy["top_level_deployment_status"],"internal_create_observed_gas":pool_deploy["observed_internal_new_expression_gas"],"code_deposit_gas":pool_deploy["code_deposit_gas"],"eip170_status":pool_deploy["eip170_status"],"eip3860_status":pool_deploy["eip3860_status"],"opcode_status":raw_opcode_status,"second_client_status":second_client_status,"receipt_status":"SIMULATION_ONLY: no mined receipt","deposit_status":"PASS_EXACT_REPORT_MATCH","deposit_execution_gas":REPORT["deposit_execution"]})
    run["result"].update({"gate_status":"FAIL","failure_reason":"Nine of 60 valid fresh part-A transactions exceed the EIP-7825 cap; top-level pool deployment and mined-receipt evidence remain incomplete."})
    run["result"]["confounders"]=["The 60-run maximum is empirical, not a formal valid-proof frontier/gas bound","No mined receipt","Top-level creation transaction gas is NOT_EVALUATED"]+(["Second-client and raw opcode counts are NOT_EVALUATED"] if not t8n_evidence else [])
    generated_notes={"Complete pool-facing A/B simulation passed in Foundry","Deployment code/initcode sizes and internal new-expression gas were measured separately","Candidate gate fails on observed EIP-7825 part-A violations","Deposit execution gas exactly matches the report"}
    base_notes=[note for note in run["result"]["notes"] if "EVM and deployment" not in note and "deployment and opcode gates" not in note and note not in generated_notes]
    run["result"]["notes"]=base_notes+sorted(generated_notes)
    path.write_text(json.dumps(run,indent=2,sort_keys=True)+"\n")
    records.append({"candidate_id":"C00/v03-baseline","run_id":run_id,"kind":run["protocol"]["semantic_source_kind"],"case_id":run["protocol"]["case_id"],"prove_wall_ms":run["prover"]["wall_ms"],"proof_only_ms":run["prover"]["proof_only_ms"],"native_verify_ms":run["prover"]["native_verify_ms"],"peak_rss_bytes":run["prover"]["peak_rss_bytes"],"raw_proof_bytes":run["proof_bytes"]["raw_proof_bytes"],"abi_calldata_bytes":run["proof_bytes"]["abi_calldata_bytes"],"zero_bytes":run["proof_bytes"]["zero_bytes"],"nonzero_bytes":run["proof_bytes"]["nonzero_bytes"],"unique_query_indices":run["proof_bytes"]["unique_query_indices"],"frontier_digests":"NOT_EVALUATED","evm_a_execution_gas":a,"evm_b_execution_gas":b,"evm_a_total_gas":a_total,"evm_b_total_gas":b_total,"evm_a_eip7825_status":"PASS" if a_total<=CAP else "FAIL","evm_b_eip7825_status":"PASS" if b_total<=CAP else "FAIL","evm_status":"PASS","gate_status":"FAIL"})

stats={name:distribution([row[field] for row in records]) for name,field in FIELDS.items()}
report_comparison={}
for name,field in [("part_a_execution","a_execution"),("part_a_total","a_total"),("part_b_execution","b_execution"),("part_b_total","b_total")]:
    median=stats[field]["p50"]; report=REPORT[field]; delta=median-report; percent=delta/report*100
    report_comparison[name]={"engineering_report":report,"reproduced_p50":median,"reproduced_min":stats[field]["min"],"reproduced_max":stats[field]["max"],"delta":delta,"delta_percent":percent,"within_one_percent":abs(percent)<=1}
summary={"candidate_id":"C00/v03-baseline","gate_status":"FAIL","run_count":60,"native_pass_count":60,"foundry_ab_pass_count":60,"part_a_eip7825_fail_count":sum(row["evm_a_eip7825_status"]=="FAIL" for row in records),"part_b_eip7825_fail_count":sum(row["evm_b_eip7825_status"]=="FAIL" for row in records),"distribution_method":"population stddev; percentiles use linear interpolation at (n-1)*p","distributions":stats,"report_comparison":report_comparison,"report_deposit_execution_gas":REPORT["deposit_execution"],"reproduced_deposit_execution_gas":REPORT["deposit_execution"],"deposit_delta_gas":0,"deposit_delta_percent":0.0,"deposit_measurement_status":"PASS_EXACT_REPORT_MATCH","deployment":deploy,"raw_opcode_counts_status":raw_opcode_status,"raw_opcode_totals":dict(sorted(opcode_totals.items())) if t8n_evidence else None,"second_client_status":second_client_status,"t8n_evidence_paths":[str(path.relative_to(ROOT)) for path in t8n_paths],"top_level_deployment_status":pool_deploy["top_level_deployment_status"],"failure_reasons":["9/60 valid part-A transactions exceed EIP-7825","pool internal new-expression gas exceeds 2^24, while top-level creation remains unmeasured","top-level creation and mined-receipt evidence remain incomplete"]}
summary["t8n_failed_simulations"]=[{"run_id":evidence["run_id"],"receipts":evidence["receipts"]} for evidence in t8n_failures]
OUT.write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
columns=list(records[0])
with SUMMARY.open("w",newline="") as handle:
    writer=csv.DictWriter(handle,fieldnames=columns); writer.writeheader(); writer.writerows(records)

status=json.loads((CAND/"status.json").read_text())
status.update({"gate_status":"FAIL","parameter_regeneration":"PASS","proof_generation":"PASS","native_verification":"PASS","evm_verification":"PASS","deployment_gas":"INTERNAL_CREATE_MEASURED; TOP_LEVEL_NOT_EVALUATED","deployment_code_size_gates":"PASS_EIP170_AND_EIP3860","opcode_profile":"COMPONENT_PROFILE_PASS; "+raw_opcode_status,"second_client":second_client_status,"deposit":"PASS_EXACT_REPORT_MATCH","part_a_eip7825":"FAIL_9_OF_60","part_b_eip7825":"PASS_60_OF_60","blocked":True,"gate_failure_reason":"Nine valid fresh part-A calls exceed 16,777,216 gas; missing top-level deployment/mined-receipt evidence cannot reverse this observed failure."})
t8n_failure_note="Pinned geth t8n also rejects retained v03-fixed-01 under the transaction cap; structured failure evidence is retained."
status["negative_results"]=[note for note in status.get("negative_results",[]) if note!=t8n_failure_note]+([t8n_failure_note] if t8n_failures else [])
(CAND/"status.json").write_text(json.dumps(status,indent=2,sort_keys=True)+"\n")

d=CAND/"deployment-gas.md"; deployment_rows="\n".join(f"| `{name}` | {v['initcode_bytes']:,} | {v['runtime_bytes']:,} | {v['code_deposit_gas']:,} | {v['observed_internal_new_expression_gas']:,} | {v['eip170_status']} | {v['eip3860_status']} | {v['internal_new_vs_eip7825_margin']:,} |" for name,v in deploy.items())
d.write_text("# C00 deployment gas\n\n**Measured component status: FAIL for the pool's internal EIP-7825 comparison; top-level deployment remains NOT_EVALUATED.** Source: retained `gas/deployment-profile.log`, Solc 0.8.30 / Foundry 1.7.1.\n\n| Contract | Initcode bytes | Runtime bytes | Exact code-deposit gas | Observed internal `new` gas | EIP-170 | EIP-3860 | Margin vs 2^24 |\n|---|---:|---:|---:|---:|---|---|---:|\n"+deployment_rows+"\n\nAll four runtimes are at most 24,576 bytes (EIP-170) and all four initcodes are at most 49,152 bytes (EIP-3860). Code-deposit gas is exact at 200 gas/runtime byte. EIP-3860 word metering is retained in `gas/measured-summary.json`. Constructor execution gas is not separately observable in this harness.\n\nThe pool's observed internal Solidity `new` expression used 18,873,630 gas, 2,096,414 above 16,777,216. This is a real local internal-CREATE measurement and a deployment blocker. It is **not** a mined creation receipt or an exact top-level creation-transaction total: initcode zero/nonzero byte counts, top-level intrinsic gas, and a receipt are absent. Those top-level fields remain `NOT_EVALUATED`, rather than being inferred.\n")

o=CAND/"opcode-profile.md"
opcode_detail=(f"go-ethereum t8n evidence is retained for {len(t8n_evidence)} passing fixture(s), with two sequential successful simulated receipts per fixture and {sum(opcode_totals.values()):,} aggregated opcode steps. The pinned client identity and per-transaction opcode maps are retained in each `gas/t8n/*/evidence.json`. {len(t8n_failures)} additional capped simulation failure(s) remain visible in `failure-evidence.json`; they do not weaken the candidate's FAIL gate. Raw multi-gigabyte JSONL is deleted only after deterministic aggregation. These are deterministic Prague state-transition simulations, not mined receipts." if t8n_evidence else "`gas/opcode-counts.json` and `gas/t8n/*/evidence.json` are absent; no raw opcode count has been accepted. `run-geth-t8n.sh` is the pinned sequential-state route.")
o.write_text(f"""# C00 opcode and component profile

**Component status: PASS for 60 Foundry A/B simulations. Raw opcode-count status: {raw_opcode_status}.**

The retained `gas/evm/v03-*.trace.log` set contains 60 complete call traces. Every trace records a passing pool-facing A/B execution, and the synthesizer byte-checks the four gas values against its run JSON. Part A execution ranges from {stats['a_execution']['min']:,} to {stats['a_execution']['max']:,} gas (p50 {stats['a_execution']['p50']:,}); part B ranges from {stats['b_execution']['min']:,} to {stats['b_execution']['max']:,} (p50 {stats['b_execution']['p50']:,}).

{opcode_detail}

Foundry traces are component evidence. t8n receipts are simulated state-transition receipts. Neither is represented as a mined network receipt.
""")

adr_path=CAND/"ADR.md"
adr=adr_path.read_text()
measured_body=f"""Sixty fresh q32 proofs were generated and verified natively; all 60 exact calldata pairs passed the complete Foundry pool-facing A/B simulation. Part-A total gas ranges {stats['a_total']['min']:,}–{stats['a_total']['max']:,} with p50 {stats['a_total']['p50']:,}; part B ranges {stats['b_total']['min']:,}–{stats['b_total']['max']:,} with p50 {stats['b_total']['p50']:,}. Nine part-A samples exceed 16,777,216; no part-B sample does.

Against the report, p50 deltas are {report_comparison['part_a_execution']['delta_percent']:.3f}% (A execution), {report_comparison['part_a_total']['delta_percent']:.3f}% (A total), {report_comparison['part_b_execution']['delta_percent']:.3f}% (B execution), and {report_comparison['part_b_total']['delta_percent']:.3f}% (B total). The B-total delta exceeds 1%. The exact cause is not isolated: fresh query/calldata variation and current harness/compiler instrumentation both differ from the single report fixture, so no stronger attribution is made. Reproduced deposit execution gas is exactly 13,991,021, matching the report.

Deployment profiling establishes EIP-170/EIP-3860 code-size passes. Pool internal `new` gas is 18,873,630, above 2^24; exact top-level creation transaction gas remains NOT_EVALUATED. Raw opcode status is {raw_opcode_status}; second-client status is {second_client_status}. Any t8n receipt is explicitly a simulation, not mined evidence."""
adr=replace_section(adr,"## Measurements","## Gate result",measured_body)
gate_body="`FAIL`. Native, deposit, and Foundry correctness passed, but 9/60 observed valid part-A transactions exceed EIP-7825. Missing top-level creation and mined-receipt evidence remain visible and cannot convert an observed cap failure into PASS."
adr=replace_section(adr,"## Gate result","## Decision and compatibility",gate_body); adr_path.write_text(adr)
print(json.dumps({"ok":True,"runs":60,"traces":60,"gate":"FAIL","part_a_cap_failures":summary["part_a_eip7825_fail_count"],"summary":str(OUT.relative_to(ROOT))},sort_keys=True))
