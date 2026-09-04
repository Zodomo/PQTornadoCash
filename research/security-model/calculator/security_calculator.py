#!/usr/bin/env python3
"""Deterministic, standard-library security accounting for manifest profiles."""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import sys
from pathlib import Path
from typing import Any, Iterable

PINNED_COMMIT = "3152b14a89067c83775a8076cc262ffc48a1fd7c"
MODEL_VERSION = 1
LDR_M_CAP = 1000
SCENARIOS = (0, 20, 32, 40)
LDR_STATUS = "conditional-theorem-johnson-correlated-agreement"
LDR_CONDITION = (
    "Requires mutual correlated agreement up to the Johnson bound, as stated by pinned "
    "security/src/assumption.rs:45-50."
)
RANDOM_STATUS = "conjectural-random-words"
RANDOM_BATCH_OMISSION = (
    "Random-words does not model the batched-opening proximity term; "
    "num_batched_functions is ignored by the pinned conjectural path."
)
INTERNAL_REVIEW_STATUS = "ACCEPT_METHOD_WITH_LIMITATIONS"
INTERNAL_REVIEW_LIMITATIONS = [
    "This is internal code/methodology review, not external human cryptographic acceptance.",
    "Conjectural random-words and conditional Johnson-bound labels remain binding limitations.",
    "No protocol or candidate qualification follows from methodology acceptance.",
]


def _review_metadata() -> dict[str, Any]:
    return {
        "status": "ACCEPTED_WITH_LIMITATIONS",
        "final": {
            "round": "corrective-2",
            "reviewer": "SecurityModelReview",
            "verdict": INTERNAL_REVIEW_STATUS,
            "findings": 0,
            "limitations": list(INTERNAL_REVIEW_LIMITATIONS),
        },
        "history": [
            {"round": "initial", "verdict": "REJECT_METHOD", "findings": 5},
            {"round": "corrective-1", "verdict": "REJECT_METHOD", "findings": 1},
            {"round": "corrective-2", "verdict": INTERNAL_REVIEW_STATUS, "findings": 0},
        ],
        "historical_findings_resolved": 6,
        "external_cryptographic_review": "OPEN",
        "independent_human_acceptance": False,
    }

SOURCES = {
    "air": f"Plonky3 {PINNED_COMMIT}: security/src/air.rs:1-16",
    "deep": f"Plonky3 {PINNED_COMMIT}: security/src/deep.rs:1-28",
    "proximity": f"Plonky3 {PINNED_COMMIT}: security/src/proximity.rs:20-80",
    "batch": f"Plonky3 {PINNED_COMMIT}: security/src/assumption.rs:126-245; security/src/stark.rs:104-145",
    "fri_random": f"Plonky3 {PINNED_COMMIT}: security/src/fri.rs:80-99; ePrint 2025/2010 sec. 1.5",
    "fri_commit_udr": f"Plonky3 {PINNED_COMMIT}: security/src/fri.rs:101-143",
    "fri_commit_ldr": f"Plonky3 {PINNED_COMMIT}: security/src/fri.rs:145-193; ePrint 2025/2055 Thm. 4.2",
    "fri_query": f"Plonky3 {PINNED_COMMIT}: security/src/fri.rs:196-202",
    "stark": f"Plonky3 {PINNED_COMMIT}: security/src/stark.rs:28-101,147-231,279-340",
    "grinding": f"Plonky3 {PINNED_COMMIT}: security/src/grinding.rs:1-54",
    "wrapper": f"Plonky3 {PINNED_COMMIT}: uni-stark/src/security.rs:174-183,244-279,283-349",
}


class ManifestError(ValueError):
    pass


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _require_int(data: dict[str, Any], key: str, minimum: int = 0) -> int:
    value = data.get(key)
    if not _is_int(value) or value < minimum:
        raise ManifestError(f"{key} must be an integer >= {minimum}")
    return value


def _log2_power_of_two(value: int, key: str) -> int:
    if value <= 0 or value & (value - 1):
        raise ManifestError(f"{key} must be a positive power of two")
    return value.bit_length() - 1


