#!/usr/bin/env python3
"""R2-02 executable parity/misuse/measurement, local unlocked PUBLIC dev accounts only.
Main starts Anvil. No wallet, environment files, public RPC, or expected-output proof oracle.
"""
import argparse,collections,gzip,hashlib,json,os,random,shutil,subprocess,sys,tempfile,time,urllib.request,urllib.parse
from pathlib import Path
from compare_constants import clean_env
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[2]
OUT=ROOT/'outputs'
ARTIFACTS=ROOT/'solidity/out'
P=2013265921
CONFIGS=['R2-H0-v03','R2-H5-complete-v1']
TIERS={'R2-H0-v03':['H0Reference','H0Optimized'],'R2-H5-complete-v1':['H5Reference','H5Packed','H5Straight']}

def file_sha256(path):
    with path.open('rb')as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def dump(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2)+'\n')
def word(x):return int(x).to_bytes(32,'big')
def array(values):return word(len(values))+b''.join(word(x)for x in values)
def decode_array(raw):
    data=bytes.fromhex(raw.removeprefix('0x'));off=int.from_bytes(data[:32],'big');n=int.from_bytes(data[off:off+32],'big');assert len(data)>=off+32+32*n;return [int.from_bytes(data[off+32+i*32:off+64+i*32],'big')for i in range(n)]
def decode_nested(raw):
    data=bytes.fromhex(raw.removeprefix('0x'));off=int.from_bytes(data[:32],'big');n=int.from_bytes(data[off:off+32],'big');base=off+32;out=[]
    for i in range(n):
        at=base+int.from_bytes(data[base+32*i:base+32*i+32],'big');size=int.from_bytes(data[at:at+32],'big');out.append([int.from_bytes(data[at+32+j*32:at+64+j*32],'big')for j in range(size)])
    return out

def nested(values):
    bodies=[array(v)for v in values];offset=32*len(values);heads=[]
    for b in bodies:heads.append(word(offset));offset+=len(b)
    return word(len(values))+b''.join(heads+bodies)

