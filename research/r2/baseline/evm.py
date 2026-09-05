"""Local-only signed transactions and non-overlapping opcode/source attribution."""
import collections
import gzip
import hashlib
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

CAP = 16_777_216
SENDER = "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266"
# Public Anvil development key, never a wallet or funded witness.
PUBLIC_TEST_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
POOL = "0xc00000000000000000000000000000000000c000"
PARAMETER = "35adfcc070249bb0393c2fd45f0bbd48ef03cbfc08070d03335eaf952975e62ab7bc82ead4f8c1f1c39b3372be85195853134dfc9d24f43b97a5e0454ea07779"
CATEGORIES = ("parse_canonicality", "transcript_challenges", "air_evaluation", "ood_quotient", "alpha_opening_aggregates", "inverse_calculations", "row_reductions", "mmcs_hashing_paths", "fri_arithmetic", "checkpoint_storage_deletion", "public_statement", "nullifier_write", "payout_calls", "constructor_hashing", "constructor_storage", "other_state", "compiler_shared_or_unmapped")


def number(value):
    return int(value, 16) if isinstance(value, str) and value.startswith("0x") else int(value)


class RPC:
    def __init__(self, url):
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "::1"} or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("only explicit loopback HTTP disposable Anvil endpoints are permitted")
        self.url = url
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        self.client = self.call("web3_clientVersion", [])
        if "anvil" not in self.client.lower() or number(self.call("eth_chainId", [])) != 31337:
            raise ValueError("requires isolated Anvil chain ID 31337")

    def call(self, method, params):
        request = urllib.request.Request(self.url, data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(), headers={"Content-Type":"application/json"})
        with self.opener.open(request, timeout=1800) as response:
            reply = json.load(response)
        if "error" in reply:
            raise RuntimeError(f"{method}: {reply['error']}")
        return reply["result"]


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def intrinsic(data, create=False):
    zero = data.count(0)
    nonzero = len(data)-zero
    tokens = zero+4*nonzero
    return {"zero_bytes":zero,"nonzero_bytes":nonzero,"standard_intrinsic":21000+4*tokens+(32000+2*((len(data)+31)//32) if create else 0),"eip7623_floor":21000+10*tokens,"initcode_word_gas":2*((len(data)+31)//32) if create else 0}


def send_signed(rpc, run, out, label, data, to=None, cap=CAP):
    out.mkdir(parents=True, exist_ok=False)
    nonce = number(rpc.call("eth_getTransactionCount", [SENDER,"pending"]))
    argv = ["cast","mktx","--legacy","--gas-limit",str(cap),"--gas-price","0","--nonce",str(nonce),"--chain","31337","--private-key",PUBLIC_TEST_KEY,"--no-proxy"]
    argv += ([to,"0x"+data.hex()] if to else ["--create","0x"+data.hex()])
    signed = run(label+"-sign", argv).stdout.decode().strip()
    raw = bytes.fromhex(signed.removeprefix("0x"))
    (out/"signed.rlp").write_bytes(raw)
    (out/"calldata.bin").write_bytes(data)
    record = {"measurement_class":"MEASURED","rpc_url":rpc.url,"client":rpc.client,"chain_id":31337,"signed_by":"PUBLIC_ANVIL_TEST_KEY","gas_limit":cap,"creation":to is None,"signed_transaction_bytes":len(raw),"abi_or_initcode_bytes":len(data),"rlp_envelope_bytes":len(raw)-len(data),"intrinsic":intrinsic(data,to is None)}
    record["nonce"] = nonce
    record["sender"] = SENDER
    record["target"] = to
    record["latest_block"] = rpc.call("eth_getBlockByNumber",["latest",False])
    write_json(out/"request.json", record)
    try:
        tx = rpc.call("eth_sendRawTransaction", [signed])
    except RuntimeError as exc:
        record.update({"admission":"REJECTED","error":str(exc),"receipt":None})
        write_json(out/"result.json", record)
        return record
    record["transaction_hash"] = tx
    deadline = time.monotonic()+120
    receipt = None
    while receipt is None and time.monotonic()<deadline:
        receipt = rpc.call("eth_getTransactionReceipt", [tx])
        if receipt is None:
            time.sleep(.1)
    if receipt is None:
        raise RuntimeError(f"local receipt timed out for {tx}")
    write_json(out/"receipt.json", receipt)
    transaction = rpc.call("eth_getTransactionByHash", [tx])
    write_json(out/"transaction.json", transaction)
    record.update({"admission":"MINED","success":number(receipt["status"]) == 1,"gas_used":number(receipt["gasUsed"]),"contract_address":receipt.get("contractAddress")})
    write_json(out/"result.json", record)
    # Separate retained call totals overlap with descendant frames; never add them.
    calls = rpc.call("debug_traceTransaction", [tx,{"tracer":"callTracer"}])
    write_json(out/"call-trace.json", calls)
    trace = rpc.call("debug_traceTransaction", [tx,{"disableMemory":True,"disableStorage":True,"disableStack":True}])
    with gzip.open(out/"opcode-trace.json.gz", "wt", compresslevel=1) as stream:
        json.dump(trace, stream, separators=(",", ":"))
    record["trace_file"] = "opcode-trace.json.gz"
    record["trace_sha256"] = hashlib.sha256((out/"opcode-trace.json.gz").read_bytes()).hexdigest()
    if record["success"] and to is None:
        code = bytes.fromhex(rpc.call("eth_getCode", [receipt["contractAddress"],"latest"]).removeprefix("0x"))
        (out/"runtime.bin").write_bytes(code)
        record.update({"runtime_bytes":len(code),"code_deposit_gas":len(code)*200})
    elif to is None:
        record.update({"runtime_bytes":0,"code_deposit_gas":0,"constructor_result":"REVERTED_OR_OUT_OF_GAS; attempted storage/hash costs retained in trace"})
    write_json(out/"result.json", record)
    return record


def source_catalog(build_dir, source_root):
    """Use solc build-info IDs, AST ranges and exact bytecode PC/source maps."""
    result = []
    for file in sorted(build_dir.glob("build-info/*.json")):
        info = json.loads(file.read_text())
        if "output" not in info or "input" not in info:
            # Foundry also emits compact build-info; reconstruct the identical
            # solc catalog from its source IDs and per-contract artifacts.
            paths = info.get("source_id_to_path",{})
            if not paths:
                continue
            normalized = {"input":{"sources":{}},"output":{"sources":{},"contracts":{}}}
            for source_id,name in paths.items():
                candidate = (source_root/name).resolve()
                normalized["input"]["sources"][name] = {"content":candidate.read_text() if candidate.is_file() else ""}
                normalized["output"]["sources"][name] = {"id":int(source_id)}
            for artifact_file in sorted(build_dir.glob("*/*.json")):
                if artifact_file.parent.name == "build-info":
                    continue
                compiled = json.loads(artifact_file.read_text())
                targets = compiled.get("metadata",{}).get("settings",{}).get("compilationTarget",{})
                for source_name,contract_name in targets.items():
                    if source_name not in normalized["output"]["sources"]:
                        continue
                    normalized["output"]["contracts"].setdefault(source_name,{})[contract_name] = {"evm":compiled}
                    if "ast" in compiled:
                        normalized["output"]["sources"][source_name]["ast"] = compiled["ast"]
            info = normalized
        if not any("ast" in source for source in info["output"].get("sources",{}).values()):
            raise ValueError("compiler AST missing; the isolated build requires --ast")
        sources = {}
        for name, source in info["output"].get("sources",{}).items():
            content = info["input"]["sources"].get(name,{}).get("content")
            if content is None:
                candidate = (source_root/name).resolve()
                content = candidate.read_text() if candidate.is_file() else ""
            functions = []
            def visit(node):
                if isinstance(node,dict):
                    if node.get("nodeType") in {"FunctionDefinition","ModifierDefinition"}:
                        start,length,_ = map(int,node["src"].split(":"))
                        functions.append((start,start+length,node.get("name") or node.get("kind","constructor")))
                    for child in node.values():
                        visit(child)
                elif isinstance(node,list):
                    for child in node:
                        visit(child)
            visit(source.get("ast",{}))
            sources[source["id"]] = (name,content.encode(),functions)
        for name, contracts in info["output"].get("contracts",{}).items():
            for contract, artifact in contracts.items():
                for kind in ("bytecode","deployedBytecode"):
                    bytecode = artifact.get("evm",{}).get(kind,{})
                    encoded = bytecode.get("object","")
                    if not encoded or "__" in encoded:
                        continue
                    code = bytes.fromhex(encoded.removeprefix("0x"))
                    entries = bytecode.get("sourceMap","").split(";")
                    last = [0,0,-1,"",0]
                    mapping = {}
                    pc = 0
                    for entry in entries:
                        fields = entry.split(":")
                        for i,value in enumerate(fields):
                            if value:
                                last[i] = value if i == 3 else int(value)
                        mapping[pc] = tuple(last)
                        if pc >= len(code):
                            break
                        op = code[pc]
                        pc += 1 + (op-0x5f if 0x60 <= op <= 0x7f else 0)
                    masks = [r for refs in bytecode.get("immutableReferences",{}).values() for r in refs]
                    result.append({"contract":contract,"kind":kind,"code":code,"masks":masks,"map":mapping,"sources":sources,"build_info":str(file),"build_info_sha256":hashlib.sha256(file.read_bytes()).hexdigest()})
    if not result:
        raise ValueError("no full solc build-info/source maps; build with --build-info --ast")
    return result


def match_code(code, catalog, kind="deployedBytecode", contract=None):
    for artifact in catalog:
        if artifact["kind"] != kind or (contract and artifact["contract"] != contract):
            continue
        expected = artifact["code"]
        if kind == "bytecode":
            if code.startswith(expected):
                return artifact
        elif len(expected) == len(code):
            a,b = bytearray(expected),bytearray(code)
            for mask in artifact["masks"]:
                start,end = mask["start"],mask["start"]+mask["length"]
                a[start:end] = b[start:end] = bytes(end-start)
            if a == b:
                return artifact
    return None


def classify(artifact, pc, op, inherited, create):
    if create and op == "SSTORE":
        return "constructor_storage", None, ""
    if not artifact or pc not in artifact["map"]:
        return inherited, None, ""
    start,length,file_id,jump,_ = artifact["map"][pc]
    source = artifact["sources"].get(file_id)
    if not source:
        return inherited, None, jump
    filename,content,functions = source
    names = [(b-a,name) for a,b,name in functions if a <= start and start+length <= b]
    fn = min(names)[1] if names else ""
    fragment = content[max(0,start):max(0,start+length)].decode(errors="replace")
    provenance = (filename,fn,start,length)
    key = (filename+" "+fn).lower()
    category = inherited
    if create and ("p2bb512" in key or "pqtcapplicationhash" in key): category = "constructor_hashing"
    elif "inv" in fn.lower() and "vanishingwithinverse" not in fn.lower(): category = "inverse_calculations"
    elif "mmcs" in key: category = "mmcs_hashing_paths"
    elif "transcript" in key or "_observe" in fn or "_sample" in fn: category = "transcript_challenges"
    elif "codec" in key or "_parse" in fn or "_readextension" in key or fn == "_requireParameter": category = "parse_canonicality"
    elif "airevaluator" in key or ("airstage" in key and fn not in {"requireValid"}): category = "air_evaluation"
    elif "starkood" in key or fn == "requireValid": category = "ood_quotient"
    elif fn in {"_openingAggregates","_dotProductExtension"} or (length < 512 and "alphaPowers" in fragment): category = "alpha_opening_aggregates"
    elif fn in {"_reduceBatch","_dotProductBase"} or (length < 512 and "state.reduced" in fragment): category = "row_reductions"
    elif fn == "_fri" or "friverifier" in key: category = "fri_arithmetic"
    elif fn in {"_validatedPublicValues","_publicValues"} or "pqtcapplicationhash" in key: category = "public_statement"
    if op == "SSTORE":
        if create: category = "constructor_storage"
        elif "registry" in key: category = "checkpoint_storage_deletion"
        elif fn == "_completeWithdrawal" or (length < 512 and "nullifiers" in fragment): category = "nullifier_write"
        else: category = "other_state"
    if op in {"CALL","CALLCODE"} and fn == "_completeWithdrawal": category = "payout_calls"
    return category, provenance, jump


def attribute(out, rpc, catalog, creation_contract=None):
    with gzip.open(out/"opcode-trace.json.gz", "rt") as stream:
        trace = json.load(stream)
    calls = json.loads((out/"call-trace.json").read_text())
    record = json.loads((out/"result.json").read_text())
    logs = trace.get("structLogs")
    if not isinstance(logs,list) or not logs:
        raise ValueError("missing actual opcode trace")
    artifacts = {}
    def resolve(call, root=False):
        if root and creation_contract:
            return match_code((out/"calldata.bin").read_bytes(),catalog,"bytecode",creation_contract)
        address = call.get("to","").lower()
        if address not in artifacts:
            code = bytes.fromhex(rpc.call("eth_getCode",[address,"latest"]).removeprefix("0x")) if address else b""
            artifacts[address] = match_code(code,catalog)
        return artifacts[address]
    # Reverse successor map identifies every frame's next opcode without summing
    # inclusive CALL spans. Child consumption is subtracted from its caller once.
    next_same = [None]*len(logs)
    active = {}
    for i in range(len(logs)-1,-1,-1):
        depth = logs[i]["depth"]
        next_same[i] = active.get(depth)
        active[depth] = i
        for deeper in list(active):
            if deeper > depth:
                del active[deeper]
    totals = collections.Counter({key:0 for key in CATEGORIES})
    opcodes = collections.Counter()
    source_totals = collections.Counter()
    classification_cache = {}
    child_execution_without_opcodes = collections.Counter()
    frames = [{"call":calls,"artifact":resolve(calls,True),"child":0,"phase":"compiler_shared_or_unmapped","jumps":[]}]
    first_depth = logs[0]["depth"]
    pending = None
    for i,row in enumerate(logs):
        depth = row["depth"]-first_depth
        while len(frames)>depth+1:
            frames.pop()
        if len(frames)<depth+1:
            if pending is None:
                raise ValueError("opcode/call trace depth mismatch")
            frames.append({"call":pending,"artifact":resolve(pending),"child":0,"phase":frames[-1]["phase"],"jumps":[]})
        frame = frames[-1]
        op = row["op"]
        cache_key = (id(frame["artifact"]),row["pc"],op,frame["phase"])
        if cache_key not in classification_cache:
            classification_cache[cache_key] = classify(frame["artifact"],row["pc"],op,frame["phase"],bool(creation_contract))
        category,where,jump = classification_cache[cache_key]
        if category != "compiler_shared_or_unmapped":
            frame["phase"] = category
        child_gas = 0
        pending = None
        if op in {"CALL","STATICCALL","DELEGATECALL","CALLCODE","CREATE","CREATE2"}:
            children = frame["call"].get("calls",[])
            if frame["child"] < len(children):
                pending = children[frame["child"]]
                frame["child"] += 1
                child_gas = number(pending.get("gasUsed",0))
        successor = next_same[i]
        if successor is not None:
            charged = number(row["gas"])-number(logs[successor]["gas"])
            exclusive = charged-child_gas
        else:
            exclusive = number(row.get("gasCost",0))
            if op in {"CALL","STATICCALL","DELEGATECALL","CALLCODE","CREATE","CREATE2"}:
                exclusive -= child_gas
        if exclusive < 0:
            raise ValueError(f"negative exclusive opcode gas at {i}; trace accounting incompatible")
        totals[category] += exclusive
        opcodes[op] += exclusive
        source_totals[(category,*(where or ("<generated>","",-1,0)))] += exclusive
        if child_gas and (i+1 == len(logs) or logs[i+1]["depth"] <= row["depth"]):
            # Precompiles/empty-code calls can consume gas without structLogs.
            # Their parent CALL delta was already reduced by this child amount.
            totals[category] += child_gas
            child_execution_without_opcodes[category] += child_gas
        if op == "JUMP" and jump == "i":
            frame["jumps"].append(category)
        elif op == "JUMP" and jump == "o" and frame["jumps"]:
            frame["phase"] = frame["jumps"].pop()
    opcode_total = sum(totals.values())
    result = {"measurement_class":"MEASURED","method":"solc PC/source-map and AST attribution; per-opcode gas deltas less child call gas; internal jump-context propagation","opcode_steps":len(logs),"exclusive_categories":dict(totals),"exclusive_opcode_gas":dict(opcodes),"exclusive_execution_gas":opcode_total,"call_totals_overlap":"call-trace.json is inclusive; NEVER sum it with these exclusive categories","source_attribution":[{"category":k[0],"file":k[1],"function":k[2],"start":k[3],"length":k[4],"gas":v} for k,v in sorted(source_totals.items())],"trace_sha256":record["trace_sha256"],"build_provenance":[{"path":a["build_info"],"sha256":a["build_info_sha256"]} for a in catalog],"receipt_gas":record["gas_used"],"intrinsic":record["intrinsic"],"code_deposit_gas":record.get("code_deposit_gas",0)}
    result["child_execution_without_opcodes"] = dict(child_execution_without_opcodes)
    result["compiled_bytecode_provenance"] = [{"contract":a["contract"],"kind":a["kind"],"sha256":hashlib.sha256(a["code"]).hexdigest()} for a in catalog]
    result["receipt_reconciliation_residual"] = record["gas_used"]-record["intrinsic"]["standard_intrinsic"]-opcode_total-record.get("code_deposit_gas",0)
    result["residual_semantics"] = "Kept separate: refunds, EIP-7623 floor, exceptional halt gas and code-deposit/trace conventions. Not falsely attributed to a phase. Optimizer-shared locations retain jump context; generated/unmapped bytes remain explicit."
    write_json(out/"gas-ledger.json",result)
    return result


def load_prestate(rpc, path):
    raw = json.loads(path.read_text())
    alloc = raw.get("alloc",raw.get("accounts",raw))
    for address, account in alloc.items():
        if not isinstance(account,dict):
            continue
        address = "0x"+address.removeprefix("0x")
        if "code" in account: rpc.call("anvil_setCode",[address,"0x"+account["code"].removeprefix("0x")])
        if "balance" in account: rpc.call("anvil_setBalance",[address,hex(number(account["balance"]))])
        if "nonce" in account: rpc.call("anvil_setNonce",[address,hex(number(account["nonce"]))])
        for slot,value in account.get("storage",{}).items():
            rpc.call("anvil_setStorageAt",[address,"0x"+slot.removeprefix("0x").zfill(64),"0x"+value.removeprefix("0x").zfill(64)])
