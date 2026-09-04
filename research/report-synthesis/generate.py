#!/usr/bin/env python3
"""Deterministically generate the fail-closed SP-90 synthesis."""
from __future__ import annotations

import argparse, csv, hashlib, io, json, sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SUMMARY = ROOT / "research/summaries"
CHECKPOINTS = [ROOT / f"research/reviews/checkpoint-{n}-{name}.json" for n, name in ((1,"baseline"),(2,"structural"),(3,"backends"),(4,"product"))]
SP80_STATUS = ROOT / "research/integrated-finalists/status.json"
SP80_RESULT = ROOT / "research/integrated-finalists/outputs/results.json"
TOKEN = "RECOMMEND_ADDITIONAL_TARGETED_RESEARCH"
FIELDS = ("protocol_semantics","application_hash_compression","digest_width","tree_shape","arithmetization","field_challenge_field","pcs_ldt","hiding_construction","proof_mmcs_transcript","security_profile","proof_bytes","abi_calldata","prover_performance_by_hardware","native_verifier_performance","evm_gas_by_component","complete_transaction_gas_three_schedules","runtime_initcode_deployment_gas","state_growth","checkpoint_behavior","implementation_maturity","external_review_status","known_blockers","gate_status")
CATEGORIES = ("security_confidence_and_completeness","one_transaction_feasibility_and_margin","total_user_gas_economic_cost","proof_bytes_future_floor_robustness","prover_ux","audit_and_implementation_complexity","deposit_efficiency","upstream_maturity_maintainability")
WEIGHTS = {
 "suggested": (25,20,15,10,10,10,5,5),
 "security_heavy": (40,15,10,10,5,10,5,5),
 "gas_heavy": (20,25,25,10,5,5,5,5),
 "operations_heavy": (20,15,10,10,20,10,5,10),
}
MINIMUM = {
 "C00":("v0.3 P2BB512","256x190 horizontal","hiding FRI q32","reproduced"),
 "C01":("v0.3 P2BB512","256x190 horizontal","hiding FRI q48","security/gas comparator"),
 "C10":("width-24 compression","best vertical","hiding FRI","measured if hash passes"),
 "C11":("width-32/12-field compression","best vertical","hiding FRI","required"),
 "C12":("width-32/12-field compression","second AIR geometry","hiding FRI","required"),
 "C20":("top relation","best AIR","HVZK-WHIR","required investigation"),
 "C21":("top relation","structured R1CS/CCS","Spartan-WHIR + ZK","required investigation"),
 "C22":("top inner proof","recursive verifier","transparent outer","required investigation"),
 "C23":("original Keccak relation","Flock repeated R1CS","Flock + ZK/outer","required investigation"),
 "C30":("best individual proof","aggregate proof","batch N=16","required if recursion exists"),
 "C40":("best non-one-tx proof","two-call verifier","bounded checkpoint","required fallback"),
}
BUNDLES = {"A":"optimized Poseidon2 compression + vertical AIR + hiding FRI","B":"optimized compression/AIR + HVZK-WHIR","C":"structured relation + Spartan-WHIR/HVZK","D":"optimized inner proof + transparent recursion","E":"Keccak relation + Flock + ZK/outer compression","F":"robust two-call fallback"}
PRODUCTS = {"individual-l1":"research/reviews/checkpoint-4-product.json","aggregation":"research/aggregation/status.json","robust-two-call":"research/two-call-state/status.json","l2":"research/l2-economics/status.json","prover-operations":"research/prover-operations/status.json"}
STOP_RULES = (
 ("SR01","relies on a prohibited classical wrapper"),("SR02","non-hiding and no concrete hiding path exists"),("SR03","generic or structural security falls below the target"),("SR04","proof floor alone exceeds the transaction cap"),("SR05","verifier requires an unavailable precompile"),("SR06","runtime cannot be modularized under current EIP-170 without changing semantics"),("SR07","complete relation destroys the toy-benchmark advantage"),("SR08","prover cannot run within available memory and has no practical service model"),("SR09","strictly dominated by another candidate"),("SR10","new consensus-critical custom cryptography is disproportionate to measured gain"),
)

def jb(v: Any)->bytes: return (json.dumps(v,indent=2,sort_keys=False,ensure_ascii=False)+"\n").encode()
def sha(p: Path)->str: return hashlib.sha256(p.read_bytes()).hexdigest()
def rel(p: Path)->str: return p.relative_to(ROOT).as_posix()
def src(p: Path, run: str|None=None)->dict[str,Any]: return {"source_run_id":run,"artifact_path":rel(p),"artifact_sha256":sha(p)}
def load(p: Path)->Any: return json.loads(p.read_text())
def readcsv(name: str)->list[dict[str,str]]:
 with (SUMMARY/name).open(newline="") as f: return list(csv.DictReader(f))
