#!/usr/bin/env python3
"""R2-05 local-only proof, parity, mutation and full transaction experiment.
No node is spawned; Main supplies a disposable Anvil endpoint and serializes runs.
"""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, subprocess, sys, tempfile, time, urllib.request, urllib.parse
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'research/harness/report-generator'))
from keccak import keccak256
PUBLIC = '0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266'

def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')

def clean_env():
    allowed = {'PATH','HOME','TMPDIR','RUSTUP_HOME','CARGO_HOME','RUSTUP_TOOLCHAIN','RUSTFLAGS','CARGO_BUILD_JOBS','RAYON_NUM_THREADS','SDKROOT','MACOSX_DEPLOYMENT_TARGET','CC','CXX','AR'}
    return {k:v for k,v in os.environ.items() if k in allowed}

def command(args, out, name, cwd=ROOT):
    env = clean_env(); env['CARGO_TARGET_DIR'] = str(HERE/'target')
    started = time.monotonic()
    p = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True)
    (out/(name+'.stdout.log')).write_text(p.stdout); (out/(name+'.stderr.log')).write_text(p.stderr)
    dump(out/(name+'.command.json'), {'argv':args,'cwd':str(cwd),'exit_status':p.returncode,'elapsed_seconds':time.monotonic()-started,'environment_keys':sorted(env)})
    if p.returncode: raise RuntimeError(f'{name} failed; see raw logs')

def build_solidity(out, queries=32):
    solidity=HERE/"solidity"
    if queries==48:
        from q48 import materialize
        solidity=materialize()
    # Explicit allowlist copy prevents Foundry's dotenv discovery reaching the repository.
    with tempfile.TemporaryDirectory(prefix='pqtc-r2-transcript-',dir='/tmp') as tmp:
        tree=Path(tmp);package=tree/solidity.relative_to(ROOT)
        for source,target in [(ROOT/'contracts/src',tree/'contracts/src'),(solidity/'src',package/'src')]:
            for p in source.rglob('*.sol'):
                q=target/p.relative_to(source);q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(p.read_bytes())
        shutil.copyfile(solidity/'foundry.toml',package/'foundry.toml')
        dump(out/'solidity-sources.json',{str(p.relative_to(tree)):hashlib.sha256(p.read_bytes()).hexdigest() for p in tree.rglob('*.sol')})
        command(['forge','build','--root',str(package)],out,'solidity-build',cwd=package)
        generated=solidity/'out'
        if generated.exists():shutil.rmtree(generated)
        shutil.copytree(package/'out',generated)

class RPC:
    def __init__(self, url, out, diagnostic, queries=32):
        self.solidity=HERE/("q48/solidity" if queries==48 else "solidity")
        parsed = urllib.parse.urlparse(url)
        if parsed.hostname not in ('127.0.0.1','localhost','::1') or parsed.scheme != 'http': raise ValueError('loopback HTTP only')
        self.url, self.out, self.counter, self.diagnostic = url, out, 0, diagnostic
        if int(self.call('eth_chainId'),16) != 31337 or 'anvil' not in self.call('web3_clientVersion').lower(): raise ValueError('disposable Anvil chain31337 required')
        self.accounts = self.call('eth_accounts')
        if self.accounts[0].lower() != PUBLIC: raise ValueError('public test accounts required')
        self.gas = 900_000_000 if diagnostic else 16_777_216
    def call(self, method, params=None):
        self.counter += 1; request = {'jsonrpc':'2.0','id':self.counter,'method':method,'params':params or []}
        with urllib.request.urlopen(urllib.request.Request(self.url,json.dumps(request).encode(),{'Content-Type':'application/json'}), timeout=600) as r: response = json.load(r)
        with (self.out/'rpc.jsonl').open('a') as log: log.write(json.dumps({'request':request,'response':response})+'\n')
        if 'error' in response: raise RuntimeError(json.dumps(response['error']))
        return response['result']
    def eth_call(self, address, data, sender=PUBLIC):
        return self.call('eth_call',[{'from':sender,'to':address,'data':'0x'+data.hex(),'gas':hex(self.gas)},'latest'])
    def transaction(self, name, data, address=None):
        tx={'from':PUBLIC,'data':'0x'+data.hex(),'gas':hex(self.gas),'value':'0x0'}
        if address: tx['to']=address
        result={'measurement_class':'diagnostic_prague_uncapped' if self.diagnostic else 'capped_osaka_signed_local_transaction','abi_bytes':len(data),'zero_bytes':data.count(0),'nonzero_bytes':len(data)-data.count(0),'rpc_url':self.url,'promotion':False}
        try:
            txid=self.call('eth_sendTransaction',[tx]); result['transaction_hash']=txid
            for _ in range(600):
                receipt=self.call('eth_getTransactionReceipt',[txid])
                if receipt: break
                time.sleep(.1)
            else: raise RuntimeError('receipt timeout')
            result.update(receipt=receipt,status='MEASURED',success=int(receipt['status'],16)==1,gas_used=int(receipt['gasUsed'],16))
            try:
                raw=self.call('eth_getRawTransactionByHash',[txid]); result['signed_envelope_bytes']=(len(raw)-2)//2; (self.out/(name+'.signed.hex')).write_text(raw+'\n')
            except RuntimeError as e: result.update(signed_envelope_bytes=None,signed_envelope_error=str(e))
        except RuntimeError as e: result.update(status='EXECUTION_BLOCKED',success=False,error=str(e),gas_used=None,signed_envelope_bytes=None)
        dump(self.out/(name+'.json'),result); return result

