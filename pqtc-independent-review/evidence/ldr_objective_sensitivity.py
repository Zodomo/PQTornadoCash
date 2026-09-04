#!/usr/bin/env python3
"""Independent arithmetic sensitivity, NOT a security proof or a PQTC test run.

Transcribes formulas visible in research/security-model/calculator/security_calculator.py
at Zodomo/PQTornadoCash commit e51a5c5ccc4f50e0beb07cdf04d7f8dd258c7997.
Compares its FRI-only selection of the analysis parameter m against selection
using all modeled terms. The conditional Johnson-correlated-agreement assumptions,
dominant-term approximation, supplied hash budget, and absent QROM theorem remain.
No upstream code, proofs, or dependencies are downloaded or executed.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path

COMMIT = 'e51a5c5ccc4f50e0beb07cdf04d7f8dd258c7997'


def terms(m: int, queries: int, *, blowup: int = 4,
          proof_degree_bits: int = 9, field_bits: int = 120,
          batches: int = 210, constraints: int = 1186,
          degree: int = 7, rotations: int = 2,
          fold_log: int = 1, grinding_credit: float = 8.0,
          include_subdominant_batch: bool = False) -> dict[str, float] | None:
    """Return modeled bit exponents, not an end-to-end security guarantee."""
    if m < 3 or queries < 1 or batches < 2:
        raise ValueError('m >= 3, queries >= 1, batches >= 2 required')
    rho = 2.0 ** -blowup
    k = 1 << proof_degree_bits
    n = k << blowup
    alpha = (1.0 + 0.5 / m) * math.sqrt(rho)
    gamma = 1.0 - alpha
    if not 0.0 < gamma < 1.0 or k + rotations >= alpha * n:
        return None
    shifted = m + 0.5
    epsilon = ((2.0 * shifted**5 + 3.0 * shifted * gamma * rho) * n
               / (3.0 * rho**1.5) + shifted / math.sqrt(rho))
    dominant_epsilon = 2.0 * shifted**5 * n / (3.0 * rho**1.5)
    list_size = shifted / math.sqrt(rho)
    commit_linear = field_bits - math.log2(max(epsilon * ((1 << fold_log) - 1), 1))
    commit_nq = (field_bits - fold_log - math.log2(n + 1)
                 - math.log2(2 * m + 1) + 0.5 * math.log2(rho))
    return {
        'air_rlc': field_bits - math.log2(list_size) - math.log2(constraints),
        'deep_ali': field_bits - math.log2(list_size)
                    - math.log2(degree * (k + rotations - 1) + (k - 1)),
        'fri_query': -queries * math.log2(alpha) + grinding_credit,
        'fri_commit': min(commit_linear, commit_nq) + grinding_credit,
        'batched_openings': field_bits
              - math.log2(epsilon if include_subdominant_batch else dominant_epsilon)
              - math.log2(batches - 1),
        'challenge_cap': float(field_bits),
        'supplied_mmcs_cap': 128.0,
    }


def summarize(m: int, values: dict[str, float]) -> dict:
    minimum = min(values.values())
    # A sensitivity only: a probability sum is not substituted for the upstream
    # round-by-round theorem. Both mathematical aggregates are made explicit.
    probability_sum_bits = minimum - math.log2(sum(2.0 ** (minimum - b) for b in values.values()))
    return {'m': m, 'minimum_modeled_bits': minimum,
            'arithmetic_probability_sum_bits': probability_sum_bits,
            'binding_terms': [k for k, v in values.items() if abs(v - minimum) < 1e-9],
            'terms': values}


def run() -> dict:
    upper = min(math.ceil(1.0 / (2.0 * (math.sqrt((512.0 + 2.0) / 512.0) - 1.0))), 1000)
    rows = []
    for queries in (32, 48, 64):
        candidates = [(m, values) for m in range(3, upper + 1)
                      if (values := terms(m, queries)) is not None]
        upstream_choice = max(candidates, key=lambda x: (min(x[1]['fri_query'], x[1]['fri_commit']), x[0]))
        full_choice = max(candidates, key=lambda x: (min(x[1].values()), x[0]))
        full_values = terms(full_choice[0], queries, include_subdominant_batch=True)
        rows.append({'queries': queries,
                     'fri_only_objective': summarize(*upstream_choice),
                     'full_modeled_objective': summarize(*full_choice),
                     'same_m_with_full_epsilon_in_batch_sensitivity': summarize(full_choice[0], full_values)})
    assert rows[0]['fri_only_objective']['m'] == 185
    assert abs(rows[0]['fri_only_objective']['minimum_modeled_bits'] - 56.201226486) < 1e-8
    assert rows[0]['full_modeled_objective']['m'] == 23
    assert abs(rows[0]['full_modeled_objective']['minimum_modeled_bits'] - 71.007139340) < 1e-8
    assert rows[1]['fri_only_objective']['m'] == 5
    return {
        'classification': 'INDEPENDENT_ARITHMETIC_SENSITIVITY_NOT_SECURITY_QUALIFICATION',
        'reviewed_commit': COMMIT,
        'source': f'https://github.com/Zodomo/PQTornadoCash/blob/{COMMIT}/research/security-model/calculator/security_calculator.py',
        'source_scope': '_common_terms, _ldr_candidate, _batch_ldr, _ldr',
        'model': {'proof_degree_bits': 9, 'field_budget_bits': 120,
                  'batches': 210, 'constraints': 1186, 'degree': 7,
                  'rotations': 2, 'log_blowup': 4, 'fold_log': 1,
                  'commit_and_query_quantum_grinding_credit_each': 8,
                  'analysis_m_range': [3, upper]},
        'rows': rows,
        'does_not_change': ['actual proof', 'query count', 'gas', 'unconditional UDR estimate'],
        'not_established': ['theorem applicability', 'knowledge extraction', 'quantum ROM composition',
                            'hash structural security', 'zero knowledge', 'implementation correctness',
                            'a 100-bit system-security claim'],
        'note': 'The epsilon-inclusive batch row and probability sum are arithmetic sensitivity checks, not proposed replacement theorems.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = run()
    encoded = json.dumps(result, indent=2, sort_keys=True) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded)
    print(encoded)
