"""Generate role-by-role attack applicability tables without inventing costs."""
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
P=2013265921


def generate():
    pinned=json.loads((ROOT/'research/candidates/hash-compression-common/constants/pinned.json').read_text())
    h5=json.loads((ROOT/'research/r2/hash/spec.json').read_text())['h5']
    layouts=[]
    h0roles=[('scope',0x10,129,65,'65 BE16 words of exact 129-byte ScopeInput'),
             ('note',0x11,128,32,'scope16 || secret8 || trapdoor8'),
             ('nullifier',0x12,96,24,'scope16 || secret8'),
             ('empty',0x13,64,16,'scope16'),
             ('node',0x20,128,32,'left16 || right16; aux=level0..19'),
             ('payout',0x14,72,36,'BE16(recipient20 || relayer20 || fee32)'),
             ('statement',0x15,256,64,'scope16 || root16 || nullifier16 || payout16')]
    for role,tag,byte_len,count,payload in h0roles:
        layouts.append(dict(candidate='H0',config_id='R2-H0-v03',role=role,width=16,digest_fields=16,
                            full_rounds=8,partial_rounds=13,variable_fixed_lanes=f'initial[0..3]=0; initial[4..8]=[1,{tag},{byte_len},{count},aux]; initial[9..15]=0; then payload {payload} absorbed additively in rate4',
                            feed_forward='none',output_lanes='0..3 of final absorption state then 0..3 after each of three further permutations',
                            role_scope='exact frozen typed role',domain_controls=f'tag={tag}; version1; bytes={byte_len}; count={count}; aux=level only for node'))
    h5layouts={role:layout for role,layout in h5['roles'].items() if role!='scope_payout_statement'}
    for role in ('scope','payout','statement'):
        h5layouts[role]=dict(h5['roles']['scope_payout_statement'],encoding=h5['public_encodings'][role])
    for role,layout in h5layouts.items():
        layouts.append(dict(candidate='H5',config_id='R2-H5-complete-v1',role=role,width=32,digest_fields=12,
                            full_rounds=8,partial_rounds=30,variable_fixed_lanes=layout,
                            feed_forward='input[i] added to permutation[i] for all retained i=0..11',output_lanes=list(range(12)),
                            role_scope='exact complete R2 role; public byte/field stream constraints retained',
                            domain_controls=dict(domain=h5['domains'][role],version=2001,format=h5['controls'])))
    layouts.append(dict(candidate='H6',config_id='H6-frozen-node-only',role='node',width=32,digest_fields=14,
                        full_rounds=8,partial_rounds=30,variable_fixed_lanes='left[0..13] || right[14..27] || [role4,version1,shape28,level0..19]',
                        feed_forward='input[i] added to permutation[i] for retained i=0..13',output_lanes=list(range(14)),
                        role_scope='frozen node-shaped comparator only; no complete H6 note/nullifier/scope relation',domain_controls='[4,1,28,level]'))
    attacks=[]
    for layout in layouts:
        width=layout['width']; d=layout['digest_fields']
        for source,scope,status in [
            ('2025/954','subspace-trail Groebner preimage/collision', 'APPLICABLE_COST_UNKNOWN'),
            ('2026/306','mode-specific round-skipping preimage/collision/CICO','APPLICABILITY_INCOMPLETE'),
            ('2026/1692','GSR partial-layer CICO gadget','APPLICABILITY_INCOMPLETE')]:
            if source=='2025/954':
                reason='Finite partial-round subspace restriction is structurally available; exact fixed-lane composed role needs equations, regularity and solver costing. Published width<=24 numerical coverage does not certify width32.'
            elif source=='2026/306':
                reason=('H0 is multi-squeeze rate4/capacity12. Sections4.2/5 sponge speedups assume at least two absorptions and one squeeze; their numerical estimates cannot be transferred. '
                        if layout['candidate']=='H0' else
                        'Lemmas3.2/3.6/4.5 enumerate widths12/16/20/24, not width32; exact roles additionally fix controls, scope or zero lanes. One-round tensor experiment is not a full attack. ')
                reason+='Paper M4 rows (5,7,1,3),(4,6,1,1),(1,3,5,7),(1,1,4,6) differ from pinned Horizon M4; tensor mechanism survives, concrete lemma use must be checked.'
            else:
                reason='Paper operationally demonstrates one initial full round followed by partial rounds (Rf0=1), not exact four-initial-full-round Poseidon2. Inverting additional nonlinear layers to satisfy external input constraints is unresolved; t-2k skipping is not a full-mode attack-cost formula.'
            attacks.append(dict(**layout,field=P,extension='none in application permutation; F_p^4 only for PCS challenges',sbox=7,
                                external_matrix='P_(t/4) tensor Horizon-M4; P=I+all-ones; M4 rows (2,3,1,1),(1,2,3,1),(1,1,2,3),(3,1,1,2)',
                                internal_matrix='all-ones + diag(pinned.poseidon2[width].diagonal)',
                                constants_artifact='research/candidates/hash-compression-common/constants/pinned.json',
                                constants=pinned['poseidon2'][str(width)],attack_source=f'https://eprint.iacr.org/{source}',
                                source_version_pin=f'research/r2/security/sources/{source.replace("/","-")}.extracted.txt',
                                attack_family=scope,status=status,reason=reason,computed_work_bits=None,memory_bits=None,
                                target_quantum_bits=100,structural_safety_margin_bits=None,
                                ideal_output_collision_work_bits=d*math.log2(P)/3,
                                ideal_output_preimage_work_bits=d*math.log2(P)/2,
                                ideal_sponge_capacity_collision_work_bits=12*math.log2(P)/3 if width==16 else None,
                                generic_model='Ideal query-complexity benchmarks, not security lower bounds or instantiated attacks. Ignore output-only ceiling when input entropy/capacity/role constraints are lower.',
                                reduced_evidence='outputs/reduced-instance.json for H5/H6 node one-full-round affine gadget only',
                                bounded_decisive_task='For this exact role, encode two-copy collision or target-preimage equations. Show an admissible skip and solve success probability before costing remaining system at omega=2 and memory costs; report inapplicable if a required constraint cannot hold.',
                                security='SECURITY_NOT_QUALIFIED',human_acceptance=False))
    games=json.loads((Path(__file__).parent/'threat-games.json').read_text())
    return dict(layouts=layouts,attacks=attacks,games=games,
                canonical_secret_entropy_bits=8*math.log2(P),secret_and_trapdoor_entropy_bits=16*math.log2(P),
                field_cardinality_bits=math.log2(P),extension_cardinality_bits=4*math.log2(P),
                modeled_challenge_budget_bits=120,unopened_candidates=['H3','H4'],qualification='NONE')
