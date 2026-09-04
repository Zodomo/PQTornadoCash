#!/usr/bin/env python3
"""Export one deterministic Foundry fixture as go-ethereum evm t8n input."""
from __future__ import annotations
import argparse, json, os, shutil, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
CAND=ROOT/"research/candidates/v03-baseline"
POOL="0xc00000000000000000000000000000000000c000"
SENDER="0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266"
SECRET_KEY="0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
CAP=16_777_216

parser=argparse.ArgumentParser()
parser.add_argument("--run-id",default="v03-fixed-19")
parser.add_argument("--out",type=Path)
args=parser.parse_args()
fixture=CAND/"proofs"/args.run_id
if not fixture.is_dir(): raise SystemExit("fixture missing; run generate-all.py")
out=(args.out or CAND/"gas/t8n"/args.run_id).resolve()
if out.exists(): shutil.rmtree(out)
out.mkdir(parents=True)
state=out/"foundry-state.json"
env={**os.environ,"V03_FIXTURE_DIR":f"../proofs/{args.run_id}","V03_PRESTATE_OUT":str(state)}
command=["forge","test","--root",".","--match-test","testExportFixturePrestate","-vv"]
result=subprocess.run(command,cwd=CAND/"evm",text=True,capture_output=True,env=env)
(out/"foundry-export.log").write_text(result.stdout+result.stderr)
if result.returncode: raise SystemExit(result.stdout+result.stderr)
raw=json.loads(state.read_text())
if "alloc" in raw: alloc=raw["alloc"]
elif "accounts" in raw: alloc=raw["accounts"]
else: alloc=raw
normalized={key.lower():value for key,value in alloc.items()}
for required in [POOL,SENDER]:
    if required not in normalized: raise SystemExit(f"dumpState output lacks required account {required}")
(out/"alloc.json").write_text(json.dumps(normalized,indent=2,sort_keys=True)+"\n")
environment={"currentCoinbase":"0x0000000000000000000000000000000000000000","currentGasLimit":"0x3000000","currentNumber":"0x1","currentTimestamp":"0x1","currentBaseFee":"0x0","currentRandom":"0x"+"00"*32,"parentBeaconBlockRoot":"0x"+"00"*32,"withdrawals":[]}
(out/"env.json").write_text(json.dumps(environment,indent=2,sort_keys=True)+"\n")
txs=[]
for nonce,name in enumerate(["part-a.calldata","part-b.calldata"]):
    data="0x"+(fixture/name).read_bytes().hex()
    command=["cast","mktx",POOL,data,"--legacy","--gas-limit",str(CAP),"--gas-price","0","--nonce",str(nonce),"--chain","1","--private-key",SECRET_KEY,"--no-proxy"]
    signed=subprocess.run(command,cwd=CAND/"evm",text=True,capture_output=True,check=True).stdout.strip()
    decoded=subprocess.run(["cast","decode-transaction","--json",signed],cwd=CAND/"evm",text=True,capture_output=True,check=True).stdout
    transaction=json.loads(json.loads(decoded))
    txs.append({key:value for key,value in transaction.items() if key not in {"hash","signer","type"}})
(out/"txs.json").write_text(json.dumps(txs,indent=2,sort_keys=True)+"\n")
(out/"route.json").write_text(json.dumps({"candidate_id":"C00/v03-baseline","run_id":args.run_id,"simulation":"go-ethereum evm t8n; sequential A then B; not mined receipts","pool":POOL,"sender":SENDER,"sender_key_policy":"well-known Anvil development key; synthetic and prohibited for real funds","transaction_count":2,"gas_limit_each":CAP,"fork":"Prague","expected_client_image":"ethereum/client-go:alltools-v1.17.5","expected_geth_commit":"9621c6ad"},indent=2,sort_keys=True)+"\n")
print(out)