def csvb(header,rows)->bytes:
 s=io.StringIO(newline=""); w=csv.DictWriter(s,fieldnames=header,lineterminator="\n",extrasaction="ignore"); w.writeheader()
 for row in rows: w.writerow({k:"" if v is None else v for k,v in row.items()})
 return s.getvalue().encode()
def safe(s: str)->str: return s.replace(":","--").replace("/","-")
def uniq(items):
 out=[]; seen=set()
 for x in items:
  k=(x["source_run_id"],x["artifact_path"],x["artifact_sha256"])
  if k not in seen: seen.add(k); out.append(x)
 return sorted(out,key=lambda x:(x["artifact_path"],x["source_run_id"] or ""))
def fld(value, prov, status=None): return {"status":status or ("NOT_EVALUATED" if value is None else "REPORTED"),"value":value,"provenance":uniq(prov)}

def provenance_index():
 rows=readcsv("run-index.csv"); out={}
 for r in rows: out[r["run_id"]]={"source_run_id":r["run_id"],"artifact_path":r["record_path"],"artifact_sha256":r["record_sha256"]}
 return out

def table_rows(name,index):
 rows=readcsv(name); out=[]
 for r in rows:
  run=r.get("run_id")
  if not run and r.get("profile","").startswith("run:"): run=r["profile"].split(";",1)[0][4:]
  p=index.get(run)
  if p: r={**r,**p}
  else:
   path=ROOT/(r.get("artifact_path") or "research/run-records/evidence-manifest.json")
   r={**r,**src(path,run)}
  out.append(r)
 return out

def status_of(d):
 for k in ("overall","status","verdict","decision","disposition","conclusion","outcome","gate_status","gateResult"):
  if k in d: return str(d[k])
 if "flock" in d or "veil" in d:
  return "_".join(f"{k.upper()}_{d[k]}" for k in ("flock","veil") if k in d)
 return "NOT_EVALUATED"
def collect_blockers(d):
 out=[]
 for k,v in d.items():
  if "block" in k.lower() or "fail" in k.lower():
   if isinstance(v,str): out.append(v)
   elif isinstance(v,list): out += [str(x) for x in v]
   elif isinstance(v,dict): out += [f"{a}={b}" for a,b in sorted(v.items())]
 return sorted(set(out))

def candidates():
 out=[]
 for mp in sorted((ROOT/"research/candidates").glob("*/manifest.json")):
  m=load(mp); sp=mp.parent/"status.json"; sd=load(sp) if sp.exists() else {}; dn=mp.parent.name
  cid=str(m.get("candidateId") or m.get("candidate_id") or m.get("studyId") or dn); aliases={cid,dn}
  if cid=="SP-31/V1-V9": aliases |= {f"V{i}" for i in range(1,10)}
  out.append(dict(scorecard_id=f"component:{dn}",candidate_id=cid,kind="component",title=str(m.get("title") or m.get("name") or dn),manifest=m,status_doc=sd,status=status_of(sd or m),evidence=[src(mp)]+([src(sp)] if sp.exists() else []),aliases=aliases,manifest_path=rel(mp)))
 cp=[src(p) for p in CHECKPOINTS]
 aliases={"C00":{"C00/v03-baseline"},"C10":{"C10-fri"},"C20":{"C20"}}
 for cid,definition in MINIMUM.items():
  st="FAIL_REPRODUCED_BASELINE" if cid=="C00" else ("RESEARCH_ONLY_NO_WINNER" if cid=="C10" else ("DEFERRED_UPSTREAM_CONTROL_NOT_INTEGRATED" if cid=="C20" else "NOT_RUN_JUSTIFIED_GATE_FAILURE"))
  out.append(dict(scorecard_id=f"minimum:{cid}",candidate_id=cid,kind="minimum_matrix",title=f"Appendix-A {cid}",manifest={"hash_relation":definition[0],"relation":definition[1],"backend":definition[2],"required_status":definition[3]},status_doc={},status=st,evidence=cp,aliases=aliases.get(cid,set()),manifest_path=None))
 sp80=load(SP80_RESULT); br={str(x.get("bundleId")):x for x in sp80.get("bundles",[])}; be=[src(SP80_STATUS),src(SP80_RESULT),src(CHECKPOINTS[2])]
 for bid,title in BUNDLES.items():
  row=br.get(bid,{})
  out.append(dict(scorecard_id=f"bundle:{bid}",candidate_id=f"Bundle-{bid}",kind="bundle",title=title,manifest=row,status_doc=row,status=str(row.get("status") or row.get("eligibility") or "BLOCKED_NO_ELIGIBLE_COMPONENTS"),evidence=be,aliases=set(),manifest_path=None))
 chk4=load(CHECKPOINTS[3])
 for pid,path_s in PRODUCTS.items():
  p=ROOT/path_s; d=load(p); key={"individual-l1":"individual_ethereum_l1","robust-two-call":"robust_two_call","prover-operations":"prover_operations"}.get(pid,pid)
  st=str(chk4.get("architectures",{}).get(key,status_of(d))); aliases={"SP-70"} if pid=="aggregation" else ({"SP-72"} if pid=="robust-two-call" else set())
  out.append(dict(scorecard_id=f"product:{pid}",candidate_id=f"product-{pid}",kind="product_study",title=pid,manifest=d,status_doc=d,status=st,evidence=[src(p),src(CHECKPOINTS[3])],aliases=aliases,manifest_path=path_s))
 return sorted(out,key=lambda x:x["scorecard_id"])

