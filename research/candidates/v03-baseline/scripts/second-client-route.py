#!/usr/bin/env python3
"""Submit exact retained A/B calldata to an explicitly local second client.

The client must expose an unlocked synthetic account and a fixture-initialized
research pool at 0xc00000000000000000000000000000000000c000. No key is read.
"""
from __future__ import annotations
import argparse, json, time, urllib.parse, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
parser=argparse.ArgumentParser()
parser.add_argument("--rpc-url",required=True)
parser.add_argument("--from-address",required=True,help="unlocked local synthetic account")
parser.add_argument("--run-id",default="v03-fixed-01")
parser.add_argument("--out",type=Path,default=ROOT/"research/candidates/v03-baseline/gas/second-client.json")
args=parser.parse_args()
url=urllib.parse.urlparse(args.rpc_url)
if url.scheme not in {"http","https"} or url.hostname not in {"127.0.0.1","localhost","::1"}:
    raise SystemExit("refusing non-loopback RPC URL")
fixture=ROOT/"research/candidates/v03-baseline/proofs"/args.run_id
if not fixture.is_dir(): raise SystemExit("proof fixture missing; run generate-all.py")
request_id=0
def rpc(method,params):
    global request_id
    request_id+=1
    body=json.dumps({"jsonrpc":"2.0","id":request_id,"method":method,"params":params}).encode()
    with urllib.request.urlopen(urllib.request.Request(args.rpc_url,data=body,headers={"content-type":"application/json"})) as response:
        reply=json.load(response)
    if "error" in reply: raise SystemExit(f"{method}: {reply['error']}")
    return reply["result"]
def receipt(tx):
    for _ in range(600):
        value=rpc("eth_getTransactionReceipt",[tx])
        if value is not None:return value
        time.sleep(.1)
    raise SystemExit(f"receipt timeout: {tx}")
client=rpc("web3_clientVersion",[])
chain=rpc("eth_chainId",[])
pool="0xc00000000000000000000000000000000000c000"
receipts=[]
for part in ["part-a.calldata","part-b.calldata"]:
    data="0x"+(fixture/part).read_bytes().hex()
    tx=rpc("eth_sendTransaction",[{"from":args.from_address,"to":pool,"gas":hex(16_777_216),"value":"0x0","data":data}])
    got=receipt(tx)
    if int(got["status"],16)!=1: raise SystemExit(f"second-client transaction reverted: {tx}")
    receipts.append(got)
args.out.parent.mkdir(parents=True,exist_ok=True)
args.out.write_text(json.dumps({"candidate_id":"C00/v03-baseline","run_id":args.run_id,"client_version":client,"chain_id":chain,"rpc_policy":"loopback only; unlocked synthetic account; no key material","transactions":[{"hash":r["transactionHash"],"block":int(r["blockNumber"],16),"gas_used":int(r["gasUsed"],16),"status":int(r["status"],16)} for r in receipts]},indent=2,sort_keys=True)+"\n")
print(args.out)