def word(value): return int(value).to_bytes(32,'big')
def hx(value): return bytes.fromhex(value.removeprefix('0x'))
def call_data(signature, static=b'', dynamic=()):
    head=bytearray(static);tail=bytearray();offset=len(static)+32*len(dynamic)
    for d in dynamic: head+=word(offset+len(tail));tail+=word(len(d))+d+b'\0'*((-len(d))%32)
    return keccak256(signature.encode())[:4]+head+tail

def artifact(name, solidity):
    matches=list((solidity/'out').glob('*/'+name+'.json'))
    if len(matches)!=1: raise RuntimeError(f'nonunique artifact {name}: {matches}')
    return json.loads(matches[0].read_text())

def deploy(rpc, name, args=b'', label=None):
    a=artifact(name,rpc.solidity); bytecode=hx(a['bytecode']['object']); result=rpc.transaction(label or ('deploy-'+name),bytecode+args)
    result.update(initcode_bytes=len(bytecode+args),compiled_runtime_bytes=len(hx(a['deployedBytecode']['object'])),artifact_sha256=hashlib.sha256(json.dumps(a,sort_keys=True).encode()).hexdigest())
    if result['success']:
        address=result['receipt']['contractAddress'];runtime=hx(rpc.call('eth_getCode',[address,'latest']));result.update(address=address,runtime_bytes=len(runtime),runtime_sha256=hashlib.sha256(runtime).hexdigest())
    dump(rpc.out/((label or 'deploy-'+name)+'.json'),result)
    return result.get('address'),result

def rejected(rpc,address,data,sender=PUBLIC):
    try: rpc.eth_call(address,data,sender); return False
    except RuntimeError: return True

def oracle(rpc,native):
    address,deployment=deploy(rpc,'TranscriptOracle');result={'deployment':deployment}
    if not address: return result
    v=json.loads((native/'transcript-vectors.json').read_text());program=(rpc.out/'typescript.json.program').read_bytes();parameter=hx(v['parameter_id']);pv=word(64)+b''.join(word(x) for x in v['public_values'])
    # uint32[] ABI is dynamic; encode its already length-prefixed array separately.
    def oracle_call(sig, p):
        h=parameter+word(128)+word(128+len(pv));return keccak256(sig.encode())[:4]+h+pv+word(len(p))+p+b'\0'*((-len(p))%32)
    data=oracle_call('replay((bytes32,bytes32),uint32[],bytes)',program)
    try:
        encoded=hx(rpc.eth_call(address,data)); first=int.from_bytes(encoded[:32],'big');second=int.from_bytes(encoded[32:64],'big')
        samples=encoded[first+32:first+32+int.from_bytes(encoded[first:first+32],'big')];states=encoded[second+32:second+32+int.from_bytes(encoded[second:second+32],'big')]
        expected=[e for e in v['events'] if e['operation']!='frame']
        assert samples==b''.join(int(e['value']).to_bytes(4,'big') for e in expected)
        assert states==b''.join(bytes.fromhex(e['after']) for e in expected)
        assert int.from_bytes(encoded[64:96],'big')==sum(len(e['rejected']) for e in expected)
        result['parity']={'status':'MEASURED','accepted':True,'samples':len(expected),'rejected_words':int.from_bytes(encoded[64:96],'big')}
        mutations={'early':b'\x01','missing':program[:-2],'trailing':program+b'\xff'}
        # first real frame starts at0: op/epoch2/slot2/type/length2/value4.
        for name,at,value in [('cross_phase',2,1),('reordered',4,1),('wrong_type',5,2),('length',7,0)]:
            m=bytearray(program);m[at]=value;mutations[name]=bytes(m)
        mutations['duplicate']=program[:12]+program
        m=bytearray(program);m[8:12]=(2013265921).to_bytes(4,'big');mutations['noncanonical']=bytes(m)
        result['mutations']={n:rejected(rpc,address,oracle_call('replay((bytes32,bytes32),uint32[],bytes)',p)) for n,p in mutations.items()}
        assert all(result['mutations'].values())
    except RuntimeError as e: result['parity']={'status':'EXECUTION_BLOCKED','error':str(e)}
    result['isolated_framed']=rpc.transaction('isolated-framed',data,address)
    result['isolated_frozen']=rpc.transaction('isolated-frozen',oracle_call('frozenReplay((bytes32,bytes32),uint32[],bytes)',program),address)
    result['attribution']='same typed observations/sample schedule, different cryptographic transcript; isolated delta is not summed into full path'
    return result

