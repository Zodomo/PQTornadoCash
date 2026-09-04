#!/usr/bin/env python3
"""Count opcodes from debug_traceTransaction on a loopback research client."""
from __future__ import annotations
import argparse, collections, json, urllib.parse, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
parser=argparse.ArgumentParser(); parser.add_argument("--rpc-url",required=True); parser.add_argument("tx_hash",nargs="+"); parser.add_argument("--out",type=Path,default=ROOT/"research/candidates/v03-baseline/gas/opcode-counts.json"); args=parser.parse_args()
url=urllib.parse.urlparse(args.rpc_url)
if url.scheme not in {"http","https"} or url.hostname not in {"127.0.0.1","localhost","::1"}: raise SystemExit("refusing non-loopback RPC URL")
def rpc(method,params):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    with urllib.request.urlopen(urllib.request.Request(args.rpc_url,data=body,headers={"content-type":"application/json"})) as response: reply=json.load(response)
    if "error" in reply: raise SystemExit(f"{method}: {reply['error']}")
    return reply["result"]
profiles=[]
for tx in args.tx_hash:
    trace=rpc("debug_traceTransaction",[tx,{"disableMemory":True,"disableStorage":True,"disableStack":True}])
    logs=trace.get("structLogs")
    if not isinstance(logs,list): raise SystemExit("client trace is not structLogs-compatible")
    counts=collections.Counter(row["op"] for row in logs)
    profiles.append({"transaction_hash":tx,"failed":trace.get("failed"),"gas":trace.get("gas"),"steps":len(logs),"opcode_counts":dict(sorted(counts.items()))})
args.out.parent.mkdir(parents=True,exist_ok=True); args.out.write_text(json.dumps({"candidate_id":"C00/v03-baseline","client_version":rpc("web3_clientVersion",[]),"profiles":profiles},indent=2,sort_keys=True)+"\n"); print(args.out)