def match(c,row): return row.get("candidate_id") in c["aliases"]
def compact(rows,keys): return [{k:(float(r[k]) if k.endswith(("_ms","_bits")) and r.get(k) not in (None,"") else (int(r[k]) if k.endswith(("_bytes","_gas","_rows","_width","_count")) and r.get(k) not in (None,"") and str(r[k]).lstrip("-").isdigit() else r.get(k))) for k in keys if r.get(k) not in (None,"")} for r in rows]
def rowprov(rows,base): return uniq([{"source_run_id":r.get("source_run_id"),"artifact_path":r["artifact_path"],"artifact_sha256":r["artifact_sha256"]} for r in rows]) or base

def stop_record(c,blockers,prov,proof,security):
 text=" ".join([c["status"],*blockers]).lower(); evaluations=[]
 for rid,rule in STOP_RULES:
  applies=False; why="No committed evidence establishes this stop predicate."
  if rid=="SR02" and "non-hiding" in text: applies=True; why="Package evidence reports non-hiding without an accepted integrated hiding path."
  elif rid=="SR03" and any(x in text for x in ("security target is not met","structural attack","round skip")): applies=True; why="Package blockers establish below-target or structurally attacked security."
  elif rid=="SR04" and any((x.get("raw_proof_bytes") or 0)*96>16_777_216 for x in proof): applies=True; why="An observed proof exceeds the active transaction cap under the draft 96-gas/byte floor."
  elif rid=="SR05" and "unavailable precompile" in text: applies=True; why="Package blocker explicitly requires an unavailable precompile."
  elif rid=="SR06" and "eip-170" in text and any(x in text for x in ("cannot","exceed")): applies=True; why="Package blocker explicitly establishes the EIP-170 condition."
  elif rid=="SR07" and "toy" in text and "not pqtc" in text: applies=True; why="Only toy/control evidence exists; the complete PQTC relation is absent."
  elif rid=="SR08" and all(x in text for x in ("memory","service")) and "fail" in text: applies=True; why="Package evidence establishes memory failure without a practical service model."
  evaluations.append({"rule_id":rid,"rule":rule,"disposition":"APPLIES" if applies else "NOT_ESTABLISHED","reason":why,"supporting_data":prov,"revival_condition":"New pinned evidence must remove the predicate and pass independent review." if applies else "No revival condition until this predicate is established."})
 stopped=any(e["disposition"]=="APPLIES" for e in evaluations) or any(x in c["status"].upper() for x in ("FAIL","STOP","BLOCK","DEFER","NOT_RUN"))
 return {"stopped":stopped,"last_stage":c["status"],"supporting_data":prov,"revival_condition":"Revive only after pinned evidence closes every hard gate and a checkpoint authorizes integration; weights cannot revive a candidate.","rule_evaluations":evaluations}

