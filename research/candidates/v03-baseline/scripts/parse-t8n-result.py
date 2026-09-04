#!/usr/bin/env python3
"""Parse go-ethereum t8n sequential simulation and opcode traces without inventing receipts."""
from __future__ import annotations
import argparse, collections, json
from pathlib import Path

parser=argparse.ArgumentParser(); parser.add_argument("directory",type=Path); args=parser.parse_args(); directory=args.directory.resolve()
route=json.loads((directory/"route.json").read_text()); result=json.loads((directory/"result.json").read_text())
client=(directory/"client-version.txt").read_text().strip()
if "1.17.5" not in client or "9621c6ad" not in client: raise SystemExit(f"unexpected go-ethereum build: {client}")
aggregate_opcode_counts=json.loads((directory/"opcode-count.json").read_text())
rejected=result.get("rejected",[])
receipts=result.get("receipts",[])
if rejected: raise SystemExit(f"t8n rejected transactions: {rejected}")
if len(receipts)!=2: raise SystemExit(f"expected two sequential t8n receipts, got {len(receipts)}")
parsed_receipts=[]
for index,receipt in enumerate(receipts):
    status=int(receipt.get("status","0x0"),16) if isinstance(receipt.get("status"),str) else int(receipt.get("status",0))
    gas=int(receipt["gasUsed"],16) if isinstance(receipt.get("gasUsed"),str) else int(receipt["gasUsed"])
    parsed_receipts.append({"index":index,"part":"A" if index==0 else "B","status":status,"gas_used":gas,"transaction_hash":receipt.get("transactionHash"),"receipt_kind":"t8n state-transition simulation; not mined"})

def gather_ops(value,counts):
    if isinstance(value,dict):
        op=value.get("opName")
        if isinstance(op,str): counts[op]+=1
        for child in value.values(): gather_ops(child,counts)
    elif isinstance(value,list):
        for child in value:gather_ops(child,counts)
trace_profiles=[]
trace_files=sorted(path for path in directory.rglob("*") if path.is_file() and "trace" in path.name.lower() and path.suffix in {".json",".jsonl"})
for path in trace_files:
    counts=collections.Counter(); lines=0
    with path.open(errors="replace") as stream:
        for line in stream:
            try: value=json.loads(line)
            except json.JSONDecodeError: continue
            lines+=1; gather_ops(value,counts)
    if counts: trace_profiles.append({"source_trace_filename":path.name,"json_records":lines,"opcode_steps":sum(counts.values()),"opcode_counts":dict(sorted(counts.items()))})
if len(trace_profiles)<2: raise SystemExit("t8n produced fewer than two opcode-bearing trace files; raw opcode status remains NOT_EVALUATED")
for path in trace_files: path.unlink()
failed=[receipt for receipt in parsed_receipts if receipt["status"]!=1]
evidence={"candidate_id":"C00/v03-baseline","run_id":route["run_id"],"client":client,"expected_commit":"9621c6ad","simulation_kind":"go-ethereum evm t8n Prague sequential state transition; not a mined block/receipt","outcome":"FAIL" if failed else "PASS","receipts":parsed_receipts,"aggregate_opcode_counts":aggregate_opcode_counts,"opcode_profiles":trace_profiles,"raw_trace_retention":"JSONL removed after deterministic per-transaction opcode aggregation","post_state_root":result.get("stateRoot"),"tx_root":result.get("txRoot"),"receipts_root":result.get("receiptsRoot"),"logs_hash":result.get("logsHash")}
name="failure-evidence.json" if failed else "evidence.json"
(directory/name).write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n")
print(directory/name)
if failed: raise SystemExit(f"t8n sequential simulation failed: {[(r['part'],r['status'],r['gas_used']) for r in failed]}")