def validate_manifest(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ManifestError("manifest root must be an object")
    if data.get("model_version") != MODEL_VERSION:
        raise ManifestError(f"model_version must be {MODEL_VERSION}")
    if not isinstance(data.get("profile_id"), str) or not data["profile_id"]:
        raise ManifestError("profile_id must be a non-empty string")
    if data.get("plonky3_commit") != PINNED_COMMIT:
        raise ManifestError(f"plonky3_commit must equal pinned commit {PINNED_COMMIT}")

    logical_height = _require_int(data, "logical_trace_height", 1)
    logical_bits = _log2_power_of_two(logical_height, "logical_trace_height")
    proof_bits = _require_int(data, "proof_degree_bits", 0)
    padding_bits = _require_int(data, "hiding_degree_padding_bits", 0)
    if proof_bits != logical_bits + padding_bits:
        raise ManifestError(
            "proof_degree_bits must equal log2(logical_trace_height) + hiding_degree_padding_bits"
        )

    blowup = _require_int(data, "fri_log_blowup", 1)
    arity = _require_int(data, "fri_max_log_arity", 1)
    final_log = _require_int(data, "fri_log_final_poly_len", 0)
    lde_log = proof_bits + blowup
    if lde_log >= 63:
        raise ManifestError("proof_degree_bits + fri_log_blowup must be < 63")
    if final_log > lde_log:
        raise ManifestError("fri_log_final_poly_len exceeds the LDE fold domain")
    if final_log > 0 and final_log >= proof_bits:
        raise ManifestError(
            "nonzero fri_log_final_poly_len must be strictly below proof_degree_bits"
        )
    available_fold_depth = lde_log - final_log
    if available_fold_depth > 0 and arity > available_fold_depth:
        raise ManifestError("fri_max_log_arity exceeds the available LDE fold depth")
    _require_int(data, "fri_num_queries", 1)
    _require_int(data, "commit_grinding_bits", 0)
    _require_int(data, "query_grinding_bits", 0)
    field_bits = _require_int(data, "challenge_field_bits", 1)
    if field_bits > _require_int(data, "extension_field_bits", 1):
        raise ManifestError("challenge_field_bits cannot exceed extension_field_bits")
    _require_int(data, "mmcs_binding_bits_classical", 1)
    _require_int(data, "mmcs_binding_bits_quantum", 1)
    _require_int(data, "num_constraints", 1)
    max_degree = _require_int(data, "max_constraint_degree", 1)
    _require_int(data, "max_combo", 1)
    _require_int(data, "num_batched_functions", 1)
    _require_int(data, "relation_width", 1)
    _require_int(data, "quotient_chunks", 0)
    _require_int(data, "hiding_random_functions", 0)
    is_zk = data.get("is_zk")
    if not isinstance(is_zk, bool):
        raise ManifestError("is_zk must be boolean")
    maximum_buildable_degree = (1 << blowup) if is_zk else (1 << blowup) + 1
    if max_degree > maximum_buildable_degree:
        mode = "zk" if is_zk else "non-zk"
        raise ManifestError(
            f"max_constraint_degree {max_degree} exceeds buildable {mode} limit {maximum_buildable_degree}"
        )
    expected_batched = data["relation_width"] + data["quotient_chunks"] + data["hiding_random_functions"]
    derivation = data.get("batch_count_derivation")
    if derivation not in ("relation_plus_quotient_plus_hiding", "explicit"):
        raise ManifestError(
            "batch_count_derivation must be relation_plus_quotient_plus_hiding or explicit"
        )
    if derivation == "relation_plus_quotient_plus_hiding" and data["num_batched_functions"] != expected_batched:
        raise ManifestError(
            f"num_batched_functions must equal relation_width + quotient_chunks + hiding_random_functions ({expected_batched})"
        )
    if derivation == "explicit":
        rationale = data.get("batch_count_rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            raise ManifestError("explicit batch_count_derivation requires batch_count_rationale")
    omissions = data.get("omissions", [])
    if not isinstance(omissions, list) or not all(isinstance(x, str) and x for x in omissions):
        raise ManifestError("omissions must be a list of non-empty strings")
    return data


def _round(value: float | None) -> float | None:
    return None if value is None else round(max(0.0, value), 9)


def _term(
    name: str,
    formula: str,
    source: str,
    inputs: dict[str, Any],
    classical: float | None,
    quantum: float | None,
    status: str,
    omissions: Iterable[str] = (),
    applies: bool = True,
) -> dict[str, Any]:
    return {
        "term": name,
        "formula": formula,
        "formula_source": source,
        "inputs": inputs,
        "classical_bits": _round(classical),
        "quantum_bits": _round(quantum),
        "proof_status": status,
        "applies": applies,
        "binding": {"classical": False, "quantum": False},
        "omissions": list(omissions),
    }


def _common_terms(m: dict[str, Any], list_size: float, regime: str) -> list[dict[str, Any]]:
    field = float(m["challenge_field_bits"])
    k = float(1 << m["proof_degree_bits"])
    constraints = m["num_constraints"]
    factor = max(
        1.0,
        m["max_constraint_degree"] * (k + m["max_combo"] - 1.0) + (k - 1.0),
    )
    status = RANDOM_STATUS if regime == "random-words" else (LDR_STATUS if regime == "ldr" else "proven")
    status_omissions = [LDR_CONDITION] if regime == "ldr" else []
    ali = field - math.log2(list_size) - math.log2(constraints)
    deep = field - math.log2(list_size) - math.log2(factor)
    return [
        _term(
            "air-random-linear-combination",
            "b = log2(|F|) - log2(L+) - log2(num_constraints)",
            SOURCES["air"],
            {"field_bits": field, "list_size": list_size, "num_constraints": constraints},
            ali,
            ali,
            status,
            status_omissions,
        ),
        _term(
            "deep-ali",
            "b = log2(|F|) - log2(L+) - log2(max_deg*(k+max_combo-1)+(k-1))",
            SOURCES["deep"],
            {
                "field_bits": field,
                "list_size": list_size,
                "max_constraint_degree": m["max_constraint_degree"],
                "k": int(k),
                "max_combo": m["max_combo"],
            },
            deep,
            deep,
            status,
            status_omissions,
        ),
    ]


def _fri_commit_udr(m: dict[str, Any], status: str) -> dict[str, Any]:
    security_num_layers = (m["proof_degree_bits"] + m["fri_log_blowup"] - m["fri_log_final_poly_len"]) // m["fri_max_log_arity"]
    folding_minus_one = (1 << m["fri_max_log_arity"]) - 1
    n = float(1 << (m["proof_degree_bits"] + m["fri_log_blowup"]))
    base = float(m["challenge_field_bits"]) - math.log2(folding_minus_one * (n + 1.0))
    return _term(
        "fri-commit-phase",
        "b = log2(|F|) - log2((folding-1)*(n+1)) + grinding",
        SOURCES["fri_commit_udr"],
        {"field_bits": m["challenge_field_bits"], "folding_factor": folding_minus_one + 1, "n": int(n), "pinned_security_num_layers_guard": security_num_layers, "configured_grinding_bits": m["commit_grinding_bits"]},
        base + m["commit_grinding_bits"],
        base + m["commit_grinding_bits"] / 2.0,
        status,
    )


def _query_term(m: dict[str, Any], alpha: float, status: str, source: str = SOURCES["fri_query"]) -> dict[str, Any]:
    base = -m["fri_num_queries"] * math.log2(alpha)
    return _term(
        "fri-query-phase",
        "b = -num_queries*log2(alpha) + grinding",
        source,
        {"alpha": alpha, "num_queries": m["fri_num_queries"], "configured_grinding_bits": m["query_grinding_bits"]},
        base + m["query_grinding_bits"],
        base + m["query_grinding_bits"] / 2.0,
        status,
    )


def _batch_udr(m: dict[str, Any]) -> dict[str, Any]:
    count = m["num_batched_functions"]
    if count < 2:
        return _term(
            "batched-opening-proximity",
            "not applicable when num_batched_functions < 2",
            SOURCES["batch"],
            {"num_batched_functions": count},
            None,
            None,
            "proven",
            applies=False,
        )
    bits = m["challenge_field_bits"] - (
        m["proof_degree_bits"] + m["fri_log_blowup"] + math.log2(count - 1)
    )
    return _term(
        "batched-opening-proximity",
        "b = log2(|F|) - (log_degree + log_inv_rate + log2(num_functions-1))",
        SOURCES["batch"],
        {"field_bits": m["challenge_field_bits"], "log_degree": m["proof_degree_bits"], "log_inv_rate": m["fri_log_blowup"], "num_batched_functions": count},
        bits,
        bits,
        "proven",
    )


def _batch_ldr(m: dict[str, Any], proximity_m: int) -> dict[str, Any]:
    count = m["num_batched_functions"]
    if count < 2:
        return _term(
            "batched-opening-proximity",
            "not applicable when num_batched_functions < 2",
            SOURCES["batch"],
            {"num_batched_functions": count, "m": proximity_m},
            None,
            None,
            LDR_STATUS,
            [LDR_CONDITION],
            applies=False,
        )
    shifted = proximity_m + 0.5
    dominant = (
        m["proof_degree_bits"]
        + m["fri_log_blowup"]
        + math.log2(2.0 * shifted**5 / 3.0)
        + 1.5 * m["fri_log_blowup"]
    )
    bits = m["challenge_field_bits"] - dominant - math.log2(count - 1)
    return _term(
        "batched-opening-proximity",
        "b = log2(|F|) - log2(2*(m+1/2)^5*n/(3*rho^(3/2))) - log2(num_functions-1)",
        SOURCES["batch"],
        {"field_bits": m["challenge_field_bits"], "m": proximity_m, "n_log2": m["proof_degree_bits"] + m["fri_log_blowup"], "rho": 2.0 ** -m["fri_log_blowup"], "num_batched_functions": count, "dominant_term_only": True},
        bits,
        bits,
        LDR_STATUS,
        [
            LDR_CONDITION,
            "Pinned implementation keeps only the BCHKS25 dominant term; documented subdominant terms are omitted as negligible.",
        ],
    )


def _caps_and_metadata(m: dict[str, Any], status: str) -> list[dict[str, Any]]:
    logical_bits = _log2_power_of_two(m["logical_trace_height"], "logical_trace_height")
    return [
        _term(
            "fri-final-phase",
            "deterministic final-polynomial degree/length check; no probabilistic error term",
            SOURCES["wrapper"],
            {"fri_log_final_poly_len": m["fri_log_final_poly_len"], "declared_bound": 1 << m["fri_log_final_poly_len"]},
            None,
            None,
            "deterministic-check",
            applies=False,
        ),
        _term(
            "commit-grinding-adjustment",
            "commit-phase delta bits = g classically; g/2 under the configured Grover-style quantum model",
            SOURCES["grinding"],
            {"configured_grinding_bits": m["commit_grinding_bits"], "site": "FRI commit challenge"},
            float(m["commit_grinding_bits"]),
            m["commit_grinding_bits"] / 2.0,
            "cost-model-adjustment",
            ["Already included in fri-commit-phase; informational row, not an independent binding term."],
            applies=False,
        ),
        _term(
            "query-grinding-adjustment",
            "query-phase delta bits = g classically; g/2 under the configured Grover-style quantum model",
            SOURCES["grinding"],
            {"configured_grinding_bits": m["query_grinding_bits"], "site": "FRI query challenge"},
            float(m["query_grinding_bits"]),
            m["query_grinding_bits"] / 2.0,
            "cost-model-adjustment",
            ["Already included in fri-query-phase; informational row, not an independent binding term."],
            applies=False,
        ),
        _term(
            "challenge-field-ceiling",
            "b <= conservative challenge-field budget",
            SOURCES["wrapper"],
            {"challenge_field_bits": m["challenge_field_bits"], "extension_field_bits": m["extension_field_bits"]},
            float(m["challenge_field_bits"]),
            float(m["challenge_field_bits"]),
            "assumption",
        ),
        _term(
            "mmcs-binding",
            "b <= stated MMCS binding security",
            "Manifest assumption; not derived by p3-security",
            {"construction": m.get("mmcs_construction", "unspecified")},
            float(m["mmcs_binding_bits_classical"]),
            float(m["mmcs_binding_bits_quantum"]),
            "assumption-unreviewed",
            ["This generic cap is not a structural analysis or a complete Fiat-Shamir/QROM composition theorem."],
        ),
        _term(
            "hiding-degree-padding",
            "proof_degree_bits = logical_degree_bits + hiding_degree_padding_bits",
            "Plonky3 pinned uni-stark/src/security.rs:249-251,326-330",
            {"logical_trace_height": m["logical_trace_height"], "logical_degree_bits": logical_bits, "hiding_degree_padding_bits": m["hiding_degree_padding_bits"], "proof_degree_bits": m["proof_degree_bits"], "is_zk": m["is_zk"]},
            None,
            None,
            "accounting-input",
            applies=False,
        ),
    ]


def _random_words(m: dict[str, Any]) -> dict[str, Any]:
    rho = 2.0 ** -m["fri_log_blowup"]
    eta = ((math.log2(math.e) + m["fri_log_blowup"]) * rho) / m["challenge_field_bits"]
    effective = rho + eta
    if not 0.0 < effective < 1.0:
        random_base = 0.0
    else:
        random_base = -m["fri_num_queries"] * math.log2(effective)
    terms = _common_terms(m, 1.0, "random-words")
    terms.append(
        _term(
            "fri-query-phase",
            "b = num_queries*(-log2(rho+eta)) + grinding; eta=((log2(e)+log_blowup)*rho)/field_bits",
            SOURCES["fri_random"],
            {"rho": rho, "eta": eta, "num_queries": m["fri_num_queries"], "field_bits": m["challenge_field_bits"], "configured_grinding_bits": m["query_grinding_bits"]},
            random_base + m["query_grinding_bits"],
            random_base + m["query_grinding_bits"] / 2.0,
            RANDOM_STATUS,
        )
    )
    terms.append(_fri_commit_udr(m, "proven-within-conjectural-composite"))
    terms.append(
        _term(
            "batched-opening-proximity",
            "no accepted random-words analogue in pinned implementation",
            SOURCES["stark"],
            {"num_batched_functions": m["num_batched_functions"]},
            None,
            None,
            "omitted-unmodeled",
            [f"{RANDOM_BATCH_OMISSION} Actual num_batched_functions={m['num_batched_functions']}; this result is optimistic."],
            applies=False,
        )
    )
    terms.extend(_caps_and_metadata(m, "conjectural"))
    return _finish_regime("random-words", terms, None)


def _udr(m: dict[str, Any]) -> dict[str, Any]:
    k = float(1 << m["proof_degree_bits"])
    n = float(1 << (m["proof_degree_bits"] + m["fri_log_blowup"]))
    rho_plus = (k + m["max_combo"]) / n
    alpha = (1.0 + rho_plus) / 2.0
    if k + m["max_combo"] >= alpha * n:
        raise ManifestError("UDR proximity precondition fails")
    terms = _common_terms(m, 1.0, "udr")
    terms.extend((_query_term(m, alpha, "proven"), _fri_commit_udr(m, "proven"), _batch_udr(m)))
    terms.extend(_caps_and_metadata(m, "proven"))
    return _finish_regime("udr", terms, None)


def _ldr_candidate(m: dict[str, Any], proximity_m: int) -> tuple[float, list[dict[str, Any]]] | None:
    rho = 2.0 ** -m["fri_log_blowup"]
    alpha = (1.0 + 0.5 / proximity_m) * math.sqrt(rho)
    gamma = 1.0 - alpha
    if alpha >= 1.0 or gamma <= 0.0:
        return None
    k = float(1 << m["proof_degree_bits"])
    n = float(1 << (m["proof_degree_bits"] + m["fri_log_blowup"]))
    if k + m["max_combo"] >= (1.0 - gamma) * n:
        return None
    shifted = proximity_m + 0.5
    eps_linear = ((2.0 * shifted**5 + 3.0 * shifted * gamma * rho) * n) / (3.0 * rho * math.sqrt(rho)) + shifted / math.sqrt(rho)
    folding_minus_one = (1 << m["fri_max_log_arity"]) - 1
    base_linear = m["challenge_field_bits"] - math.log2(max(eps_linear * folding_minus_one, 1.0))
    base_n_over_q = (
        m["challenge_field_bits"]
        - math.log2(1 << m["fri_max_log_arity"])
        - math.log2(n + 1.0)
        - math.log2(2.0 * proximity_m + 1.0)
        + 0.5 * math.log2(rho)
    )
    query = _query_term(m, alpha, LDR_STATUS)
    query["omissions"].append(LDR_CONDITION)
    commit = _term(
        "fri-commit-phase",
        "b = min(BCHKS25 linear bound, 2024/1553 n/q bound) + grinding",
        SOURCES["fri_commit_ldr"],
        {"m": proximity_m, "rho": rho, "alpha": alpha, "gamma": gamma, "n": int(n), "bchks25_base_bits": _round(base_linear), "n_over_q_base_bits": _round(base_n_over_q), "configured_grinding_bits": m["commit_grinding_bits"]},
        min(base_linear, base_n_over_q) + m["commit_grinding_bits"],
        min(base_linear, base_n_over_q) + m["commit_grinding_bits"] / 2.0,
        LDR_STATUS,
        [LDR_CONDITION],
    )
    # Pinned best_ldr_m maximizes the quantum-adjusted LDT-only min before full composition.
    ldt_score = min(query["quantum_bits"], commit["quantum_bits"])
    list_size = shifted / math.sqrt(rho)
    terms = _common_terms(m, list_size, "ldr")
    terms.extend((query, commit, _batch_ldr(m, proximity_m)))
    terms.extend(_caps_and_metadata(m, LDR_STATUS))
    return float(ldt_score), terms


def _ldr(m: dict[str, Any]) -> dict[str, Any]:
    trace_length = 1 << m["proof_degree_bits"]
    upper = min(math.ceil(1.0 / (2.0 * (math.sqrt((trace_length + 2.0) / trace_length) - 1.0))), LDR_M_CAP)
    best: tuple[float, int, list[dict[str, Any]]] | None = None
    for proximity_m in range(3, upper + 1):
        candidate = _ldr_candidate(m, proximity_m)
        if candidate is None:
            continue
        score, terms = candidate
        if best is None or score > best[0] or (score == best[0] and proximity_m > best[1]):
            best = (score, proximity_m, terms)
    if best is None:
        return {
            "regime": "ldr",
            "available": False,
            "proof_status": "not-applicable-no-valid-ldr-m",
            "assumptions": [LDR_CONDITION],
            "proximity_m": None,
            "classical_bits": 0.0,
            "quantum_bits": 0.0,
            "floor_classical_bits": 0,
            "floor_quantum_bits": 0,
            "terms": [],
            "bottlenecks": [],
            "omissions": ["Pinned best_ldr_m returned no valid m; UDR remains independently available."],
        }
    return _finish_regime("ldr", best[2], best[1])


def _finish_regime(name: str, terms: list[dict[str, Any]], proximity_m: int | None) -> dict[str, Any]:
    applicable = [t for t in terms if t["applies"] and t["classical_bits"] is not None]
    classical = min(t["classical_bits"] for t in applicable)
    quantum = min(t["quantum_bits"] for t in applicable)
    tolerance = 5e-10
    for term in applicable:
        term["binding"]["classical"] = abs(term["classical_bits"] - classical) <= tolerance
        term["binding"]["quantum"] = abs(term["quantum_bits"] - quantum) <= tolerance
    bottlenecks = sorted(
        ({"term": t["term"], "classical_bits": t["classical_bits"], "quantum_bits": t["quantum_bits"], "binding": t["binding"]} for t in applicable),
        key=lambda x: (x["quantum_bits"], x["classical_bits"], x["term"]),
    )
    return {
        "available": True,
        "proof_status": (
            RANDOM_STATUS
            if name == "random-words"
            else (LDR_STATUS if name == "ldr" else "proven-no-decoding-conjecture")
        ),
        "assumptions": (
            [f"{RANDOM_BATCH_OMISSION} Actual num_batched_functions is recorded per term."]
            if name == "random-words"
            else ([LDR_CONDITION] if name == "ldr" else [])
        ),
        "regime": name,
        "proximity_m": proximity_m,
        "classical_bits": _round(classical),
        "quantum_bits": _round(quantum),
        "floor_classical_bits": math.floor(classical),
        "floor_quantum_bits": math.floor(quantum),
        "terms": terms,
        "bottlenecks": bottlenecks,
    }


def _subtract_targets(regime: dict[str, Any], target_log2: int) -> dict[str, Any]:
    adjusted = json.loads(json.dumps(regime))
    adjusted["target_count_log2"] = target_log2
    adjusted["classical_bits"] = _round(regime["classical_bits"] - target_log2)
    adjusted["quantum_bits"] = _round(regime["quantum_bits"] - target_log2)
    adjusted["floor_classical_bits"] = math.floor(max(0.0, regime["classical_bits"] - target_log2))
    adjusted["floor_quantum_bits"] = math.floor(max(0.0, regime["quantum_bits"] - target_log2))
    for term in adjusted["terms"]:
        if term["applies"] and term["classical_bits"] is not None:
            term["classical_bits"] = _round(term["classical_bits"] - target_log2)
            term["quantum_bits"] = _round(term["quantum_bits"] - target_log2)
    adjusted["bottlenecks"] = sorted(
        ({"term": t["term"], "classical_bits": t["classical_bits"], "quantum_bits": t["quantum_bits"], "binding": t["binding"]} for t in adjusted["terms"] if t["applies"] and t["classical_bits"] is not None),
        key=lambda x: (x["quantum_bits"], x["classical_bits"], x["term"]),
    )
    return adjusted


def exact_union_bits(components: list[tuple[int, float]]) -> float:
    if not components:
        raise ManifestError("composition must contain at least one component")
    if any(count < 1 or bits < 0.0 for count, bits in components):
        raise ManifestError("composition counts must be positive and bits non-negative")
    minimum = min(bits for _, bits in components)
    scaled = sum(count * 2.0 ** (minimum - bits) for count, bits in components)
    return max(0.0, minimum - math.log2(scaled))


def _composition(m: dict[str, Any], classical: float, quantum: float) -> dict[str, Any] | None:
    spec = m.get("composition")
    if spec is None:
        return None
    if not isinstance(spec, dict) or not isinstance(spec.get("components"), list):
        raise ManifestError("composition.components must be a list")
    rows: list[dict[str, Any]] = []
    cparts: list[tuple[int, float]] = []
    qparts: list[tuple[int, float]] = []
    for item in spec["components"]:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise ManifestError("each composition component needs a name")
        count = item.get("count")
        if not _is_int(count) or count < 1:
            raise ManifestError("composition component count must be a positive integer")
        if item.get("use_profile_result") is True:
            cbits, qbits, source = classical, quantum, "profile-best-proven"
        else:
            cbits, qbits = item.get("classical_bits"), item.get("quantum_bits")
            if not isinstance(cbits, (int, float)) or not isinstance(qbits, (int, float)):
                raise ManifestError("fixed composition components need classical_bits and quantum_bits")
            cbits, qbits, source = float(cbits), float(qbits), "manifest-assumption"
        rows.append({"name": item["name"], "count": count, "classical_bits": _round(cbits), "quantum_bits": _round(qbits), "source": source})
        cparts.append((count, cbits))
        qparts.append((count, qbits))
    return {
        "formula": "-log2(sum_i count_i * 2^(-bits_i)) (exact union-bound arithmetic; no min approximation)",
        "components": rows,
        "classical_bits": _round(exact_union_bits(cparts)),
        "quantum_bits": _round(exact_union_bits(qparts)),
        "proof_status": "inherits-component-status; unreviewed",
        "omissions": list(spec.get("omissions", [])),
    }


def calculate(manifest: dict[str, Any]) -> dict[str, Any]:
    m = validate_manifest(json.loads(json.dumps(manifest)))
    random_words = _random_words(m)
    udr = _udr(m)
    ldr = _ldr(m)
    best_proven_classical = max(udr["classical_bits"], ldr["classical_bits"])
    best_proven_quantum = max(udr["quantum_bits"], ldr["quantum_bits"])
    selected_classical = "udr" if udr["classical_bits"] >= ldr["classical_bits"] else "ldr"
    selected_quantum = "udr" if udr["quantum_bits"] >= ldr["quantum_bits"] else "ldr"
    scenarios = []
    for target_log2 in SCENARIOS:
        scenarios.append(
            {
                "target_count_log2": target_log2,
                "method": "conservative union bound across 2^target_count_log2 proof-forgery targets",
                "random_words": _subtract_targets(random_words, target_log2),
                "udr": _subtract_targets(udr, target_log2),
                "ldr": _subtract_targets(ldr, target_log2),
            }
        )
    return {
        "model_version": MODEL_VERSION,
        "profile_id": m["profile_id"],
        "classification": "UNREVIEWED_RESEARCH_RESULT",
        "security_qualified_candidate": False,
        "independent_human_acceptance": False,
        "pinned_plonky3_commit": PINNED_COMMIT,
        "manifest": m,
        "single_target": {
            "random_words": random_words,
            "udr": udr,
            "ldr": ldr,
            "best_proven": {
                "selection": "max(UDR,LDR), because each is an independent valid theorem bound",
                "classical_bits": _round(best_proven_classical),
                "quantum_bits": _round(best_proven_quantum),
                "floor_classical_bits": math.floor(best_proven_classical),
                "floor_quantum_bits": math.floor(best_proven_quantum),
                "selected_classical_regime": selected_classical,
                "selected_quantum_regime": selected_quantum,
                "classical_proof_status": (
                    udr["proof_status"] if selected_classical == "udr" else ldr["proof_status"]
                ),
                "quantum_proof_status": (
                    udr["proof_status"] if selected_quantum == "udr" else ldr["proof_status"]
                ),
                "conditional_assumptions": (
                    [LDR_CONDITION]
                    if "ldr" in (selected_classical, selected_quantum)
                    else []
                ),
            },
        },
        "multi_target_scenarios": scenarios,
        "composition": _composition(m, best_proven_classical, best_proven_quantum),
        "global_omissions": list(m.get("omissions", [])) + [
            "No complete Fiat-Shamir/QROM composition theorem is claimed.",
            "No structural analysis of the configured field, hash, or MMCS is performed by this calculator.",
            "The random-words result omits the batched-opening proximity term exactly as the pinned implementation does.",
        ],
        "review": _review_metadata(),
    }


def rows_for_csv(report: dict[str, Any], target_log2: int = 0) -> list[dict[str, Any]]:
    scenario = next(x for x in report["multi_target_scenarios"] if x["target_count_log2"] == target_log2)
    rows = []
    for regime_name in ("random_words", "udr", "ldr"):
        regime = scenario[regime_name]
        for term in regime["terms"]:
            rows.append(
                {
                    "profile_id": report["profile_id"],
                    "target_count_log2": target_log2,
                    "regime": regime_name,
                    "term": term["term"],
                    "formula_source": term["formula_source"],
                    "formula": term["formula"],
                    "inputs": json.dumps(term["inputs"], sort_keys=True, separators=(",", ":")),
                    "classical_bits": "" if term["classical_bits"] is None else term["classical_bits"],
                    "quantum_bits": "" if term["quantum_bits"] is None else term["quantum_bits"],
                    "proof_status": term["proof_status"],
                    "binding_classical": term["binding"]["classical"],
                    "binding_quantum": term["binding"]["quantum"],
                    "applies": term["applies"],
                    "omissions": " | ".join(term["omissions"]),
                }
            )
    return rows


def render_csv(report: dict[str, Any], target_log2: int = 0) -> str:
    rows = rows_for_csv(report, target_log2)
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def render_table(report: dict[str, Any], target_log2: int = 0) -> str:
    scenario = next(x for x in report["multi_target_scenarios"] if x["target_count_log2"] == target_log2)
    lines = [
        f"Profile: {report['profile_id']}  targets: 2^{target_log2}  external status: UNREVIEWED",
        f"Internal methodology: {report['review']['final']['verdict']}; external cryptographic review: OPEN",
        "",
    ]
    for regime_name in ("random_words", "udr", "ldr"):
        regime = scenario[regime_name]
        lines.append(f"[{regime_name}] classical={regime['classical_bits']:.3f} quantum={regime['quantum_bits']:.3f}")
        lines.append(f"Proof status: {regime['proof_status']}")
        lines.append(f"Assumptions: {' | '.join(regime['assumptions']) or '-'}")
        lines.append("Term                             Classical  Quantum  Status                          Binding")
        lines.append("-------------------------------- --------- --------- ------------------------------- -------")
        for term in regime["terms"]:
            cb = "n/a" if term["classical_bits"] is None else f"{term['classical_bits']:.3f}"
            qb = "n/a" if term["quantum_bits"] is None else f"{term['quantum_bits']:.3f}"
            binding = "/".join(k for k, v in term["binding"].items() if v) or "-"
            lines.append(f"{term['term'][:32]:32} {cb:>9} {qb:>9} {term['proof_status'][:31]:31} {binding}")
            lines.append(f"  formula: {term['formula']}")
            lines.append(f"  source: {term['formula_source']}")
            lines.append(f"  inputs: {json.dumps(term['inputs'], sort_keys=True, separators=(',', ':'))}")
            lines.append(f"  omissions: {' | '.join(term['omissions']) or '-'}")
        lines.append(
            "Bottlenecks (low to high): "
            + ", ".join(
                f"{x['term']}({x['classical_bits']:.3f}c/{x['quantum_bits']:.3f}q)"
                for x in regime["bottlenecks"]
            )
        )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def target_profiles(
    manifest: dict[str, Any],
    targets: Iterable[int] = (80, 100, 112, 128),
    max_queries: int = 512,
    max_log_blowup: int = 12,
) -> dict[str, Any]:
    base = validate_manifest(json.loads(json.dumps(manifest)))
    target_values = tuple(targets)
    regime_names = ("random_words", "udr", "ldr", "best_proven")
    found: dict[tuple[int, str], dict[str, Any] | None] = {
        (target, regime): None for target in target_values for regime in regime_names
    }
    # Compare candidates by queries first, then blowup. This is an explicit
    # search objective, not a proof-size or verifier-cost optimization.
    for blowup in range(1, max_log_blowup + 1):
        for queries in range(1, max_queries + 1):
            trial = dict(base)
            trial["fri_log_blowup"] = blowup
            trial["fri_num_queries"] = queries
            try:
                report = calculate(trial)
            except ManifestError:
                continue
            for regime in regime_names:
                if regime == "best_proven":
                    source_report = report["single_target"]["best_proven"]
                    bits = source_report["quantum_bits"]
                    proof_status = source_report["quantum_proof_status"]
                    assumptions = source_report["conditional_assumptions"]
                else:
                    source_report = report["single_target"][regime]
                    bits = source_report["quantum_bits"]
                    proof_status = source_report["proof_status"]
                    assumptions = source_report["assumptions"]
                for target in target_values:
                    if bits < target:
                        continue
                    candidate = {
                        "fri_log_blowup": blowup,
                        "fri_num_queries": queries,
                        "quantum_bits": bits,
                        "proof_status": proof_status,
                        "assumptions": list(assumptions),
                        "target_recommendation": (
                            "excluded-conjectural-and-batched-opening-unmodeled"
                            if regime == "random_words"
                            else "internal-method-accepted-with-limitations-external-cryptographic-review-open"
                        ),
                    }
                    if regime == "random_words":
                        candidate["batching"] = {
                            "num_batched_functions": base["num_batched_functions"],
                            "modeled": False,
                            "omission": RANDOM_BATCH_OMISSION,
                        }
                    current = found[(target, regime)]
                    if current is None or (queries, blowup) < (
                        current["fri_num_queries"],
                        current["fri_log_blowup"],
                    ):
                        found[(target, regime)] = candidate
    results = []
    for target in target_values:
        by_regime: dict[str, Any] = {}
        for regime in regime_names:
            profile = found[(target, regime)]
            reason = None
            if profile is None:
                reason = (
                    f"not attained for log_blowup 1..{max_log_blowup} and queries "
                    f"1..{max_queries}; a non-query term, buildability constraint, or cap binds"
                )
            default_status = {
                "random_words": RANDOM_STATUS,
                "udr": "proven-no-decoding-conjecture",
                "ldr": LDR_STATUS,
                "best_proven": "selected-regime-status-recorded-in-profile",
            }[regime]
            by_regime[regime] = {
                "attainable": profile is not None,
                "profile": profile,
                "reason": reason,
                "proof_status": profile["proof_status"] if profile is not None else default_status,
                "target_recommendation": (
                    "excluded-conjectural-and-batched-opening-unmodeled"
                    if regime == "random_words"
                    else "internal-method-accepted-with-limitations-external-cryptographic-review-open"
                ),
                "batching_omission": (
                    {
                        "num_batched_functions": base["num_batched_functions"],
                        "modeled": False,
                        "omission": RANDOM_BATCH_OMISSION,
                    }
                    if regime == "random_words"
                    else None
                ),
            }
        results.append(
            {
                "target_quantum_bits": target,
                "regimes": by_regime,
                "security_qualified_candidate": False,
            }
        )
    return {
        "profile_id": base["profile_id"],
        "classification": "UNREVIEWED_RESEARCH_RESULT",
        "review": _review_metadata(),
        "external_cryptographic_review": "OPEN",
        "independent_human_acceptance": False,
        "random_words_eligible_for_target_recommendation": False,
        "search_objective": "minimize fri_num_queries, then fri_log_blowup",
        "search_bounds": {
            "fri_log_blowup": [1, max_log_blowup],
            "fri_num_queries": [1, max_queries],
        },
        "targets": results,
    }


def _load(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ManifestError("manifest root must be an object")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    calc = sub.add_parser("calculate", help="calculate one manifest")
    calc.add_argument("manifest")
    calc.add_argument("--format", choices=("json", "csv", "table"), default="json")
    calc.add_argument("--target-count-log2", type=int, choices=SCENARIOS, default=0)
    targets = sub.add_parser("targets", help="find minimum-query target profiles")
    targets.add_argument("manifest")
    targets.add_argument("--max-queries", type=int, default=512)
    targets.add_argument("--max-log-blowup", type=int, default=12)
    args = parser.parse_args(argv)
    try:
        manifest = _load(args.manifest)
        if args.command == "targets":
            print(
                json.dumps(
                    target_profiles(
                        manifest,
                        max_queries=args.max_queries,
                        max_log_blowup=args.max_log_blowup,
                    ),
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        report = calculate(manifest)
        if args.format == "json":
            print(json.dumps(report, indent=2, sort_keys=True))
        elif args.format == "csv":
            print(render_csv(report, args.target_count_log2), end="")
        else:
            print(render_table(report, args.target_count_log2), end="")
        return 0
    except (ManifestError, OSError, json.JSONDecodeError) as error:
        print(f"security-calculator: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