def build_card(c,tables):
 base=uniq(c["evidence"]); rr={k:[r for r in v if match(c,r)] for k,v in tables.items()}
 proof=compact(rr["proof"],("source_run_id","raw_proof_bytes","abi_calldata_bytes","zero_bytes","nonzero_bytes")); prover=compact(rr["prover"],("source_run_id","hardware_id","threads","wall_ms","cpu_ms","peak_rss_bytes","native_verify_ms","success")); gas=compact(rr["gas"],("source_run_id","operation","execution_gas")); tx=compact([r for r in rr["gas"] if r.get("eip7623_total")],("source_run_id","operation","eip7623_total","eip7976_total","eip8311_total","tx_cap_margin")); deploy=compact([r for r in rr["gas"] if any(r.get(k) for k in ("runtime_bytes","initcode_bytes","deployment_gas"))],("source_run_id","operation","runtime_bytes","initcode_bytes","deployment_gas")); sec=compact(rr["security"],("source_run_id","term","model","classical_bits","quantum_bits","proven_or_conjectural","binding","notes")); relation=compact(rr["relation"],("source_run_id","logical_rows","padded_rows","base_degree_bits","hiding_degree_bits","trace_width","constraint_count","max_degree","batched_functions"))
 m=c["manifest"]; blockers=collect_blockers(m)+collect_blockers(c["status_doc"]); blockers=sorted(set(blockers)) or ["No security qualification or integration authorization is present in checkpoints 1-4 and SP-80."]
 vals={
  "protocol_semantics":m.get("protocol") or m.get("protocolComponents") or m.get("frozenRelationControl"),
  "application_hash_compression":m.get("applicationHash") or m.get("immutableDefinition") or m.get("hash_relation"),
  "digest_width":m.get("applicationDigest") or m.get("outputFields"),"tree_shape":m.get("treeArityDepth") or (m.get("frozenRelationControl") or {}).get("applicationTree"),
  "arithmetization":relation or m.get("relation"),"field_challenge_field":(m.get("proofSystem") or {}).get("baseField") or (m.get("inheritanceMap") or {}).get("baseChallengeField"),
  "pcs_ldt":(m.get("inheritanceMap") or {}).get("pcsLdt") or m.get("backend"),"hiding_construction":(m.get("inheritanceMap") or {}).get("hidingConstruction") or (m.get("proofSystem") or {}).get("hiding"),
  "proof_mmcs_transcript":(m.get("inheritanceMap") or {}).get("transcript") or (m.get("noSilentInheritanceMatrix") or {}).get("mmcsTranscriptCodec"),
  "security_profile":sec or None,"proof_bytes":proof or None,"abi_calldata":[x for x in proof if "abi_calldata_bytes" in x] or None,
  "prover_performance_by_hardware":prover or None,"native_verifier_performance":[x for x in prover if "native_verify_ms" in x] or None,
  "evm_gas_by_component":gas or None,"complete_transaction_gas_three_schedules":tx or None,"runtime_initcode_deployment_gas":deploy or None,
  "state_growth":m.get("stateGrowth") or m.get("state_growth"),"checkpoint_behavior":m.get("checkpointModel") or (m.get("noSilentInheritanceMatrix") or {}).get("checkpoint"),
  "implementation_maturity":{"reported_status":c["status"],"manifest_path":c["manifest_path"]},"external_review_status":m.get("externalReview") or c["status_doc"].get("independentCryptanalysis") or "NOT_EXTERNALLY_SECURITY_QUALIFIED","known_blockers":blockers,"gate_status":{"reported_status":c["status"],"hard_gate_eligible":False},
 }
 prov_for={"relation":rowprov(rr["relation"],base),"proof":rowprov(rr["proof"],base),"prover":rowprov(rr["prover"],base),"gas":rowprov(rr["gas"],base),"security":rowprov(rr["security"],base)}
 raw={}
 for name in FIELDS:
  group="security" if name=="security_profile" else ("proof" if name in ("proof_bytes","abi_calldata") else ("prover" if name in ("prover_performance_by_hardware","native_verifier_performance") else ("gas" if name in ("evm_gas_by_component","complete_transaction_gas_three_schedules","runtime_initcode_deployment_gas") else ("relation" if name=="arithmetization" else None))))
  raw[name]=fld(vals[name],prov_for[group] if group else base,"OBSERVED" if group and vals[name] is not None else None)
 cats={}
 for name in CATEGORIES:
  value=None; reason="NOT_EVALUATED; null is not zero."
  if name==CATEGORIES[0]: value=0.0; reason="Known failure: no accepted security qualification."
  elif name==CATEGORIES[-1]: value=0.0 if any(x in c["status"].upper() for x in ("FAIL","STOP","BLOCK")) else 20.0; reason="Status rubric only; not a hard gate."
  cats[name]={"value":value,"reason":reason,"provenance":base}
 sets=[]
 for wn,weights in WEIGHTS.items():
  pairs=[(cats[k]["value"],w) for k,w in zip(CATEGORIES,weights) if cats[k]["value"] is not None]; cov=sum(w for _,w in pairs); score=round(sum(v*w for v,w in pairs)/cov,6) if cov else None
  sets.append({"name":wn,"weights_percent":dict(zip(CATEGORIES,weights)),"score":score,"evaluated_weight_percent":cov,"missing_categories":[k for k in CATEGORIES if cats[k]["value"] is None],"eligible_after_hard_gates":False,"provenance":base})
 scores=[x["score"] for x in sets if x["score"] is not None]; sensitivity={"minimum_score":min(scores) if scores else None,"maximum_score":max(scores) if scores else None,"range":round(max(scores)-min(scores),6) if scores else None,"ranking_effect":"INELIGIBLE_UNDER_ALL_WEIGHT_SETS","null_policy":"Missing categories are excluded and coverage disclosed; null is never converted to zero.","provenance":base}
 gateprov=uniq(base+[src(CHECKPOINTS[1]),src(CHECKPOINTS[2]),src(CHECKPOINTS[3]),src(SP80_STATUS)])
 return {"schema":"pqtc.sp90.candidate-scorecard.v1","scorecard_id":c["scorecard_id"],"candidate_id":c["candidate_id"],"candidate_kind":c["kind"],"identity":fld({"title":c["title"],"manifest_path":c["manifest_path"],"metric_aliases":sorted(c["aliases"])},base),"raw_metrics":raw,"secondary_scores":{"raw_category_scores":cats,"weight_sets":sets,"sensitivity":sensitivity},"hard_gate":{"eligible":False,"security_qualified":False,"integration_eligible":False,"reasons":["No accepted security qualification.","Checkpoints 2-4 authorize no integration or product candidate.","SP-80 records zero eligible bundles and zero complete prototypes."],"provenance":gateprov},"stop_record":stop_record(c,blockers,base,proof,sec)}

