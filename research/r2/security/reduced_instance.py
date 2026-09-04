#!/usr/bin/env python3
"""Construct a one-full-round affine subspace using exact BabyBear constants.
Not a full-round attack, collision, preimage, funded note, or measured work factor.
"""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
P=2013265921
M4=((2,3,1,1),(1,2,3,1),(1,1,2,3),(3,1,1,2))


def mul4(x):
    return [sum(a*b for a,b in zip(row,x))%P for row in M4]


def solve4(rhs):
    rows=[list(row)+[b] for row,b in zip(M4,rhs)]
    for col in range(4):
        pivot=next(i for i in range(col,4) if rows[i][col]%P)
        rows[col],rows[pivot]=rows[pivot],rows[col]
        inverse=pow(rows[col][col],-1,P)
        rows[col]=[v*inverse%P for v in rows[col]]
        for i in range(4):
            if i!=col:
                factor=rows[i][col]
                rows[i]=[(a-factor*b)%P for a,b in zip(rows[i],rows[col])]
    return [r[-1] for r in rows]


def external(x):
    blocks=[mul4(x[i:i+4]) for i in range(0,len(x),4)]
    totals=[sum(b[j] for b in blocks)%P for j in range(4)]
    return [(b[j]+totals[j])%P for b in blocks for j in range(4)]


def round_with_initial_linear(x, constants):
    return external([pow((a+b)%P,7,P) for a,b in zip(external(x),constants)])


def experiment():
    source=ROOT/'research/candidates/hash-compression-common/constants/pinned.json'
    params=json.loads(source.read_text())['poseidon2']['32']
    constants=params['initial'][:32]
    results=[]
    for candidate,d,control_start,control in [('R2-H5-complete-v1',12,24,[5,2001,24,7]),('H6-frozen-node-only',14,28,[4,1,28,7])]:
        fixed=[0]*32
        fixed[control_start:control_start+4]=control
        other_sum=[sum(fixed[j] for j in range(8+i,32,4))%P for i in range(4)]
        target=[-(constants[i]+constants[4+i])%P for i in range(4)]
        inv_target=solve4(target)
        u=[(a-2*b)*pow(3,-1,P)%P for a,b in zip(inv_target,other_sum)]
        assert mul4(solve4(target))==target
        witnesses=[]; outside=None; second_outside=None; second_round_counterexample=None
        for index in range(257):
            x=[(index**(j+1)+j)%P for j in range(4)]
            state=fixed[:]
            state[:4]=[(a+b)%P for a,b in zip(u,x)]
            state[4:8]=[(-v)%P for v in x]
            affine=[(a+b)%P for a,b in zip(external(state),constants)]
            assert all((affine[j]+affine[4+j])%P==0 for j in range(4))
            output=round_with_initial_linear(state,constants)
            assert state[8:]==fixed[8:]
            if outside is None: outside=output[8:]
            assert output[8:]==outside
            compressed=[(a+b)%P for a,b in zip(output[:d],state[:d])]
            next_round=external([pow((a+b)%P,7,P) for a,b in zip(output,params['initial'][32:64])])
            if second_outside is None: second_outside=next_round[8:]
            elif next_round[8:]!=second_outside and second_round_counterexample is None:
                second_round_counterexample=dict(index=index,first_output_outside=outside,second_output_outside=next_round[8:])
            witnesses.append(dict(index=index,input=state,pre_sbox=affine,one_round_output=output,one_round_feedforward_output=compressed))
        assert second_round_counterexample is not None,'do not silently extend the one-round result'
        results.append(dict(candidate_id=candidate,width=32,digest_fields=d,rounds_executed=1,
                            domain_controls=control,control_start=control_start,pair_blocks=[0,1],affine_offset=u,
                            parameter_dimension=4,samples=257,witnesses=witnesses,
                            next_round_nonextension_counterexample=second_round_counterexample,
                            conclusion='Exact fixed-control one-round low-weight affine propagation; full 8+30-round hash unbroken by this experiment'))
    return dict(classification='CONSTRUCTED_REDUCED_ROUND_EVIDENCE_NOT_HASH_BREAK',field=P,sbox=7,
                constants_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),matrix=M4,
                equation='3*M4*U+2*M4*S_other+C_block0+C_block1=0; odd Sbox preserves (Y,-Y); tensor layer confines differences to the pair',
                relation_to_paper='2026/306 sections 3.2/3.3 structural mechanism; exact width32/Horizon M4 extension proved only for this one round',
                attack_work_bits=None,full_security_margin_bits=None,results=results)


if __name__=='__main__':
    print(json.dumps(experiment(),indent=2))
