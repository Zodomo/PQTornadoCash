#!/usr/bin/env python3
"""R2-01 arithmetic research, not a security qualification or measured attack cost."""
from __future__ import annotations
import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PIN = '3152b14a89067c83775a8076cc262ffc48a1fd7c'
VERSION = 'r2-full-objective-v1'
CONDITIONS = ['Johnson mutual correlated agreement at the same radius for all terms',
              'Theorem parameter must match actual PCS batching objects',
              'No complete Fiat-Shamir/QROM, MMCS structural or hiding composition proof',
              'Probability-sum and full-epsilon columns are arithmetic sensitivities, not replacement theorems']


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def csv_rows(path, rows):
    if not rows:
        raise ValueError(f'no rows for {path}')
    columns = list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, columns)
        writer.writeheader()
        writer.writerows({k: json.dumps(v, sort_keys=True) if isinstance(v, (dict, list)) else v
                         for k, v in row.items()} for row in rows)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def upper_m(p):
    k = 1 << p['proof_degree_bits']
    return min(math.ceil(1 / (2 * (math.sqrt((k + 2) / k) - 1))), 1000)


def aggregates(values):
    minimum = min(values.values())
    return {'minimum_bits': minimum,
            'error_sum_bits': minimum - math.log2(math.fsum(2 ** (minimum - x) for x in values.values()))}


def full_terms(p, m, quantum, full_epsilon):
    # Independent implementation: do not call frozen calculator helpers here.
    rho = 2.0 ** -p['fri_log_blowup']
    k = 1 << p['proof_degree_bits']
    n = k << p['fri_log_blowup']
    alpha = (1 + 1 / (2 * m)) * math.sqrt(rho)
    gamma = 1 - alpha
    list_size = (m + .5) / math.sqrt(rho)
    dominant = 2 * (m + .5) ** 5 * n / (3 * rho ** 1.5)
    subdominant_linear = (m + .5) * gamma * n / math.sqrt(rho)
    subdominant_constant = (m + .5) / math.sqrt(rho)
    epsilon = dominant + subdominant_linear + subdominant_constant
    linear = p['challenge_field_bits'] - math.log2(max(epsilon * ((1 << p['fri_max_log_arity']) - 1), 1))
    nq = p['challenge_field_bits'] - p['fri_max_log_arity'] - math.log2(n + 1) - math.log2(2*m+1) + .5*math.log2(rho)
    divisor = 2 if quantum else 1
    values = {
        'air_rlc': p['challenge_field_bits'] - math.log2(list_size * p['num_constraints']),
        'deep_ali': p['challenge_field_bits'] - math.log2(list_size * (p['max_constraint_degree'] * (k + p['max_combo'] - 1) + k - 1)),
        'fri_query': -p['fri_num_queries'] * math.log2(alpha) + p['query_grinding_bits']/divisor,
        'fri_commit': min(linear, nq) + p['commit_grinding_bits']/divisor,
        'challenge_cap': float(p['challenge_field_bits']),
        'mmcs_cap': float(p['mmcs_binding_bits_quantum' if quantum else 'mmcs_binding_bits_classical']),
    }
    if p['num_batched_functions'] >= 2:
        values['batch'] = p['challenge_field_bits'] - math.log2(epsilon if full_epsilon else dominant) - math.log2(p['num_batched_functions']-1)
    valid = 0 < gamma < 1 and k + p['max_combo'] < alpha*n
    metadata = dict(m=m, alpha=alpha, gamma=gamma, list_size=list_size, rho=rho, k=k, n=n,
                    proximity_valid=valid, strict_degree_gap=alpha*n-k-p['max_combo'],
                    m_in_pinned_range=3 <= m <= upper_m(p), epsilon_dominant=dominant,
                    epsilon_subdominant_linear=subdominant_linear, epsilon_subdominant_constant=subdominant_constant,
                    epsilon_full=epsilon, fri_commit_linear_bits=linear, fri_commit_n_over_q_bits=nq)
    return values, metadata