class RPC:
    def __init__(self,url,label,gas):
        parsed=urllib.parse.urlparse(url)
        if parsed.scheme!='http' or parsed.hostname not in ('127.0.0.1','localhost','::1') or parsed.username or parsed.password:raise ValueError('local disposable HTTP endpoint required')
        self.url=url;self.label=label;self.gas=gas;self.seq=0;self.signatures={};self.log=(OUT/f'{label}-rpc.jsonl').open('w')
        assert int(self.call('eth_chainId',[]),16)==31337,'chain31337 required'
        assert 'anvil' in self.call('web3_clientVersion',[]).lower(),'disposable Anvil required'
        self.account=self.call('eth_accounts',[])[0]
        assert self.account.lower()=='0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266','public default development account required'
    def call(self,method,params):
        self.seq+=1;request={'jsonrpc':'2.0','id':self.seq,'method':method,'params':params}
        data=json.dumps(request).encode();start=time.monotonic_ns()
        with urllib.request.urlopen(urllib.request.Request(self.url,data,{'Content-Type':'application/json'}),timeout=600)as response:result=json.load(response)
        # Trace payloads live in separate artifacts; ordinary requests/results include synthetic input provenance.
        self.log.write(json.dumps({'request':request,'response':result if method!='debug_traceTransaction' else {'trace_artifact_id':self.seq,'error':result.get('error')},'elapsed_ns':time.monotonic_ns()-start})+'\n');self.log.flush()
        if 'error'in result:raise RuntimeError(json.dumps(result['error']))
        return result['result']
    def sig(self,text):
        if text not in self.signatures:self.signatures[text]=bytes.fromhex(self.call('web3_sha3',['0x'+text.encode().hex()])[2:10])
        return self.signatures[text]
    def ethcall(self,to,data):return self.call('eth_call',[{'to':to,'data':'0x'+data.hex(),'gas':hex(self.gas)},'latest'])
    def encoded(self,r):return self.sig('evaluate(uint256,uint256,uint256[])')+word(r['role'])+word(r['level'])+word(96)+array(r['payload'])
    def evaluate(self,address,r):return decode_array(self.ethcall(address,self.encoded(r)))
    def batch(self,address,requests):
        args=[array([r['role']for r in requests]),array([r['level']for r in requests]),nested([r['payload']for r in requests])];offset=96;heads=[]
        for b in args:heads.append(word(offset));offset+=len(b)
        data=self.sig('batch(uint256[],uint256[],uint256[][])')+b''.join(heads+args)
        return decode_nested(self.ethcall(address,data))
    def transact(self,data,to=None):
        tx={'from':self.account,'data':'0x'+data.hex(),'gas':hex(self.gas),'value':'0x0'}
        if to:tx['to']=to
        txhash=self.call('eth_sendTransaction',[tx]);receipt=None
        for _ in range(600):
            receipt=self.call('eth_getTransactionReceipt',[txhash])
            if receipt:break
            time.sleep(.1)
        if receipt is None:raise RuntimeError('receipt timeout')
        return receipt
    def deploy(self,name,args=b''):
        artifact=json.loads((ARTIFACTS/('Deposit.sol'if name=='Deposit'else'Roles.sol')/(name+'.json')).read_text());code=bytes.fromhex(artifact['bytecode']['object'].removeprefix('0x'))
        initcode=code+args;zero=initcode.count(0);nonzero=len(initcode)-zero;metering=2*((len(initcode)+31)//32)
        metadata={'initcode_bytes':len(initcode),'initcode_zero_bytes':zero,'initcode_nonzero_bytes':nonzero,'initcode_word_metering_gas':metering,'intrinsic_gas_without_floor':53000+4*zero+16*nonzero+metering,'eip7623_calldata_floor_threshold':21000+10*(zero+4*nonzero),'floor_note':'threshold competes with execution-inclusive total, never added to it','artifact_runtime_template_bytes':len(artifact['deployedBytecode']['object'].removeprefix('0x'))//2,'artifact_sha256':hashlib.sha256(json.dumps(artifact,sort_keys=True).encode()).hexdigest()}
        evidence=OUT/'initcode'/(self.label+'-'+name+'-'+hashlib.sha256(initcode).hexdigest()+'.json')
        record={'initcode':'0x'+initcode.hex(),'metadata':metadata};dump(evidence,record)
        try:receipt=self.transact(initcode)
        except RuntimeError as e:record['error']=str(e);dump(evidence,record);raise
        record['receipt']=receipt
        if int(receipt['status'],16)==1:
            runtime=self.call('eth_getCode',[receipt['contractAddress'],'latest']);metadata['actual_runtime_bytes']=len(runtime[2:])//2;metadata['runtime_code_deposit_gas']=200*metadata['actual_runtime_bytes'];record['runtime']=runtime
        dump(evidence,record)
        return receipt,metadata

class Native:
    def __init__(self,binary):
        self.children=[]
        for name,argv in [('rust',[str(binary.resolve())]),('typescript',['node','--experimental-strip-types',str(ROOT/'reference.ts')])]:
            stderr=(OUT/f'{name}.stderr').open('w');p=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=stderr,text=True,env=clean_env(),bufsize=1);self.children.append((name,p,stderr))
    def evaluate(self,r):
        results={}
        for name,p,_ in self.children:
            p.stdin.write(json.dumps(r)+'\n');p.stdin.flush();line=p.stdout.readline()
            if not line:raise RuntimeError(f'{name} stopped: {p.poll()}')
            results[name]=json.loads(line)
        return results
    def close(self):
        for _,p,stderr in self.children:p.stdin.close();p.wait(timeout=60);stderr.close()

def request(config,role,payload,level=0):return {'config':config,'role':role,'level':level,'payload':payload}
def full_vectors(count):
    rng=random.Random(20010032)
    for i in range(count):
        config=CONFIGS[i%2];role=1+(i//2)%7;d=16 if i%2==0 else 12;n=[0,65,d+16,d+8,d,2*d,36,4*d][role]
        limit=65536 if role in (1,6)else P
        p=[rng.randrange(limit)for _ in range(n)]
        # Edge corpora retain asymmetry for order-sensitive roles.
        if i<14:p=[0]*n
        elif i<28:p=[limit-1]*n
        elif i<42:p=[j%limit for j in range(n)]
        if role==1:p[-1]&=65280
        yield request(config,role,p,(i//14)%20 if role==5 else 0)

def check(native,r,rpc,addresses,expected_error=False):
    answers=native.evaluate(r)
    for tier,address in addresses[r['config']].items():
        try:answers[tier]={'output':rpc.evaluate(address,r)}
        except (RuntimeError,OverflowError,ValueError,TypeError)as e:answers[tier]={'error':str(e)}
    if expected_error:
        assert all('error'in value for value in answers.values()),answers
    else:
        assert all('output'in value for value in answers.values()),answers
        outputs=[v['output']for v in answers.values()];assert all(x==outputs[0]for x in outputs),answers
    return answers

def misuse(native,rpc,addresses):
    cases=[]
    for config in CONFIGS:
        d=16 if config==CONFIGS[0]else 12
        note=request(config,2,list(range(1,d+17)));node=request(config,5,list(range(1,2*d+1)),3)
        for label,base,mut in [
            ('domain-swap',note,{**note,'role':3}),('payload-count',note,{**note,'payload':note['payload'][:-1]}),
            ('secret-width',note,{**note,'payload':note['payload'][:d+7]+note['payload'][d+8:]}),
            ('trapdoor-width',note,{**note,'payload':note['payload']+[1]}),
            ('field-at-modulus',note,{**note,'payload':[P]+note['payload'][1:]}),
            ('field-above-modulus',note,{**note,'payload':[P+1]+note['payload'][1:]}),
            ('scope-odd-padding',note,request(config,1,[0]*64+[1])),
            ('public-byte-lane-overflow',note,request(config,6,[65536]+[0]*35)),
            ('wrong-level-range',node,{**node,'level':20})]:
            cases.append({'config':config,'case':label,'actual':check(native,mut,rpc,addresses,True)})
        for label,base,mut in [
            ('scope-swap',note,{**note,'payload':[99]+note['payload'][1:]}),
            ('scope-omitted-note',note,{**note,'payload':[0]*d+note['payload'][d:]}),
            ('level-change',node,{**node,'level':4}),
            ('child-order',node,{**node,'payload':node['payload'][d:]+node['payload'][:d]}),
            ('note-nullifier-reinterpretation',note,request(config,3,note['payload'][:d+8])),
            ('empty-node-confusion',request(config,4,list(range(1,d+1))),node),
            ('endian-swap',request(config,6,list(range(1,37))),request(config,6,[x<<8 for x in range(1,37)]))]:
            before=check(native,base,rpc,addresses);after=check(native,mut,rpc,addresses);assert before['rust']['output']!=after['rust']['output'],label;cases.append({'config':config,'case':label,'before':before,'after':after})
        scope_fields=list(range(65));scope_fields[-1]=256
        s1=check(native,request(config,1,scope_fields),rpc,addresses)['rust']['output'];scope_fields[-2]^=1;s2=check(native,request(config,1,scope_fields),rpc,addresses)['rust']['output'];assert s1!=s2
        cases.append({'config':config,'case':'parameter-context-swap','scope_before':s1,'scope_after':s2})
        for role,tail in [(2,[1]*16),(3,[1]*8),(4,[]),(7,[1]*(3*d))]:
            a=check(native,request(config,role,s1+tail),rpc,addresses);b=check(native,request(config,role,[0]*d+tail),rpc,addresses);assert a['rust']['output']!=b['rust']['output'];cases.append({'config':config,'case':f'scope-omitted-role-{role}','before':a,'after':b})
        # Ill-formed Solidity calldata is sent to the actual ABI decoder, not counted as host-encoder rejection.
        malformed={}
        for tier,address in addresses[config].items():
            try:rpc.ethcall(address,rpc.sig('evaluate(uint256,uint256,uint256[])')+word(2));raise AssertionError('ABI truncation accepted')
            except RuntimeError as e:malformed[tier]={'error':str(e)}
        wire=native.evaluate({**note,'payload':['malformed']+note['payload'][1:]});assert all('error'in x for x in wire.values());cases.append({'config':config,'case':'malformed-field-wire-and-abi','native':wire,'solidity':malformed})
    config=CONFIGS[1];state=list(range(1,25))+[5,2001,24,3]+[0]*4
    good=check(native,request(config,9,state),rpc,addresses)
    bad=state.copy();bad[28]=1;fixed=check(native,request(config,9,bad),rpc,addresses);assert good['rust']['output']!=fixed['rust']['output'];cases.append({'config':config,'case':'fixed-lane-mutation','before':good,'after':fixed})
    for label,lane,value in [('control-domain',24,4),('control-version',25,2002),('control-payload-count',26,23),('control-level',27,4)]:
        changed=state.copy();changed[lane]=value;actual=check(native,request(config,9,changed),rpc,addresses);assert actual['rust']['output']!=good['rust']['output'];cases.append({'config':config,'case':label,'actual':actual})
    for role,label in [(10,'wrong-feedforward-lane'),(11,'wrong-truncation')]:
        faulty=check(native,request(config,role,state),rpc,addresses)
        assert all(value['output']!=good[name]['output']for name,value in faulty.items())
        cases.append({'config':config,'case':label,'actual_normal_compression':good,'actual_fault_injection_kernel':faulty})
    dump(OUT/'misuse.json',{'cases':cases,'passed':True,'security':'not-qualified'});return len(cases)

def trace(rpc,receipt,label):
    options={'disableStorage':True,'disableMemory':True,'disableStack':True}
    # A full high-gas constructor trace disconnected in resume-full-02. Retain a bounded repair separately.
    if int(receipt['gasUsed'],16)>16777216:options['limit']=200000
    try:
        result=rpc.call('debug_traceTransaction',[receipt['transactionHash'],options])
    except (OSError,RuntimeError) as error:
        failure={'measurement_status':'EXECUTION_BLOCKED','transaction_hash':receipt['transactionHash'],'receipt_gas':int(receipt['gasUsed'],16),'options':options,'error':str(error),'opcode_attribution':None,'scope':'Trace acquisition failed; transaction receipt remains measured. Continue independent parity and cost experiments.'}
        dump(OUT/'traces'/(label+'-error.json'),failure)
        return failure
    path=OUT/'traces'/(label+'.json.gz');path.parent.mkdir(parents=True,exist_ok=True)
    with gzip.open(path,'wt')as stream:json.dump(result,stream,separators=(',',':'))
    categories={'arithmetic':{'ADD','SUB','MUL','DIV','MOD','ADDMOD','MULMOD','EXP'},'dispatch':{'JUMP','JUMPI','JUMPDEST','PC'},'memory':{'MLOAD','MSTORE','MSTORE8','MCOPY','MSIZE'},'storage':{'SLOAD','SSTORE','TLOAD','TSTORE'},'calls_abi':{'CALL','STATICCALL','DELEGATECALL','CALLCODE','CREATE','CREATE2','RETURN','RETURNDATACOPY','CALLDATACOPY','CALLDATALOAD','CALLDATASIZE','CODECOPY'},'hash':{'KECCAK256','SHA3'}}
    counts=collections.Counter();costs=collections.Counter()
    for row in result.get('structLogs',[]):counts[row['op']]+=1;costs[row['op']]+=int(row['gasCost'],0)if isinstance(row['gasCost'],str)else row['gasCost']
    attribution={name:{'opcodes':sum(counts[x]for x in ops),'reported_gas_cost':sum(costs[x]for x in ops)}for name,ops in categories.items()}
    return {'receipt_gas':int(receipt['gasUsed'],16),'opcode_counts':dict(counts),'opcode_reported_costs':dict(costs),'categories':attribution,'trace_path':str(path.relative_to(OUT)),'trace_options':options,'trace_complete':not options.get('limit')or len(result.get('structLogs',[]))<options['limit'],'classification':'overlapping opcode attribution, not additive causal deltas; limited traces are partial attribution only; CALL cost includes callee budget; constant access overlaps memory/dispatch; source strategies alone do not establish causal gas savings'}

def deploy_tiers(rpc,do_trace):
    addresses={c:{}for c in CONFIGS};records=[]
    for config,names in TIERS.items():
        for tier in names:
            record={'config':config,'tier':tier,'measurement_class':rpc.label}
            try:
                receipt,meta=rpc.deploy(tier);record.update(receipt=receipt,**meta)
                if do_trace:record['constructor_attribution']=trace(rpc,receipt,rpc.label+'-'+tier+'-implementation-constructor')
                if int(receipt['status'],16)==1:
                    address=receipt['contractAddress'];addresses[config][tier]=address;code=rpc.call('eth_getCode',[address,'latest']);record['actual_runtime_bytes']=len(code[2:])//2;record['actual_runtime_sha256']=hashlib.sha256(bytes.fromhex(code[2:])).hexdigest();dump(OUT/'bytecode'/(rpc.label+'-'+tier+'.json'),{'runtime':code,'receipt':receipt})
                    with tempfile.TemporaryDirectory(prefix='pqtc-r2-hash-cast-',dir='/tmp')as directory:
                        disassembly=subprocess.run(['cast','disassemble',code],capture_output=True,text=True,env=clean_env(),cwd=directory)
                    (OUT/'bytecode'/(rpc.label+'-'+tier+'.disassembly')).write_text(disassembly.stdout)
                    (OUT/'bytecode'/(rpc.label+'-'+tier+'.stderr')).write_text(disassembly.stderr)
                    record['disassembly_command']={'argv':['cast','disassemble',code],'cwd_class':'isolated /tmp, no dotenv copied','exit':disassembly.returncode}
                    disassembly.check_returncode()
            except RuntimeError as e:record['error']=str(e)
            records.append(record)
    dump(OUT/(rpc.label+'-deployments.json'),records);return addresses,records

def deposit_measurements(rpc,addresses,native,do_trace):
    records=[]
    for config,tiers in addresses.items():
        for tier,address in tiers.items():
            record={'config':config,'tier':tier,'measurement_class':rpc.label,'envelope':'same Deposit source and dynamic-field ABI; both digest widths packed into exactly two storage words, H5 unused tail zero; reentrancy guard, canonical/nonzero/duplicate/capacity checks, permanent knownRoots, twenty frontier updates, timestamp event; external hash calls in every tier; intentionally unfunded denomination0 and no withdrawal registry'}
            try:
                receipt,meta=rpc.deploy('Deposit',word(int(address,16))+bytes(64)+word(0));record.update(constructor_receipt=receipt,**meta)
                if do_trace:record['constructor_attribution']=trace(rpc,receipt,rpc.label+'-'+tier+'-constructor')
                if int(receipt['status'],16)!=1:continue
                pool=receipt['contractAddress'];raw=(31337).to_bytes(8,'big')+bytes.fromhex(pool[2:])+bytes(32)+bytes([20])+(3).to_bytes(4,'big')+bytes(64)
                fields=[int.from_bytes(raw[i:i+2].ljust(2,b'\0'),'big')for i in range(0,len(raw),2)]
                expected=native.evaluate(request(config,1,fields));assert expected['rust']['output']==expected['typescript']['output'];scope=decode_array(rpc.ethcall(pool,rpc.sig('getScope()')));assert scope==expected['rust']['output']
                zero=native.evaluate(request(config,4,scope))['rust']['output'];zeros=[]
                for level in range(20):zeros.append(zero);zero=native.evaluate(request(config,5,zero+zero,level))['rust']['output']
                initial=decode_array(rpc.ethcall(pool,rpc.sig('getRoot()')));assert initial==zero
                leaf=native.evaluate(request(config,2,scope+list(range(1,17))))['rust']['output'];data=rpc.sig('deposit(uint256[])')+word(32)+array(leaf)
                dep=rpc.transact(data,pool);record.update(scope=scope,initial_root=initial,leaf=leaf,deposit_receipt=dep)
                if do_trace:record['deposit_attribution']=trace(rpc,dep,rpc.label+'-'+tier+'-deposit')
                if int(dep['status'],16)==1:
                    root=leaf
                    for level in range(20):root=native.evaluate(request(config,5,root+zeros[level],level))['rust']['output']
                    actual=decode_array(rpc.ethcall(pool,rpc.sig('getRoot()')));assert actual==root;record['final_root']=actual;record['scope_correct_zero_tree_and_insertion']=True
                    second_leaf=native.evaluate(request(config,2,scope+list(range(17,33))))['rust']['output']
                    second=rpc.transact(rpc.sig('deposit(uint256[])')+word(32)+array(second_leaf),pool);record['second_deposit_receipt']=second
                    if do_trace:record['second_deposit_attribution']=trace(rpc,second,rpc.label+'-'+tier+'-second-deposit')
                    if int(second['status'],16)==1:
                        second_root=native.evaluate(request(config,5,leaf+second_leaf,0))['rust']['output']
                        for level in range(1,20):second_root=native.evaluate(request(config,5,second_root+zeros[level],level))['rust']['output']
                        assert decode_array(rpc.ethcall(pool,rpc.sig('getRoot()')))==second_root;record['second_final_root']=second_root
                    rejected={}
                    for label,bad in [('duplicate',leaf),('zero',[0]*len(leaf)),('noncanonical',[P]+leaf[1:])]:
                        try:rpc.ethcall(pool,rpc.sig('deposit(uint256[])')+word(32)+array(bad));raise AssertionError('deposit mutation accepted: '+label)
                        except RuntimeError as e:rejected[label]=str(e)
                    record['deposit_rejections']=rejected
            except RuntimeError as e:record['error']=str(e)
            finally:
                records.append(record)
                dump(OUT/(rpc.label+'-deposit.json'),records)
    return records

def map_fields(seed,count,ledger,label):
    # Rejection sampling on independent SHA256 counter words. No mod-p reduction.
    values=[];counter=0
    while len(values)<count:
        raw=hashlib.sha256(b'PQTC-R2-HASH-MAP-v1'+label.encode()+seed+counter.to_bytes(8,'big')).digest();counter+=1
        for j in range(0,32,4):
            draw=int.from_bytes(raw[j:j+4],'big');accepted=draw<P;ledger.write(json.dumps({'label':label,'counter':counter-1,'word':j//4,'draw':draw,'accepted':accepted})+'\n')
            if accepted:values.append(draw)
            if len(values)==count:break
    return values

def corpus_vectors(native):
    corpus=json.loads((REPO/'research/r2/corpus/semantic-cases.json').read_text())['cases']
    with (OUT/'mapping-ledger.jsonl').open('w')as ledger:
        for case in corpus:
            secret=map_fields(bytes.fromhex(case['nullifierSecretBytes'][2:]),8,ledger,case['caseId']+'secret');trapdoor=map_fields(bytes.fromhex(case['trapdoorBytes'][2:]),8,ledger,case['caseId']+'trapdoor')
            for config in CONFIGS:
                d=16 if config==CONFIGS[0]else 12
                raw=int(case['chainId']).to_bytes(8,'big')+bytes.fromhex(case['poolAddress'][2:])+int(case['denomination']).to_bytes(32,'big')+bytes([20])+(3).to_bytes(4,'big')+bytes(64)
                scope_request=request(config,1,[int.from_bytes(raw[i:i+2].ljust(2,b'\0'),'big')for i in range(0,len(raw),2)]);yield scope_request
                scope=native.evaluate(scope_request)['rust']['output'];note_request=request(config,2,scope+secret+trapdoor);yield note_request
                note=native.evaluate(note_request)['rust']['output'];null_request=request(config,3,scope+secret);yield null_request
                null=native.evaluate(null_request)['rust']['output'];yield request(config,4,scope)
                payraw=bytes.fromhex(case['recipient'][2:])+bytes.fromhex(case['relayer'][2:])+int(case['fee']).to_bytes(32,'big');pay_request=request(config,6,[int.from_bytes(payraw[i:i+2],'big')for i in range(0,72,2)]);yield pay_request
                pay=native.evaluate(pay_request)['rust']['output'];index=case['leafIndex'];root=note
                for level,seed in enumerate(case['siblingSeeds']):
                    sibling=map_fields(bytes.fromhex(seed[2:]),d,ledger,case['caseId']+config+f'sibling{level}');r=request(config,5,root+sibling if index&1==0 else sibling+root,level);yield r;root=native.evaluate(r)['rust']['output'];index>>=1
                yield request(config,7,scope+root+null+pay)

def main():
    global OUT,ARTIFACTS
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--rpc-url',required=True);p.add_argument('--diagnostic-rpc-url');p.add_argument('--build',action='store_true');p.add_argument('--vectors',type=int,default=10010);p.add_argument('--chunk',type=int,default=2);p.add_argument('--gas-limit',type=int,default=16777216);p.add_argument('--diagnostic-gas-limit',type=int,default=1000000000);p.add_argument('--trace',action='store_true');p.add_argument('--native-repetitions',type=int,default=10);p.add_argument('--plonky3',type=Path);p.add_argument('--reuse-parity',type=Path);a=p.parse_args()
    if a.vectors<10000 or a.chunk<=0 or a.native_repetitions<=0:p.error('at least 10000 vectors, a positive chunk size and native repetitions required')
    OUT=a.output.resolve()
    if not OUT.is_relative_to(ROOT) or not OUT.name.startswith('resume-'):p.error('output must be a fresh resume-* directory under research/r2/hash')
    OUT.mkdir(parents=True,exist_ok=False);commands=[];environment=clean_env();os.environ.clear();os.environ.update(environment)
    def command(argv,label,input=None,cwd=ROOT):
        start=time.monotonic_ns();r=subprocess.run(list(map(str,argv)),input=input,text=True,capture_output=True,env=environment,cwd=cwd);(OUT/(label+'.stdout')).write_text(r.stdout);(OUT/(label+'.stderr')).write_text(r.stderr);commands.append({'argv':list(map(str,argv)),'cwd':str(cwd),'exit':r.returncode,'elapsed_ns':time.monotonic_ns()-start,'stdout':label+'.stdout','stderr':label+'.stderr'});dump(OUT/'commands.json',commands);r.check_returncode();return r.stdout
    sources=[f for directory in (ROOT/'rust/src',ROOT/'solidity/src')for f in directory.rglob('*')if f.is_file()and f.suffix in ('.rs','.sol')]
    sources.extend(ROOT/name for name in ('run.py','generate.py','compare_constants.py','reference.ts','constants.json','spec.json','execution.json','package.json','rust/Cargo.toml','rust/Cargo.lock','solidity/foundry.toml'))
    sources.extend((REPO/'contracts/src/libraries').glob('*.sol'));sources.extend([REPO/'contracts/src/PQTCDomains.sol',REPO/'Cargo.toml',REPO/'Cargo.lock',REPO/'crates/pqtc-hash/src/lib.rs',REPO/'research/candidates/hash-compression-common/reference/reference.ts',REPO/'research/candidates/hash-compression-common/constants/pinned.json'])
    sources.extend((REPO/'research/candidates/hash-compression-common/solidity/src').glob('*.sol'))
    sources.append(REPO/'crates/pqtc-hash/Cargo.toml')
    for source in sources:
        target=OUT/'source-epoch'/source.relative_to(REPO);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    dump(OUT/'source-hashes.json',{str(f.relative_to(REPO)):hashlib.sha256(f.read_bytes()).hexdigest()for f in sources})
    binary=ROOT/'target/release/pqtc-r2-hash';constants_binary=ROOT/'target/release/constants'
    if a.build:
        with tempfile.TemporaryDirectory(prefix='pqtc-r2-hash-native-',dir='/tmp')as directory:
            environment['CARGO_TARGET_DIR']=directory
            command(['cargo','build','--release','--locked','--offline','--manifest-path',ROOT/'rust/Cargo.toml'],'cargo-build',cwd=Path(directory))
            (OUT/'native').mkdir()
            for name in ('pqtc-r2-hash','constants'):shutil.copy2(Path(directory)/'release'/name,OUT/'native'/name)
        environment.pop('CARGO_TARGET_DIR',None)
        binary=OUT/'native/pqtc-r2-hash';constants_binary=OUT/'native/constants'
        with tempfile.TemporaryDirectory(prefix='pqtc-r2-hash-forge-',dir='/tmp')as directory:
            work=Path(directory);ignore=shutil.ignore_patterns('.env','.env.*');shutil.copytree(ROOT/'solidity/src',work/'src',ignore=ignore);shutil.copytree(REPO/'contracts/src',work/'frozen',ignore=ignore);shutil.copytree(REPO/'research/candidates/hash-compression-common/solidity/src',work/'frozen-generic',ignore=ignore)
            config=(ROOT/'solidity/foundry.toml').read_text().replace('../../../../contracts/src/','frozen/').replace('../../../candidates/hash-compression-common/solidity/src/','frozen-generic/').replace('../../../../contracts','frozen').replace('../../../candidates/hash-compression-common/solidity','frozen-generic')
            (work/'foundry.toml').write_text(config);command(['forge','build','--offline','--root',work],'forge-build',cwd=work);ARTIFACTS=OUT/'solidity-out';shutil.copytree(work/'out',ARTIFACTS)
    if a.plonky3:command([sys.executable,ROOT/'compare_constants.py','--plonky3',a.plonky3,'--binary',constants_binary,'--output',OUT/'constants'],'constants-comparison')
    result={'specification':'complete R2-H5-complete-v1; exact frozen H0 control','correctness':'pending','privacy':'synthetic-unfunded only; no hiding claim','security':'security-not-qualified','performance':'pending','stage':'executing-isolated-measurements','promotion':'not-promoted','argv':sys.argv,'environment':environment,'native_binary':{'path':str(binary),'sha256':hashlib.sha256(binary.read_bytes()).hexdigest()},'solidity_artifacts':str(ARTIFACTS),'source_corpus_sha256':hashlib.sha256((REPO/'research/r2/corpus/semantic-cases.json').read_bytes()).hexdigest()};dump(OUT/'results.json',result)
    dump(OUT/'operation-counts.json',{'classification':'exact source schedule, not gas extrapolation','H0_permutations':{'scope':20,'note':11,'nullifier':9,'empty':7,'node':11,'payout':12,'statement':19,'permutation':1,'compression_control':1,'twenty_levels':220,'constructor_scope_empty_twenty_levels':247,'deposit_twenty_levels':220},'H5_permutations':{'scope':5,'note':1,'nullifier':1,'empty':1,'node':1,'payout':3,'statement':4,'permutation':1,'compression':1,'twenty_levels':20,'constructor_scope_empty_twenty_levels':26,'deposit_twenty_levels':20},'note':'deposit receives a commitment, as frozen pool does; offchain note derivation not hidden in deposit cost. Scope is recomputed for actual pool address in constructor. Proof roles are not instantiated.'})
    primary=RPC(a.rpc_url,'capped-local-top-level',a.gas_limit);primary_addresses,deployment=deploy_tiers(primary,a.trace)
    diagnostic=RPC(a.diagnostic_rpc_url,'diagnostic-unpromotable',a.diagnostic_gas_limit)if a.diagnostic_rpc_url else primary
    addresses,diag_deploy=deploy_tiers(diagnostic,a.trace)if diagnostic is not primary else(primary_addresses,deployment)
    result['endpoints']={'primary':{'url':a.rpc_url,'label':'capped-local-top-level','gas_limit':a.gas_limit,'client':primary.call('web3_clientVersion',[]),'block':primary.call('eth_getBlockByNumber',['latest',False])},'diagnostic':{'url':a.diagnostic_rpc_url,'label':'diagnostic-unpromotable'if a.diagnostic_rpc_url else'not-used','gas_limit':a.diagnostic_gas_limit if a.diagnostic_rpc_url else None}}
    native=Native(binary)
    try:
        assert all(len(addresses[c])==len(TIERS[c])for c in CONFIGS),'all five implementations must physically deploy for full parity; see deployment records'
        prior=None
        if a.reuse_parity:
            prior=json.loads((a.reuse_parity/'results.json').read_text())
            previous_sources=json.loads((a.reuse_parity/'source-hashes.json').read_text())
            assert prior['parity']['checked_shared_full_roles']>=10000 and json.loads((a.reuse_parity/'misuse.json').read_text())['passed']
            assert prior['source_corpus_sha256']==result['source_corpus_sha256']
            for source in sources:
                if source.suffix in ('.rs','.sol','.ts')or source.name in ('constants.json','spec.json','Cargo.lock'):
                    assert previous_sources[str(source.relative_to(REPO))]==file_sha256(source),'parity source epoch changed'
            result['reused_parity']={'path':str(a.reuse_parity),'results_sha256':file_sha256(a.reuse_parity/'results.json'),'executed_this_run':False,'scope':'Previously executed full-role parity, identical implementation/corpus sources; not new observations'}
        checked=0;coverage=collections.Counter()
        with (OUT/'vectors.jsonl').open('w')as vectors,(OUT/'parity.jsonl').open('w')as parity:
            import itertools
            source=()if prior else itertools.chain(full_vectors(a.vectors),corpus_vectors(native));batch=[]
            def flush(batch):
                nonlocal checked
                # Group only same-config bounded chunks; no giant JSON corpus.
                groups=collections.defaultdict(list)
                for r in batch:groups[r['config']].append(r)
                for config,requests in groups.items():
                    native_outputs=[native.evaluate(r)for r in requests]
                    evm={tier:diagnostic.batch(address,requests)for tier,address in addresses[config].items()}
                    for i,r in enumerate(requests):
                        rust=native_outputs[i]['rust'];ts=native_outputs[i]['typescript'];assert 'output'in rust and rust['output']==ts.get('output'),(r,native_outputs[i]);assert all(outputs[i]==rust['output']for outputs in evm.values()),r
                        vectors.write(json.dumps({'id':checked,'request':r,'output':rust['output']})+'\n');parity.write(json.dumps({'id':checked,'config':config,'role':r['role'],'rust':True,'typescript':True,'solidity_tiers':list(evm)})+'\n');checked+=1;coverage[f'{config}/role{r["role"]}']+=1
            for r in source:
                batch.append(r)
                if len(batch)>=a.chunk:flush(batch);batch=[]
            if batch:flush(batch)
        result['parity']=prior['parity']if prior else{'checked_shared_full_roles':checked,'coverage':dict(coverage),'chunk_size':a.chunk};result['misuse_cases']=misuse(native,diagnostic,addresses)
        benchmarks=[]
        for config in CONFIGS:
            d=16 if config==CONFIGS[0]else 12
            samples=[request(config,role,list(range(1,[0,65,d+16,d+8,d,2*d,36,4*d,16 if d==16 else 32,16 if d==16 else 32][role]+1)))for role in range(1,10)];samples[0]['payload'][-1]=256
            native_bench=command([binary,a.native_repetitions],'native-'+config,'\n'.join(json.dumps(r)for r in samples)+'\n');measurements=[json.loads(x)for x in native_bench.splitlines()];assert len(measurements)==len(samples)and all('output'in x for x in measurements),measurements
            dump(OUT/('native-'+config+'.json'),{'requests':samples,'measurements':measurements,'binary_bytes':binary.stat().st_size,'measurement_class':'native-latency-no-proof-performance-claim'})
            for tier,address in addresses[config].items():
                for r in samples:
                    data=diagnostic.encoded(r);gas=diagnostic.call('eth_estimateGas',[{'to':address,'from':diagnostic.account,'data':'0x'+data.hex(),'gas':hex(diagnostic.gas)}]);row={'config':config,'tier':tier,'role':r['role'],'gas':int(gas,16),'measurement_class':'eth_estimateGas-complete-ABI-call-not-transaction-receipt'}
                    if a.trace:
                        receipt=diagnostic.transact(data,address);row['receipt']=receipt;row['attribution']=trace(diagnostic,receipt,tier+'-role'+str(r['role']))
                    benchmarks.append(row)
                    dump(OUT/'benchmarks.json',benchmarks)
                siblings=[[i+1]*d for i in range(20)];parts=[array([1]*d),nested(siblings)];data=diagnostic.sig('hash20(uint256[],uint256[][],uint256)')+word(96)+word(96+len(parts[0]))+word(0)+b''.join(parts)
                gas=diagnostic.call('eth_estimateGas',[{'to':address,'from':diagnostic.account,'data':'0x'+data.hex(),'gas':hex(diagnostic.gas)}]);row={'config':config,'tier':tier,'operation':'twenty-level-hashing','gas':int(gas,16),'measurement_class':'eth_estimateGas-compute-only'}
                if a.trace:
                    receipt=diagnostic.transact(data,address);row['receipt']=receipt;row['attribution']=trace(diagnostic,receipt,tier+'-twenty-levels')
                benchmarks.append(row)
                dump(OUT/'benchmarks.json',benchmarks)
        result['capped_deposit']=deposit_measurements(primary,primary_addresses,native,a.trace)
        if diagnostic is not primary:result['diagnostic_deposit']=deposit_measurements(diagnostic,addresses,native,a.trace)
        dump(OUT/'benchmarks.json',benchmarks)
        result.update(correctness='full-role three-language parity and actual misuse passed',performance='measured-see-artifacts',stage='executed-isolated-research',benchmarks=len(benchmarks),constants_parity='passed'if a.plonky3 else'not-executed',research_relation_eligible=bool(a.plonky3))
    except Exception as e:result['error']=str(e);result['stage']='execution-failed-partial-evidence-retained';raise
    finally:
        native.close();dump(OUT/'results.json',result);dump(OUT/'artifact-ledger.json',{str(f.relative_to(ROOT)):{'bytes':f.stat().st_size,'sha256':file_sha256(f)}for f in OUT.rglob('*')if f.is_file()and f.name!='artifact-ledger.json'})
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