def value_map(card):
 r=card["raw_metrics"]
 def nums(field,key,pred=lambda x:True):
  v=r[field]["value"]; return [float(x[key]) for x in v or [] if isinstance(x,dict) and x.get(key) is not None and pred(x)] if isinstance(v,list) else []
 accepted=[]  # Checkpoints and SP-80 accept no security profile; theorem/heuristic terms are not qualification.
 comp=r["evm_gas_by_component"]["value"] if isinstance(r["evm_gas_by_component"]["value"],list) else []
 dep=[float(x["execution_gas"]) for x in comp if x.get("execution_gas") is not None and "deposit" in str(x.get("operation","")).lower()]; wd=[float(x["execution_gas"]) for x in comp if x.get("execution_gas") is not None and "withdraw" in str(x.get("operation","")).lower()]; runtime=nums("runtime_initcode_deployment_gas","runtime_bytes"); tx=nums("complete_transaction_gas_three_schedules","eip7623_total"); proof=nums("proof_bytes","raw_proof_bytes"); prover=nums("prover_performance_by_hardware","wall_ms")
 return {"security":min(accepted) if accepted else None,"tx":min(tx) if tx else None,"proof":min(proof) if proof else None,"prover":min(prover) if prover else None,"deposit":min(dep) if dep else None,"withdrawal":min(wd) if wd else (min(tx) if tx else None),"runtime":min(runtime) if runtime else None,"verifier":None,"complexity":None,"performance":min(tx) if tx else None,"total":None,"amortized":None}