def inventory(p):
    """Derive matrix objects from HidingFriPcs commit/get_quotient_ldes/randomization methods."""
    if p['max_combo'] not in (1,2) or p.get('preprocessed_width',0):
        raise ValueError('inventory supports local/next base AIR only; extra rotations/preprocessing require actual commitment inventory')
    w, h, r, c, d = p['relation_width'], p['logical_trace_height'], p['hiding_random_functions'], p['quotient_chunks'], 4
    if not p['is_zk']:
        raise ValueError('this inventory is only for the configured hiding FRI PCS')
    if 1 << p['proof_degree_bits'] != 2*h:
        raise ValueError('HidingFriPcs inventory requires one interleaved hiding row per logical row')
    rows = []
    power = 0
    for commitment, matrix, width, original, points, desc in [
            ('random', 0, d+r, d, ['zeta'], 'DIMENSION independent base polynomials plus r random codewords; inner.commit avoids second padding'),
            ('trace', 0, w+r, w, ['zeta','zeta*g_logical'] if p['max_combo'] == 2 else ['zeta'], 'original trace interleaved with random rows; r appended columns'),
            *[('quotient', i, d+r, d, ['zeta'], 'extension coefficient columns; r appended codewords; correlated vanishing-polynomial masks across chunks') for i in range(c)]]:
        start = power
        power += width * len(points)
        rows.append(dict(commitment=commitment, matrix=matrix, base_width=width,
                         data_coefficient_columns=original, appended_random_columns=r,
                         pre_hiding_height=h if commitment != 'random' else 2*h,
                         committed_degree_bound=2*h, lde_height=(2*h) << p['fri_log_blowup'],
                         extension_dimension=d, opening_points=points,
                         alpha_exponents=list(range(start,power)), description=desc))
    base_count = sum(row['base_width'] for row in rows)
    observed=p.get('observed_input_matrices')
    if observed is not None:
        expected=[(r['commitment'],r['matrix'],r['base_width'],r['lde_height']) for r in rows]
        actual=[(r['commitment'],r['matrix'],r['base_width'],r['lde_height']) for r in observed]
        if actual != expected:
            raise ValueError(f'actual committed matrices differ from hiding PCS inventory: {actual} != {expected}')
    return dict(profile_id=p['profile_id'], candidate_id=p.get('candidate_id','R2-C0'), matrices=rows,
                commitment_order=['random','trace','quotient'], commitment_count=3,
                matrix_count=len(rows), nominal_count=w+c+r,
                visible_base_columns=base_count, reduction_terms=power,
                distinct_mask_columns=r*(c+2), extension_coefficient_columns=d*(c+1), trace_columns=w,
                observed_input_matrices=observed,observation_status='matched-native-proof' if observed else 'source-derived-not-runtime-instrumented',
                quotient_mask_relation='q_i_prime=q_i+v_H_i*t_i; final t_last=-sum_i(c_i/c_last)*t_i. Not extra committed columns.',
                mmcs_salts='8 base fields per authenticated input row, outside polynomial widths and alpha powers',
                degree_correction='Each quotient chunk is randomized from degree<h to degree<2h; all input LDE heights equal. Each (f(z)-f(X))/(z-X) lowers degree by one; repeated trace rotation consumes a separate alpha exponent, not a new committed polynomial.',
                theorem_object_status='OPEN: nominal extension chunks vs base coefficient polynomials vs reduced point-specific functions; no mechanical replacement',
                source_basis=['p3/fri/src/hiding_pcs.rs:110-135,190-258,443-462', 'p3/uni-stark/src/prover.rs:186-215,298-332,367-409',
                              'crates/pqtc-stark/src/query.rs:302-376','contracts/src/verifier/PQTCQueryVerifier.sol:217-237'])