def exercise(rpc, registry, directory, parameter, pv, first, lifecycle=True):
    row=json.loads((directory/'results.json').read_text());a=(directory/'part-a.calldata').read_bytes();b=(directory/'part-b.calldata').read_bytes();id=hx(row['verification_id']);result={}
    snapshot=rpc.call('evm_snapshot')
    result['part_a']=rpc.transaction(f'{first}-a',a,registry)
    if result['part_a']['success']:
        if lifecycle:
            expiry_data=call_data('expiresAt(bytes32)',id);expiry=rpc.eth_call(registry,expiry_data)
            result['idempotent_a']=rpc.transaction(f'{first}-idempotent-a',a,registry);assert rpc.eth_call(registry,expiry_data)==expiry
            assert rejected(rpc,registry,b,rpc.accounts[1]);result['consumer_rejection']=True
            mutations=[]
            for part,name in [(0,'part-a'),(1,'part-b')]:
                original=(directory/(name+'.pqtc')).read_bytes()
                raw_offset=4+int.from_bytes((a if part==0 else b)[4+(66 if part==0 else 67)*32:4+(67 if part==0 else 68)*32],'big')+32
                for item in row['mutations']:
                    if item['part']!=part or 'offset' not in item: continue
                    mutated=bytearray(a if part==0 else b);mutated[raw_offset+item['offset']]^=1
                    ok=rejected(rpc,registry,mutated);assert ok;mutations.append({**item,'solidity_rejected':ok})
            result['mutations']=mutations
        result['part_b']=rpc.transaction(f'{first}-b',b,registry)
        if result['part_b']['success']:
            assert rejected(rpc,registry,b);result['completed_session_replay_rejected']=True
        if lifecycle:
            rpc.call('evm_revert',[snapshot]);snapshot=rpc.call('evm_snapshot')
            again=rpc.transaction(f'{first}-lifecycle-a',a,registry)
            if again['success']:
                assert rejected(rpc,registry,call_data('cleanupExpired(bytes32)',id));rpc.call('anvil_mine',['0x40'])
                assert rejected(rpc,registry,b);cleanup=rpc.transaction(f'{first}-cleanup',call_data('cleanupExpired(bytes32)',id),registry);assert cleanup['success']
                result['lifecycle']={'expires_after_blocks':64,'early_cleanup_rejected':True,'expired_completion_rejected':True,'permissionless_cleanup':cleanup}
                restart=rpc.transaction(f'{first}-replacement-a',a,registry);result['replacement']=restart
                if restart['success']:
                    assert int(rpc.eth_call(registry,call_data('expiresAt(bytes32)',id)),16)>0
                    result['cancel']=rpc.transaction(f'{first}-cancel',call_data('cancelVerification(bytes32)',id),registry)
    rpc.call('evm_revert',[snapshot])
    if (directory/'one-call.calldata').exists():result['one_call']=rpc.transaction(f'{first}-onecall',(directory/'one-call.calldata').read_bytes(),registry)
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--rpc-url',required=True);p.add_argument('--queries',type=int,choices=[32,48],default=32);p.add_argument('--out',type=Path,default=HERE/'outputs');p.add_argument('--input',type=Path,default=ROOT/'research/candidates/v03-baseline/proofs/v03-fixed-01');p.add_argument('--native-dir',type=Path);p.add_argument('--skip-build',action='store_true');p.add_argument('--diagnostic',action='store_true');args=p.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    rpc=RPC(args.rpc_url,out,args.diagnostic,args.queries);native=args.native_dir.resolve() if args.native_dir else out/'native'
    if not args.native_dir: command(['cargo','run','--release','--manifest-path',str(HERE/'rust/Cargo.toml'),*(['--features','q48'] if args.queries==48 else []),'--','--input',str(args.input.resolve()),'--out',str(native),'--compare-frozen'],out,'native')
    if not args.skip_build:build_solidity(out,args.queries)
    command(['node',str(HERE/'transcript.ts'),str(native/'transcript-vectors.json'),str(out/'typescript.json')],out,'typescript')
    command(['node',str(HERE/'codec.ts'),str(native),str(out/'typescript-codec.json')],out,'typescript-codec')
    results=json.loads((native/'results.json').read_text());parameter=hx(results['parameter_id']);pv=results['public_values'];deployments=[];paths=[]
    if results['query_count']!=args.queries:raise ValueError('native/verifier query-count mismatch')
    air,d=deploy(rpc,'R2TranscriptAir');deployments.append(d)
    if air:
        for first in [row['first_queries'] for row in results['splits']]:
            qa,d=deploy(rpc,'R2TranscriptQuery',word(first),f'deploy-query-{first}a');deployments.append(d)
            qb,d=deploy(rpc,'R2TranscriptQuery',word(args.queries-first),f'deploy-query-{first}b');deployments.append(d)
            if not qa or not qb:continue
            registry,d=deploy(rpc,'R2TranscriptRegistry',hx(air).rjust(32,b'\0')+hx(qa).rjust(32,b'\0')+hx(qb).rjust(32,b'\0')+parameter,f'deploy-registry-{first}');deployments.append(d)
            if registry:paths.append({'split':[first,args.queries-first],'registry':registry,**exercise(rpc,registry,native/f'split-{first}',parameter,pv,str(first))})
    isolated=oracle(rpc,native)
    control=None
    if args.queries==32 and (native/'frozen-control').exists():
        ca,d=deploy(rpc,'R2FrozenAir');deployments.append(d);cq,d=deploy(rpc,'R2FrozenQuery');deployments.append(d)
        if ca and cq:
            cr,d=deploy(rpc,'R2FrozenRegistry',hx(ca).rjust(32,b'\0')+hx(cq).rjust(32,b'\0')+parameter);deployments.append(d)
            if cr:control=exercise(rpc,cr,native/'frozen-control',parameter,pv,'control',False)
    deltas=[]
    if control and control.get('part_a',{}).get('success') and control.get('part_b',{}).get('success'):
        base=control['part_a']['gas_used']+control['part_b']['gas_used']
        for row in paths:
            if row.get('part_a',{}).get('success') and row.get('part_b',{}).get('success'):deltas.append({'split':row['split'],'integrated_two_call_gas_delta':row['part_a']['gas_used']+row['part_b']['gas_used']-base,'baseline_measured_two_call_gas':base,'attribution':'whole-path T3-02+full512+split, not sum of isolated kernels'})
    measured=[{'split':row['split'],'worst_call_gas':max(row['part_a']['gas_used'],row['part_b']['gas_used']),'combined_gas':row['part_a']['gas_used']+row['part_b']['gas_used']} for row in paths if row.get('part_a',{}).get('success') and row.get('part_b',{}).get('success')]
    dump(out/'balanced-work.json',{'query_count':args.queries,'measurement_class':'diagnostic_prague_uncapped' if args.diagnostic else 'capped_osaka_signed_local_transaction','observed':measured,'selected':min(measured,key=lambda row:row['worst_call_gas']) if measured else None,'status':'MEASURED' if measured else 'NOT_EVALUATED','rule':'minimum measured max(A,B); no query-linear extrapolation','promotion':False})
    dump(out/'results.json',{'package':'R2-05','pipeline':'R2-C0','query_count':args.queries,'specification_status':f'T3-02 q{args.queries} exact schedule, H0 predicate unchanged','correctness_evidence':{'native':str(native/'results.json'),'typescript':str(out/'typescript.json'),'solidity':isolated,'paths':paths},'privacy_evidence':'upstream hiding construction; no external qualification','security_status':'EXPERIMENTAL_UNQUALIFIED','performance_evidence':{'deployments':deployments,'paths':paths,'frozen_control':control,'differential':deltas,'isolated':isolated},'implementation_stage':'local_executable_measurement','promotion_status':'NOT_READY_FOR_BUILD_SELECTION','command':sys.argv,'rpc_url':args.rpc_url,'measurement_class':'diagnostic_prague_uncapped' if args.diagnostic else 'capped_osaka_signed_local_transaction','optimization_count':1,'optimization':'typed challenge-epoch batching','comparison_warning':'Security width/split overhead is included in integrated comparison; no additive kernel claim'})
if __name__=='__main__':main()