def pareto(cards):
 defs=(("security-vs-one-tx-gas","security","tx","max","min"),("security-vs-proof-bytes","security","proof","max","min"),("proof-bytes-vs-execution-gas","proof","tx","min","min"),("prover-time-vs-transaction-gas","prover","tx","min","min"),("deposit-gas-vs-withdrawal-gas","deposit","withdrawal","min","min"),("runtime-code-size-vs-verifier-gas","runtime","verifier","min","min"),("implementation-complexity-vs-performance","complexity","performance","min","min"),("total-gas-vs-amortized-aggregation-gas","total","amortized","min","min")); maps={c["scorecard_id"]:value_map(c) for c in cards}; outputs={}; summaries=[]
 for aid,xk,yk,xd,yd in defs:
  rows=[]; points=[]
  for c in cards:
   x,y=maps[c["scorecard_id"]][xk],maps[c["scorecard_id"]][yk]; ok=x is not None and y is not None
   if ok: points.append((c["scorecard_id"],x,y))
   missing=[k for k,v in ((xk,x),(yk,y)) if v is None]
   rows.append({"scorecard_id":c["scorecard_id"],"candidate_id":c["candidate_id"],"x_metric":xk,"x_value":x,"x_direction":xd,"y_metric":yk,"y_value":y,"y_direction":yd,"comparable":str(ok).lower(),"exclusion_reason":"" if ok else "INCOMPARABLE_NULL_"+"_AND_".join(m.upper() for m in missing),"nondominated":"","dominated_by":""})
  for r in rows:
   if r["comparable"]!="true": continue
   x,y=float(r["x_value"]),float(r["y_value"]); dom=[]
   for oid,ox,oy in points:
    if oid==r["scorecard_id"]: continue
    xn=ox>=x if xd=="max" else ox<=x; yn=oy>=y if yd=="max" else oy<=y; xb=ox>x if xd=="max" else ox<x; yb=oy>y if yd=="max" else oy<y
    if xn and yn and (xb or yb): dom.append(oid)
   r["nondominated"]=str(not dom).lower(); r["dominated_by"]=json.dumps(sorted(dom),separators=(",",":"))
  path=f"research/report-synthesis/pareto/{aid}.csv"; outputs[path]=csvb(("scorecard_id","candidate_id","x_metric","x_value","x_direction","y_metric","y_value","y_direction","comparable","exclusion_reason","nondominated","dominated_by"),rows); summaries.append({"axis_id":aid,"path":path,"x_metric":xk,"x_direction":xd,"y_metric":yk,"y_direction":yd,"comparable_count":len(points),"excluded_count":len(rows)-len(points),"nondominated_scorecards":[r["scorecard_id"] for r in rows if r["nondominated"]=="true"],"policy":"Nondominance computed only among records with both axes non-null; exclusions retain explicit reasons."})
 return outputs,summaries