def profiles(shapes, calculator):
    baseline = json.loads((ROOT / 'research/security-model/manifests/v03-q32.json').read_text())
    records = [dict(baseline, candidate_id='R2-C0')]
    for path in shapes:
        supplied = json.loads(path.read_text())
        if isinstance(supplied, dict): supplied = supplied['shapes']
        for shape in supplied:
            required = ['candidate_id','logical_trace_height','proof_degree_bits','relation_width','num_constraints',
                        'max_constraint_degree','max_combo','quotient_chunks','hiding_random_functions','num_batched_functions']
            missing = [k for k in required if k not in shape]
            if missing: raise ValueError(f'{path}: missing exact candidate shape fields {missing}')
            p = dict(baseline, **shape)
            p['profile_id'] = shape.get('profile_id',shape['candidate_id'])
            p['hiding_degree_padding_bits'] = p['proof_degree_bits'] - (p['logical_trace_height'].bit_length()-1)
            p['batch_count_derivation'] = 'explicit'
            p['batch_count_rationale'] = shape.get('batch_count_rationale','Caller-supplied analytical input; inventory records alternative meanings separately')
            records.append(p)
    result = []
    for record in records:
        inv = inventory(record)
        for q in sorted({32,48,64,record['fri_num_queries']}):
            for basis,count in [('declared',record['num_batched_functions']),('base_columns',inv['visible_base_columns']),('reduction_terms',inv['reduction_terms'])]:
                p = dict(record, fri_num_queries=q, profile_id=f"{record['candidate_id']}-q{q}-{basis}",
                         num_batched_functions=count, batch_count_derivation='explicit',
                         batch_count_rationale=f'{basis} sensitivity; not asserted to be the theorem object',count_basis=basis)
                calculator.validate_manifest(p)
                result.append(p)
    return result


def normalized(records, calculator, target):
    result=[]
    for original in records:
        if original['fri_num_queries'] != 32 or original['count_basis'] != 'declared': continue
        for b in (3,4,5):
            p = dict(original, fri_log_blowup=b)
            if p['max_constraint_degree'] > (1<<b): continue
            for regime in ('no-Johnson-UDR','conditional-Johnson-full-objective'):
                best = None
                for q in range(1,257):
                    p['fri_num_queries']=q
                    if regime == 'no-Johnson-UDR':
                        bits = calculator._udr(p)['quantum_bits']; selected_m=None
                    else:
                        candidates = [(min(t.values()),m) for m in range(3,upper_m(p)+1)
                                      if (pair := full_terms(p,m,True,False))[1]['proximity_valid'] for t in [pair[0]]]
                        bits,selected_m=max(candidates)
                    row=dict(candidate_id=p['candidate_id'],q=q,log_blowup=b,regime=regime,model=VERSION,
                             target_bits=target,achieved_bits=bits,m=selected_m,
                             status='TARGET_MET_CONDITIONALLY' if bits>=target else 'TARGET_UNREACHABLE_IN_DECLARED_SWEEP',
                             query_search=[1,256],count_basis=p['count_basis'],num_batched_functions=p['num_batched_functions'],
                             security='SECURITY_NOT_QUALIFIED',conditions=CONDITIONS if selected_m else CONDITIONS[1:])
                    if best is None or bits>best['achieved_bits']: best=row
                    if bits>=target: best=row; break
                result.append(best)
    return result


