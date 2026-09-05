#!/usr/bin/env python3
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PIN='3152b14a89067c83775a8076cc262ffc48a1fd7c'
P=2013265921
ALLOWED={'PATH','HOME','USER','TMPDIR','CARGO_HOME','RUSTUP_HOME','RUSTUP_TOOLCHAIN','CARGO_TARGET_DIR','RUSTFLAGS','SDKROOT','MACOSX_DEPLOYMENT_TARGET','CC','CXX','AR','LIBRARY_PATH','DYLD_LIBRARY_PATH','OMP_NUM_THREADS','RAYON_NUM_THREADS'}
def clean_env():return {k:v for k,v in os.environ.items() if k in ALLOWED}
def main():
    p=argparse.ArgumentParser();p.add_argument('--plonky3',type=Path,required=True);p.add_argument('--binary',type=Path,required=True);a=p.parse_args();out=ROOT/'outputs/constants';out.mkdir(parents=True,exist_ok=True)
    commands=[]
    def run(argv):
        r=subprocess.run(list(map(str,argv)),capture_output=True,text=True,env=clean_env());commands.append({'argv':list(map(str,argv)),'exit':r.returncode});(out/f'command-{len(commands)}.stdout').write_text(r.stdout);(out/f'command-{len(commands)}.stderr').write_text(r.stderr);r.check_returncode();return r.stdout
    commit=run(['git','-C',a.plonky3,'rev-parse','HEAD']).strip();assert commit==PIN
    literals=json.loads((ROOT/'constants.json').read_text())['poseidon2'];upstream=json.loads(run([a.binary.resolve()]));comparisons={}
    for w in (16,32):
        generated=json.loads(run([sys.executable,a.plonky3/'poseidon2/generate_constants.py','--field','babybear','--width',str(w),'--format','json','--skip-matrix']))
        c=literals[str(w)];u=upstream[str(w)];sections={'initial':[int(x,16)for row in generated['external_initial']for x in row],'internal':[int(x,16)for x in generated['internal']],'final':[int(x,16)for row in generated['external_final']for x in row]}
        for k,v in sections.items():assert v==c[k]==u[k],(w,k)
        internal=[[(1+(c['diagonal'][i]if i==j else 0))%P for j in range(w)]for i in range(w)]
        m4=[[2,3,1,1],[1,2,3,1],[1,1,2,3],[3,1,1,2]]
        external=[[m4[i%4][j%4]*(2 if i//4==j//4 else 1)for j in range(w)]for i in range(w)]
        assert internal==u['internal_matrix'],('internal matrix',w)
        assert external==u['external_matrix'],('external matrix',w)
        comparisons[str(w)]={'round_constants':sum(map(len,sections.values())),'internal_matrix_entries':w*w,'external_matrix_entries':w*w,'equal':True}
    files=[ROOT/'constants.json',a.plonky3/'poseidon2/generate_constants.py',a.plonky3/'baby-bear/src/poseidon2.rs',a.plonky3/'poseidon2/src/external.rs',a.binary]
    result={'commit':commit,'comparisons':comparisons,'commands':commands,'sha256':{str(f):hashlib.sha256(f.read_bytes()).hexdigest()for f in files},'matrix_note':'Grain script does not generate production optimized diagonals. Every matrix entry compared against actual pinned Rust linear layer acting on all basis vectors. Generator default M4 is NOT substituted for production MDSMat4.','security':'not-qualified'}
    (out/'comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