def expected():
 idx=provenance_index(); tables={"relation":table_rows("relation-geometry.csv",idx),"proof":table_rows("proof-ledger.csv",idx),"gas":table_rows("evm-gas.csv",idx),"prover":table_rows("prover.csv",idx),"security":table_rows("security.csv",idx)}; cs=candidates(); cards=[build_card(c,tables) for c in cs]; out={f"research/report-synthesis/scorecards/{safe(c['scorecard_id'])}.json":jb(c) for c in cards}; po,ps=pareto(cards); out.update(po)
 master=[]
 for c,card in zip(cs,cards):
  rr=[r for r in tables["relation"] if match(c,r)]; r=rr[0] if rr else {}; p=r or c["evidence"][0]
  master.append({"scorecard_id":c["scorecard_id"],"candidate_id":c["candidate_id"],"candidate_kind":c["kind"],"title":c["title"],"manifest_path":c["manifest_path"],"reported_status":c["status"],"security_qualified":"false","integration_eligible":"false","hard_gate_status":"FAIL","table_id":r.get("source_run_id"),**{k:r.get(k) for k in ("logical_rows","padded_rows","base_degree_bits","hiding_degree_bits","trace_width","preprocessed_width","constraint_count","max_degree","quotient_chunks","batched_functions","rotations","active_rows","padding_rows")},"source_run_id":r.get("source_run_id"),"artifact_path":p["artifact_path"],"artifact_sha256":p["artifact_sha256"],"scorecard_path":f"research/report-synthesis/scorecards/{safe(c['scorecard_id'])}.json"})
 mh=("scorecard_id","candidate_id","candidate_kind","title","manifest_path","reported_status","security_qualified","integration_eligible","hard_gate_status","table_id","logical_rows","padded_rows","base_degree_bits","hiding_degree_bits","trace_width","preprocessed_width","constraint_count","max_degree","quotient_chunks","batched_functions","rotations","active_rows","padding_rows","source_run_id","artifact_path","artifact_sha256","scorecard_path"); out["research/summaries/candidate-master.csv"]=csvb(mh,master)
 specs={"security-master.csv":(("candidate_id","source_run_id","profile","term","model","formula_source","input_summary","classical_bits","quantum_bits","proven_or_conjectural","multi_target_count","binding","notes","artifact_path","artifact_sha256"),tables["security"]),"gas-decomposition.csv":(("candidate_id","source_run_id","operation","execution_gas","standard_intrinsic","eip7623_floor","eip7623_total","eip7976_floor","eip7976_total","eip8311_floor","eip8311_total","tx_cap_margin","runtime_bytes","initcode_bytes","deployment_gas","artifact_path","artifact_sha256"),tables["gas"]),"proof-byte-ledger-master.csv":(("candidate_id","source_run_id","raw_proof_bytes","abi_calldata_bytes","header_bytes","statement_bytes","global_bytes","query_row_bytes","salt_bytes","frontier_bytes","ldt_bytes","final_bytes","continuation_bytes","abi_overhead_bytes","zero_bytes","nonzero_bytes","artifact_path","artifact_sha256"),tables["proof"]),"prover-master.csv":(("candidate_id","source_run_id","hardware_id","threads","cold_or_warm","wall_ms","cpu_ms","peak_rss_bytes","proof_bytes","native_verify_ms","success","artifact_path","artifact_sha256"),tables["prover"])}
 for n,(h,rows) in specs.items(): out[f"research/summaries/{n}"]=csvb(h,rows)
 mins=[]
 for cid,d in MINIMUM.items(): mins.append({"candidate_id":cid,"hash_relation":d[0],"air_r1cs":d[1],"backend":d[2],"required_status":d[3],"evaluation_status":"EVIDENCE_RECORDED_GATE_FAIL" if cid in ("C00","C10","C20") else "NOT_RUN","justified_gate_failure":"NO_SECURITY_QUALIFIED_OR_INTEGRATION_AUTHORIZED_COMPONENT; CHECKPOINTS_2_4_AND_SP80_FAIL_CLOSED","security_qualified":"false","integration_eligible":"false","scorecard_id":f"minimum:{cid}","artifact_path":rel(CHECKPOINTS[2]),"artifact_sha256":sha(CHECKPOINTS[2])})
 out["research/summaries/minimum-candidate-matrix.csv"]=csvb(("candidate_id","hash_relation","air_r1cs","backend","required_status","evaluation_status","justified_gate_failure","security_qualified","integration_eligible","scorecard_id","artifact_path","artifact_sha256"),mins)
 sr=[]
 for c in cards:
  s=next(x for x in c["secondary_scores"]["weight_sets"] if x["name"]=="suggested"); sr.append({"scorecard_id":c["scorecard_id"],"candidate_id":c["candidate_id"],"candidate_kind":c["candidate_kind"],"reported_gate_status":c["raw_metrics"]["gate_status"]["value"]["reported_status"],"security_qualified":"false","integration_eligible":"false","suggested_score":s["score"],"score_coverage_percent":s["evaluated_weight_percent"],"alternative_scores":json.dumps({x["name"]:x["score"] for x in c["secondary_scores"]["weight_sets"] if x["name"]!="suggested"},sort_keys=True,separators=(",",":")),"sensitivity_range":c["secondary_scores"]["sensitivity"]["range"],"hard_gate_override":"false","scorecard_path":f"research/report-synthesis/scorecards/{safe(c['scorecard_id'])}.json","score_provenance":json.dumps(s["provenance"],sort_keys=True,separators=(",",":"))})
 out["research/summaries/candidate-scorecards.csv"]=csvb(("scorecard_id","candidate_id","candidate_kind","reported_gate_status","security_qualified","integration_eligible","suggested_score","score_coverage_percent","alternative_scores","sensitivity_range","hard_gate_override","scorecard_path","score_provenance"),sr)
 sm=[]; numeric={"candidate-master.csv":set(mh[10:23]),"security-master.csv":{"classical_bits","quantum_bits","multi_target_count"},"gas-decomposition.csv":set(specs["gas-decomposition.csv"][0][3:15]),"proof-byte-ledger-master.csv":set(specs["proof-byte-ledger-master.csv"][0][2:16]),"prover-master.csv":{"threads","wall_ms","cpu_ms","peak_rss_bytes","proof_bytes","native_verify_ms"},"candidate-scorecards.csv":{"suggested_score","score_coverage_percent","sensitivity_range"}}
 allrows={"candidate-master.csv":master,**{n:rows for n,(_,rows) in specs.items()},"candidate-scorecards.csv":sr}
 for n,rows in allrows.items():
  for i,r in enumerate(rows,1):
   for col in numeric[n]:
    if r.get(col) in (None,""): continue
    prov=idx.get(r.get("source_run_id")) or cpoint_source()
    sm.append({"output_path":f"research/summaries/{n}","row_number":i,"row_key":str(r.get("scorecard_id") or r.get("source_run_id") or r.get("candidate_id")),"column":col,**prov})
 out["research/report-synthesis/source-map.json"]=jb({"schema":"pqtc.sp90.numeric-source-map.v1","policy":"Every non-null numeric summary cell maps to a run or checkpoint hash; scorecard numeric values carry provenance in their enclosing raw field or score object.","entries":sorted(sm,key=lambda x:(x["output_path"],x["row_number"],x["column"]))})
 cps=[src(p) for p in CHECKPOINTS]; result={"schema":"pqtc.sp90.result.v1","spike":"SP-90","research_cutoff":"2026-09-04","evidence_boundary":{"allowed":["research/runs","research/run-records","committed package results","checkpoints 1-4"],"excluded":["projections as measurements","uncommitted observations","weighted gate overrides"],"provenance":[src(ROOT/"research/run-records/evidence-manifest.json")]},"scorecard_count":len(cards),"scorecard_index":[{"scorecard_id":c["scorecard_id"],"candidate_id":c["candidate_id"],"kind":c["candidate_kind"],"path":f"research/report-synthesis/scorecards/{safe(c['scorecard_id'])}.json","eligible":False} for c in cards],"pareto_axes":ps,"weight_sets":[{"name":n,"weights_percent":dict(zip(CATEGORIES,w)),"sum_percent":sum(w),"policy":"Secondary only; null excluded with coverage; gates control."} for n,w in WEIGHTS.items()],"sensitivity":{"sets_evaluated":list(WEIGHTS),"eligible_under_any_set":[],"conclusion":"Score movement cannot create a finalist while hard gates fail."},"stop_rule_catalog":[{"rule_id":i,"rule":r} for i,r in STOP_RULES],"decision":{"outcome":"OUTCOME_D","label":"no new full build yet","hard_gate_winners":[],"eligible_finalists":[]},"recommendation_token":TOKEN,"decision_evidence":[{"claim":"Checkpoint 1 forbids integration, deployment, and security qualification.","provenance":[cps[0]]},{"claim":"Checkpoint 2 authorizes no full bundle.","provenance":[cps[1]]},{"claim":"Checkpoint 3 records empty integration scope.","provenance":[cps[2]]},{"claim":"Checkpoint 4 selects no product path.","provenance":[cps[3]]},{"claim":"SP-80 records zero eligible bundles and complete prototypes.","provenance":[src(SP80_STATUS),src(SP80_RESULT)]}],"consistency":{"checkpoint_1_forbids_integration":True,"checkpoint_2_authorizes_no_bundle":True,"checkpoint_3_empty_integration_scope":True,"checkpoint_4_selects_no_product":True,"sp80_zero_eligible":True,"weighted_scores_cannot_override_gates":True,"null_is_not_zero":True,"false_finalist_count":0}}
 result["decision_evidence"][-1]["frontier_status"]=load(SP80_STATUS)["status"]
 out["research/summaries/spike-results.json"]=jb(result)
 if len([x for x in cards if x["candidate_kind"]=="component"])!=len(list((ROOT/"research/candidates").glob("*/manifest.json"))) or len(ps)!=8 or any(x["hard_gate"]["eligible"] for x in cards): raise ValueError("coverage or hard-gate invariant failed")
 return out