def clean_env():
    keep={'PATH','HOME','TMPDIR','RUSTUP_HOME','CARGO_HOME','RUSTUP_TOOLCHAIN','RUSTFLAGS','RAYON_NUM_THREADS','CARGO_BUILD_JOBS','SDKROOT','MACOSX_DEPLOYMENT_TARGET'}
    return {k:v for k,v in os.environ.items() if k in keep}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--shapes',type=Path,action='append',default=[])
    ap.add_argument('--output',type=Path,default=HERE/'outputs')
    ap.add_argument('--pinned-binary',type=Path)
    ap.add_argument('--arithmetic-only',action='store_true',help='Explicit partial execution; not a three-path result')
    ap.add_argument('--target-bits',type=float,default=100)
    args=ap.parse_args()
    if not args.pinned_binary and not args.arithmetic_only: ap.error('--pinned-binary required for complete three-path run')
    args.output=args.output.resolve()
    if not args.output.is_relative_to(HERE) or args.output==HERE:
        ap.error('--output must be a dedicated directory under research/r2/security; frozen outputs are read-only')
    if (args.output/'results.json').exists():
        ap.error('existing results.json must be preserved; select a new output directory')
    if not math.isfinite(args.target_bits) or args.target_bits<=0:
        ap.error('--target-bits must be finite and positive')
    args.output.mkdir(parents=True,exist_ok=True)
    calculator=load_module('r2_frozen_calculator','research/security-model/calculator/security_calculator.py')
    supplied=load_module('r2_review_sensitivity','pqtc-independent-review/evidence/ldr_objective_sensitivity.py')
    entries=profiles(args.shapes,calculator)
    dump(args.output/'profiles.json',entries)
    dump(args.output/'supplied-sensitivity.json',supplied.run())
    inventories=[inventory(p) for p in entries if p['fri_num_queries']==32 and p['count_basis']=='declared']
    # Source-accounting regression: derive rather than assert one number is the theorem count.
    baseline=next(i for i in inventories if i['candidate_id']=='R2-C0')
    assert (baseline['nominal_count'],baseline['visible_base_columns'],baseline['reduction_terms'])==(210,330,524)
    sol=(ROOT/'contracts/src/verifier/PQTCQueryVerifier.sol').read_text()
    assert int(re.search(r'REDUCTION_TERMS = (\d+)',sol)[1])==baseline['reduction_terms']
    assert [int(re.search(r'uint256\[(\d+)\] '+name,sol)[1]) for name in ['randomAtZeta','traceLocalAtZeta','traceNextAtZeta','quotientAtZeta']]==[8,194,194,128]
    dump(args.output/'pcs-inventory.json',inventories)
    csv_rows(args.output/'pcs-matrices.csv',[dict(profile_id=i['profile_id'],**m) for i in inventories for m in i['matrices']])
    summaries=[]; terms=[]; translations=[]
    term_names={'air-random-linear-combination':'air_rlc','deep-ali':'deep_ali','fri-query-phase':'fri_query',
                'fri-commit-phase':'fri_commit','batched-opening-proximity':'batch','challenge-field-ceiling':'challenge_cap','mmcs-binding':'mmcs_cap'}
    for p in entries:
        translated=calculator.calculate(p)
        translations.append(translated)
        rows=[]
        for m in range(3,upper_m(p)+1):
            frozen=calculator._ldr_candidate(p,m)
            for quantum in (False,True):
                for epsilon in (False,True):
                    values,meta=full_terms(p,m,quantum,epsilon)
                    row=dict(profile_id=p['profile_id'],candidate_id=p['candidate_id'],formula_version=VERSION,
                             regime='conditional-Johnson',adversary='quantum_grinding_only' if quantum else 'classical',
                             batch_epsilon='full' if epsilon else 'dominant',conditions=CONDITIONS,**meta,**values,**aggregates(values))
                    terms.append(row)
                    if meta['proximity_valid']: rows.append(row)
                    if frozen and not epsilon:
                        key='quantum_bits' if quantum else 'classical_bits'
                        for item in frozen[1]:
                            if item['applies'] and item['term'] in term_names:
                                assert abs(item[key]-max(0,values[term_names[item['term']]]))<1e-7,(p['profile_id'],m,item['term'])
        for quantum in (False,True):
            adversary='quantum_grinding_only' if quantum else 'classical'
            for epsilon in ('dominant','full'):
                subset=[r for r in rows if r['adversary']==adversary and r['batch_epsilon']==epsilon]
                for objective in ('fri-only','full-minimum','full-error-sum'):
                    score=lambda r: min(r['fri_query'],r['fri_commit']) if objective=='fri-only' else r['minimum_bits' if objective=='full-minimum' else 'error_sum_bits']
                    winner=max(subset,key=lambda r:(score(r),r['m']))
                    summaries.append(dict(winner,objective=objective,udr_bits=translated['single_target']['udr']['quantum_bits' if quantum else 'classical_bits']))
    expected=[(32,185,23,56.201226486,71.007139340),(48,5,3,81.580445275,84.840828758),(64,3,3,84.840828758,84.840828758)]
    for q,fm,mm,fb,mb in expected:
        ss=[s for s in summaries if s['profile_id']==f'R2-C0-q{q}-declared' and s['adversary']=='quantum_grinding_only' and s['batch_epsilon']=='dominant']
        for objective,m,bits in [('fri-only',fm,fb),('full-minimum',mm,mb)]:
            s=next(x for x in ss if x['objective']==objective)
            assert s['m']==m and abs(s['minimum_bits']-bits)<1e-8,s
    dump(args.output/'translation.json',translations)
    dump(args.output/'all-terms.json',terms); csv_rows(args.output/'all-terms.csv',terms)
    dump(args.output/'summary.json',summaries); csv_rows(args.output/'summary.csv',summaries)
    selections=normalized(entries,calculator,args.target_bits)
    dump(args.output/'normalized-profiles.json',selections); csv_rows(args.output/'normalized-profiles.csv',selections)
    command=None; upstream=[]
    if args.pinned_binary:
        command=[str(args.pinned_binary.resolve()),str((args.output/'profiles.json').resolve()),str((args.output/'pinned-upstream.json').resolve())]
        proc=subprocess.run(command,env=clean_env(),capture_output=True,text=True)
        (args.output/'pinned.stdout.log').write_text(proc.stdout)
        (args.output/'pinned.stderr.log').write_text(proc.stderr)
        if proc.returncode: raise RuntimeError(f'pinned runner failed with exit {proc.returncode}; see raw logs')
        upstream=json.loads((args.output/'pinned-upstream.json').read_text())
        for native in upstream:
            trans=next(t for t in translations if t['profile_id']==native['profile_id'])
            # Frozen translation deliberately selects quantum-optimal m also for its classical report.
            # Therefore compare quantum path only; retain native classical selector differences.
            if native['adversary']=='quantum_grinding_only':
                for regime in ('udr','ldr'):
                    assert abs(native[f'{regime}_bits']-trans['single_target'][regime]['quantum_bits'])<1e-7,native['profile_id']
                assert native['selected_m']==trans['single_target']['ldr']['proximity_m']
    from reduced_instance import experiment
    dump(args.output/'reduced-instance.json',experiment())
    from packet import generate
    packet=generate()
    dump(args.output/'attack-matrix.json',packet['attacks']); csv_rows(args.output/'attack-matrix.csv',packet['attacks'])
    dump(args.output/'threat-games.json',packet['games']); csv_rows(args.output/'threat-games.csv',packet['games'])
    dump(args.output/'exact-role-layouts.json',packet['layouts'])
    dump(args.output/'entropy.json',{k:v for k,v in packet.items() if k not in ('attacks','games','layouts')})
    inputs=[ROOT/'research/security-model/calculator/security_calculator.py',ROOT/'pqtc-independent-review/evidence/ldr_objective_sensitivity.py',
            ROOT/'crates/pqtc-stark/src/lib.rs',ROOT/'crates/pqtc-stark/src/query.rs',ROOT/'contracts/src/verifier/PQTCQueryVerifier.sol',*args.shapes]
    inputs.extend([HERE/'run.py',HERE/'packet.py',HERE/'reduced_instance.py',HERE/'threat-games.json',
                   HERE/'rust/src/main.rs',ROOT/'research/r2/hash/spec.json',
                   ROOT/'research/candidates/hash-compression-common/constants/pinned.json',
                   HERE/'sources/index.json',HERE/'sources/native-index.json'])
    result=dict(work_package='R2-01',classification='ARITHMETIC_AND_REDUCED_ROUND_EXPERIMENT',
                specification='explicit-formulas-and-source-derived-matrix-inventory',correctness='arithmetic-regressions-passed',
                privacy='not-established',security='SECURITY_NOT_QUALIFIED',performance='analytical-not-runtime',
                stage='three-calculator-execution' if upstream else 'partial-arithmetic-only',promotion='NOT_PROMOTED',
                human_acceptance=False,all_term_rows=len(terms),pinned_rows=len(upstream),command=command,
                argv=sys.argv,inputs=[dict(path=str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p),sha256=sha(p)) for p in inputs],
                m_is_runtime_parameter=False,unchanged_runtime_sources=[str(p.relative_to(ROOT)) for p in inputs[2:5]],
                conditions=CONDITIONS,source_pin=PIN)
    dump(args.output/'results.json',result)
    print(json.dumps(result,sort_keys=True))


if __name__=='__main__': main()