def cpoint_source(): return src(CHECKPOINTS[2])
def managed():
 paths={f"research/summaries/{x}" for x in ("candidate-master.csv","security-master.csv","gas-decomposition.csv","proof-byte-ledger-master.csv","prover-master.csv","minimum-candidate-matrix.csv","candidate-scorecards.csv","spike-results.json")}; paths.add("research/report-synthesis/source-map.json")
 for d in (HERE/"scorecards",HERE/"pareto"):
  if d.exists(): paths|={rel(p) for p in d.iterdir() if p.is_file()}
 return paths
def write_all(out):
 for p in managed()-set(out): (ROOT/p).unlink(missing_ok=True)
 for n,b in sorted(out.items()): p=ROOT/n; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(b)
def check_all(out):
 bad=[]
 for n,b in sorted(out.items()):
  p=ROOT/n; a=p.read_bytes() if p.exists() else None
  if a!=b: bad.append({"path":n,"expected":hashlib.sha256(b).hexdigest(),"actual":None if a is None else hashlib.sha256(a).hexdigest()})
 if managed()-set(out): bad += [{"path":p,"error":"STALE"} for p in sorted(managed()-set(out))]
 if bad: raise ValueError(json.dumps({"code":"NONDETERMINISTIC_OR_STALE_OUTPUT","failures":bad},sort_keys=True))
def main(argv=None):
 ap=argparse.ArgumentParser(); ap.add_argument("--check",action="store_true"); a=ap.parse_args(argv)
 try:
  one=expected(); two=expected()
  if one!=two: raise ValueError("in-process nondeterminism")
  check_all(one) if a.check else write_all(one); print(f"PASS: {len(one)} deterministic SP-90 outputs" if a.check else f"WROTE: {len(one)} deterministic SP-90 outputs"); return 0
 except Exception as e: print(f"SP-90 generation failed: {e}",file=sys.stderr); return 1
if __name__=="__main__": raise SystemExit(main())
