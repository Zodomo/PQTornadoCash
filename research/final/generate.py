#!/usr/bin/env python3
"""Deterministically generate and fail-closed check the SP-92 report package."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
REPORT = HERE / "NEXT_GENERATION_RESEARCH_REPORT.md"
MATRIX = HERE / "EXECUTIVE_MATRIX.csv"
QUESTIONS = HERE / "UNRESOLVED_QUESTIONS.md"
SOURCE_MAP = HERE / "report-source-map.json"
OUTCOME = "OUTCOME_D"
RECOMMENDATION = "RECOMMEND_ADDITIONAL_TARGETED_RESEARCH"
FRONTIER = "CURRENT_RESEARCH_FRONTIER_NO_VIABLE_NEXT_BUILD"

SECTIONS = [
    "Executive conclusion", "Scope and evidence boundary", "Reproducibility manifest",
    "v0.1–v0.3 baseline chronology", "Baseline reproduction results",
    "Security model and corrected v0.3 interpretation", "Common benchmark corpus",
    "Application hash/compression experiments", "Merkle/deposit experiments",
    "AIR geometry experiments", "Transcript/verifier experiments",
    "Field/extension experiments", "Hiding FRI Pareto results", "HVZK-WHIR results",
    "STIR/Circle readiness results", "Spartan-WHIR results", "Recursive proof results",
    "Flock/VEIL results", "Aggregation results", "Robust two-call state-machine results",
    "L2/economic results", "Prover UX results", "Security and cryptanalysis review",
    "Advisory applicability matrix", "Candidate Pareto frontiers",
    "One-transaction feasibility conclusion", "Two-transaction fallback conclusion",
    "Recommended next-build architecture, if any", "Rejected/deferred candidates",
    "Unresolved decisions", "Raw evidence index", "Reproduction instructions",
]

SOURCES = {
    "PLAN": "PQTC_NEXT_GENERATION_RESEARCH_PLAN.md",
    "BASE": "research/candidates/v03-baseline/gas/measured-summary.json",
    "BASE_STATUS": "research/candidates/v03-baseline/status.json",
    "SEC": "research/security-model/v03-q32.json",
    "SEC_STATUS": "research/security-model/status.json",
    "CP1": "research/reviews/checkpoint-1-baseline.json",
    "CP2": "research/reviews/checkpoint-2-structural.json",
    "CP3": "research/reviews/checkpoint-3-backends.json",
    "CP4": "research/reviews/checkpoint-4-product.json",
    "SP10": "research/candidates/hash-compression-common/status.json",
    "SP11": "research/candidates/merkle-shape/status.json",
    "SP20": "research/candidates/air-geometry/status.json",
    "SP21": "research/candidates/structured-relation/status.json",
    "SP31": "research/candidates/verifier-optimization-common/status.json",
    "SP31_RESULT": "research/candidates/V9/outputs/benchmark.json",
    "SP40": "research/candidates/field-bakeoff-common/status.json",
    "SP50": "research/fri-pareto/status.json",
    "SP51": "research/candidates/C20-hvzk-whir/status.json",
    "SP52": "research/candidates/C30-stir/status.json",
    "SP53": "research/candidates/C40-circle/status.json",
    "SP60": "research/candidates/C50-spartan-whir/status.json",
    "SP61": "research/candidates/C60-recursion/status.json",
    "SP62": "research/candidates/C70-flock-veil/status.json",
    "SP70": "research/aggregation/status.json",
    "SP71": "research/l2-economics/status.json",
    "SP72": "research/two-call-state/status.json",
    "SP73": "research/prover-operations/status.json",
    "SP80": "research/integrated-finalists/status.json",
    "SP80_RESULT": "research/integrated-finalists/outputs/results.json",
    "SP91": "research/reproduction/independent-result.json",
    "ADVISORY": "research/advisories/status.json",
    "FORMAL": "research/formal-assurance/status.json",
    "RUNTIME": "research/runtime-binding/status.json",
    "PUBLIC": "research/public-statement/status.json",
    "DIGEST": "research/digest-width/status.json",
    "CANDIDATES": "research/summaries/candidate-master.csv",
    "SECURITY": "research/summaries/security-master.csv",
    "GAS": "research/summaries/gas-decomposition.csv",
    "PROOF": "research/summaries/proof-byte-ledger-master.csv",
    "PROVER": "research/summaries/prover-master.csv",
    "RUN_INDEX": "research/summaries/run-index.csv",
    "SCORECARDS": "research/summaries/candidate-scorecards.csv",
    "MINIMUM": "research/summaries/minimum-candidate-matrix.csv",
    "SP90": "research/summaries/spike-results.json",
    "REPRO_COMMANDS": "research/reproduction/command-registry.json",
    "REPRO_NEGATIVE": "research/reproduction/negative-results.json",
}


def load_json(key: str):
    return json.loads((ROOT / SOURCES[key]).read_text())


def read_csv(key: str) -> list[dict[str, str]]:
    with (ROOT / SOURCES[key]).open(newline="") as handle:
        return list(csv.DictReader(handle))


def sha(path: str) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def citation(key: str) -> str:
    return f"[{key}]"


def card(spike_id: str, hypothesis: str, candidates: str, commits: str, completed: str,
         omitted: str, gate: str, evidence: str, security: str, operational: str,
         recommendation: str) -> str:
    if gate not in {"PASS", "CONDITIONAL", "FAIL", "DEFERRED"}:
        raise ValueError(f"invalid result-card gate: {gate}")
    return "\n".join([
        "| Field | Content |", "|---|---|", f"| Spike ID | {spike_id} |",
        f"| Hypothesis | {hypothesis} |", f"| Candidate IDs | {candidates} |",
        f"| Source commits | {commits} |", f"| Completed scope | {completed} |",
        f"| Omitted scope | {omitted} |", f"| Gate result | {gate} |",
        f"| Primary evidence | {evidence} |", f"| Security status | {security} |",
        f"| Operational status | {operational} |", f"| Recommendation | {recommendation} |",
    ])


def spike_section(number: int, title: str, result_card: str, methodology: str,
                  implementation: str, raw: str, distribution: str, comparison: str,
                  confounders: str, failures: str, interpretation: str, artifacts: Iterable[str]) -> str:
    paths = "\n".join(f"- `{path}`" for path in artifacts)
    return f"""## {number}. {title}

{result_card}

### Methodology

{methodology}

### Exact implementation

{implementation}

### Raw results

{raw}

### Confidence intervals/distributions

{distribution}

### Comparison with baseline

{comparison}

### Confounders

{confounders}

### Failures

{failures}

### Interpretation

{interpretation}

### Artifact paths

{paths}
"""


def build_report() -> str:
    base = load_json("BASE")
    sec = load_json("SEC")
    sp80 = load_json("SP80")
    sp91 = load_json("SP91")
    d = base["distributions"]
    assert sp80["eligibleCount"] == sp80["finalistCount"] == sp80["prototypeCount"] == 0
    assert sp80["status"] == FRONTIER
    assert sp91["scope"]["reproduced_claim"].startswith(OUTCOME)
    assert sp91["scope"]["recommendation"] == RECOMMENDATION

    parts: list[str] = ["# PQTornado next-generation research report\n"]
    parts.append(f"""## 1. Executive conclusion

**Outcome:** `{OUTCOME}` — no new full build yet. **Recommendation:** `{RECOMMENDATION}`. The separately recorded SP-80 frontier is `{FRONTIER}`. There are zero security-qualified candidates, zero eligible finalists, and zero complete prototypes. {citation('SP80')}

- **One-transaction feasibility:** not demonstrated. The frozen baseline fails; every theorem-feasible hiding-FRI frontier row also fails the robust two-transaction filter, and no integrated alternative exists. {citation('BASE')} {citation('CP3')}
- **Best candidate and exact measured envelope:** no best eligible candidate exists. The only complete reference is C00, not a candidate for promotion: fresh raw proof median **{d['raw_proof_bytes']['p50']:,.0f} B**, ABI median **{d['abi_calldata_bytes']['p50']:,.0f} B**, Part-A active-total median **{d['a_total']['p50']:,.1f} gas** with **{base['part_a_eip7825_fail_count']} of {base['run_count']}** over the active cap, and Part-B active-total median **{d['b_total']['p50']:,.1f} gas** with **{base['part_b_eip7825_fail_count']} of {base['run_count']}** over it. These are C00 measurements, not a new architecture envelope. {citation('BASE')}
- **Security status and lowest binding term:** not security-qualified and external cryptographic acceptance is open. For q32, the random-words estimate is **107 bits** and conjectural; the theorem-derived Johnson/list-decoding term is **56 bits** and conditional on correlated agreement; the unconditional unique-decoding regime is **37 bits**. The conservative binding result is therefore below the required security target. {citation('CP1')} {citation('SEC')}
- **Deposit cost:** the exact H0 direct deposit measured **13,991,021 execution gas**, above the research deposit UX gate; higher-arity alternatives were stopped. {citation('GAS')} {citation('SP11')}
- **Proof bytes:** C00 median raw proof and ABI sizes are the values above. They are distributions over fresh retained runs, not worst-case bounds; maximum proof length remains unresolved. {citation('BASE')}
- **Prover latency/RSS:** C00 H1 warm-only proof wall-time median is **{d['prove_wall_ms']['p50']:,.3f} ms**, p95 **{d['prove_wall_ms']['p95']:,.3f} ms**, and peak-RSS median **{d['peak_rss_bytes']['p50']:,.0f} B**. Cold H1, H2, H3, portability, cancellation, and recovery were not evaluated. {citation('BASE')} {citation('SP73')}
- **Current/future gas floors:** C00 measured active-schedule totals fail the complete robust gate. The 64- and 96-gas-per-byte scenarios are prospective design scenarios, not active-network receipts; no integrated candidate has exact complete totals under all schedules. {citation('PLAN')} {citation('CP3')}
- **Code/deployment status:** research components and state harnesses exist, but no integrated finalist/prototype exists and deployment is prohibited. C00 runtime/initcode size checks pass, while its pool internal CREATE measured **18,873,630 gas** and exact top-level deployment remains `NOT_EVALUATED`. {citation('BASE')} {citation('SP80')}
- **Full-plan decision:** a full new engineering plan is **not warranted**. Only blocker-closing, source-pinned targeted research is warranted.
- **Three largest unresolved risks:** (1) no externally accepted complete composed security/QROM/structural analysis; (2) no accepted fixed-compression relation feeding a hiding integrated proof; (3) no exact integrated transaction/deployment/prover envelope across required schedules and hardware. {citation('CP4')}

`PASS` means the named spike scope passed, never global qualification. `CONDITIONAL` means useful evidence with an unmet dependency. `FAIL` means a required gate failed. `DEFERRED` means work was intentionally not completed because a prerequisite or maturity gate was absent. `NOT_EVALUATED` is unknown and is never interpreted as zero. `BENCHMARK_ONLY` and projections are non-integrated diagnostics. Internal review is not external cryptographic acceptance.
""")
    parts.append(f"""## 2. Scope and evidence boundary

This report is standalone and frozen to committed evidence through the SP-91 clean detached snapshot at `{sp91['snapshot']['commit']}`. {citation('SP91')} Its allowed basis is retained run records, generated summaries, candidate package status/results, SP-90 scorecards, checkpoints one through four, and the SP-91 record. It excludes private discussion, uncommitted observations, and any conversion of projections or isolated component diagnostics into integrated measurements.

The active hard-cap model is EIP-7825 at **16,777,216 transaction gas**; the current calldata-floor model is EIP-7623; EIP-7976 at **64 gas/byte** and EIP-8311 at **96 gas/byte** are future sensitivity scenarios. EIP-170 bounds runtime code and EIP-3860 bounds/meters initcode. The report's hard research gates are stricter: complete one-call withdrawal no more than **14.0M gas** under each schedule, exact ABI no more than **80 KiB**, runtime module no more than **22,000 B**, and each deployment no more than **14.0M gas**. Robust two-call requires each call no more than **12.0M gas**, combined no more than **20.0M gas**, combined ABI no more than **128 KiB**, bounded state, cleanup, and value movement only after complete verification. {citation('PLAN')}

Security qualification requires a conservative composed result meeting the plan target after quantum, composition, batching, and multi-target adjustments, plus hiding, transcript ordering, exact-instance structural analysis, statement binding, and explicit QROM status. A generic ceiling or conjectural estimate is necessary evidence, not acceptance. No component or bundle met this definition. {citation('PLAN')} {citation('SP80')}
""")

    parts.append(spike_section(3, SECTIONS[2], card(
        "SP-91", "A clean snapshot can reproduce the fail-closed decision.", "C00 and minimum matrix C00–C40",
        sp91["snapshot"]["commit"], "Offline safe checks and evidence-chain reproduction.",
        "Fresh integrated finalist proof/verifier/transaction; none existed.", "PASS", SOURCES["SP91"],
        "External cryptographic review remains open.", "Offline; no network or secret inputs.",
        "Retain Outcome D; do not infer a finalist."),
        "Run registered offline checks from a clean detached worktree and compare deterministic products.",
        "The reproducer validates the pinned inventory, run-record synthesis, scorecards, bundle gate, and stopped dependency states without network actions.",
        f"The snapshot inventory contained **1,886 files**, **60 authoritative baseline records**, **47 research records**, **54 ledger outputs**, **79 SP-90 outputs**, **62 scorecards**, **8 Pareto axes**, and **6 blocked bundles**. {citation('SP91')}",
        "This is an inventory/check result, not a statistical sample and has no confidence interval.",
        "It reproduces C00 and the zero-finalist decision; it does not produce a new proof path.",
        "Committed caches/toolchains can affect runnable commands; the safe checks explicitly avoid subprocess and network work where recorded.",
        "No eligible finalist existed to rebuild. That absence is a reproduced negative result, not a skipped success.",
        "The reproducibility manifest proves custody of committed evidence, not cryptographic correctness.",
        [SOURCES["SP91"], SOURCES["REPRO_COMMANDS"], "research/reproduction/evidence-manifest.json"]))

    parts.append(f"""## 4. v0.1–v0.3 baseline chronology

v0.1 and v0.2 are historical context only; their report-era claims are not relabeled as current measurements. v0.3 is the frozen reproducible reference using P2BB512, a horizontal AIR, and hiding FRI q32. SP-00 regenerated fresh evidence, corrected the security interpretation, and failed the baseline gate. SP-01 separated conjectural random-words, conditional list-decoding, and unconditional unique-decoding claims. Checkpoint one approved the method freeze only, with integration forbidden. {citation('CP1')}

The chronology therefore ends at a failed reference, not a launch point: later components compare against C00 while retaining their own evidence classes.
""")

    parts.append(spike_section(5, SECTIONS[4], card(
        "SP-00", "Frozen v0.3 can be reproduced and clear current gates.", "C00/v03-baseline",
        "d956ac0a7cd878b200be240fa8fd9a1a3da09d30", "Fresh native proofs, native verification, A/B Foundry calls, gas/byte/prover distributions, size checks.",
        "Complete second-client coverage, mined receipts, exact top-level deployment, worst-case proof bound.", "FAIL", SOURCES["BASE"],
        "q32 below qualification under theorem-derived terms; external review open.", "Reference only; public network prohibited.",
        "Keep as frozen negative baseline."),
        "Use the frozen corpus and fixed vectors to produce fresh proofs; report population standard deviation and interpolation percentiles over retained runs.",
        "Pinned Rust prover/verifier plus complete local Foundry pool calls for Part A and Part B; every run retains proof, calldata, gas, and hardware records.",
        f"Across **{base['run_count']} runs**, raw proof p50 was **{d['raw_proof_bytes']['p50']:,.0f} B** (min **{d['raw_proof_bytes']['min']:,.0f}**, max **{d['raw_proof_bytes']['max']:,.0f}**); ABI p50 **{d['abi_calldata_bytes']['p50']:,.0f} B**; Part-A active-total p50 **{d['a_total']['p50']:,.1f} gas**; Part-B active-total p50 **{d['b_total']['p50']:,.1f} gas**. {citation('BASE')}",
        f"Proof p95 **{d['raw_proof_bytes']['p95']:,.1f} B**, p99 **{d['raw_proof_bytes']['p99']:,.2f} B**, population σ **{d['raw_proof_bytes']['stddev']:,.2f} B**; Part-A total p95 **{d['a_total']['p95']:,.1f} gas** and Part-B total p95 **{d['b_total']['p95']:,.1f} gas**. These are empirical distributions, not worst-case bounds. {citation('BASE')}",
        f"The reproduced Part-B total median differs from the prior report by -1.036%; cause was not isolated. Deposit matched the report exactly. {citation('BASE')}",
        "Compiler/harness versus proof-variation attribution remains unresolved; second-client coverage is partial and top-level deployment lacks calldata distribution/receipt evidence.",
        f"Part A exceeded the active cap in **{base['part_a_eip7825_fail_count']} of {base['run_count']}** runs; pool internal CREATE exceeded it; future schedule and worst-case gates remain unpassed. {citation('BASE')}",
        "Correct native/EVM parity does not rescue a security, gas, deployment, or evidence-completeness failure.",
        [SOURCES["BASE_STATUS"], SOURCES["BASE"], "research/summaries/v03-distribution.csv", "research/runs/v03-*.json"]))

    parts.append(spike_section(6, SECTIONS[5], card(
        "SP-01", "Independent accounting can identify the conservative v0.3 security floor.", "C00 q32; C01 q48 comparator",
        "d956ac0a7cd878b200be240fa8fd9a1a3da09d30", "Calculator, theorem regimes, composition omissions, internal method review.",
        "External human cryptographic acceptance, complete QROM/Fiat–Shamir composition, structural MMCS analysis.", "CONDITIONAL", SOURCES["SEC"],
        "Method accepted internally with limitations; no candidate qualified.", "Research calculator only.",
        "Seek external review before any integration."),
        "Calculate each applicable term separately; label conjectural, conditional-theorem, unconditional-theorem, heuristic, and omitted composition explicitly.",
        "Pinned calculator consumes exact relation/FRI/MMCS/transcript parameters and emits per-term bottlenecks rather than one blended score.",
        f"q32 results are **107 conjectural**, **56 conditional Johnson/list-decoding**, and **37 unconditional unique-decoding bits**. {citation('CP1')} The exact lowest accepted operative term remains unsettled because external review is open.",
        "These are analytical bounds/estimates; statistical confidence intervals do not apply. Precision in JSON must not be mistaken for cryptographic confidence.",
        "The old interpretation emphasized random-words. The corrected interpretation foregrounds theorem-derived lower terms and omissions.",
        "The MMCS cap is assumed; random-words omits the batched-opening proximity term; zero knowledge is not graded; no full QROM composition proof exists.",
        "The target is missed under conservative theorem regimes, and self-awarding qualification from the conjectural estimate is forbidden.",
        "The only defensible status is unreviewed PQ-oriented research, not security-qualified.",
        [SOURCES["SEC"], SOURCES["SEC_STATUS"], "research/security-model/external-review-request.md", SOURCES["CP1"]]))

    generic = {
        7: ("SP-00/SP-10", "A common corpus can support comparable candidate evaluation.", "C00; H0–H7", "Semantic corpus and retained fixed vectors were used where implementations existed.", "No integrated post-baseline candidate consumed the full common protocol.", "FAIL", "Corpus mechanics are available, but cross-candidate comparison is blocked by zero eligible relations.", ["research/common-corpus/semantic-cases.json", "research/summaries/run-index.csv"]),
        8: ("SP-10", "A fixed-length compressor can materially reduce the relation and remain acceptable.", "H0–H7", "Rust/TypeScript vectors and Solidity anchors; primitive diagnostics.", "Full required Solidity parity, misuse suite, structural acceptance, eligible AIR relation.", "FAIL", "18,146 Rust/TypeScript vectors and 8 Solidity anchors did not establish an eligible compressor; verdict NO_AIR_CANDIDATE. [SP10]", [SOURCES["SP10"], "research/candidates/hash-compression-common/vectors/cross-language.json.zst"]),
        9: ("SP-11/SP-12", "Tree shape or batching can reduce deposit cost safely.", "H0; higher-arity shapes; deposit batching", "H0 root parity and isolated tree/batch diagnostics.", "Complete transactions for alternatives; accepted compressor; deployable batching path.", "FAIL", "H0 parity passed for 1,000 roots, but higher arity stopped and complete alternative transaction gas was not evaluated. [SP11]", [SOURCES["SP11"], "research/candidates/deposit-batching/status.json", "research/candidates/merkle-shape/outputs/results.json"]),
        10: ("SP-20/SP-21", "Vertical AIR or structured decomposition can shrink the complete relation.", "A0–A4; structured AIR/R1CS/CCS", "Dependency evaluation and source-verified reference mapping.", "Alternative relation implementation, proof integration, gas and prover measurement.", "DEFERRED", "Both studies stopped by dependency because SP-10 produced no eligible compressor; null results are not zero. [SP20] [SP21]", [SOURCES["SP20"], SOURCES["SP21"]]),
        11: ("SP-30/SP-31", "Transcript and verifier changes can create robust complete-path margin.", "T0–T3; V1–V9", "Isolated Solidity measurements, diagnostics, boundary review.", "Full verifier variants, complete claim-state machine, QROM review, integrated path.", "DEFERRED", "T3 is external-review-only. V9 projected minimum margin 1,274,248 gas, but full path is NOT_EVALUATED and the projection is not additive evidence. [SP31_RESULT]", ["research/candidates/T3/status.json", SOURCES["SP31"], "research/candidates/V9/status.json", SOURCES["SP31_RESULT"]]),
        12: ("SP-40", "A different base/challenge field can improve the complete proof.", "F0–F5", "Native and Solidity kernel diagnostics and deterministic vectors.", "Ported full relation/proof/verifier, complete soundness and accepted selection.", "DEFERRED", "All field candidates remain unranked benchmark-only diagnostics; none passed a complete protocol gate. [SP40]", [SOURCES["SP40"], "research/candidates/field-bakeoff-common/outputs/native-latest.json", "research/candidates/field-bakeoff-common/outputs/solidity-latest.json"]),
        13: ("SP-50", "Hiding-FRI parameters can meet security and transaction frontiers.", "C10-fri", "Analytical Cartesian sweep and fresh native anchors.", "Exact complete transaction measurements and external security acceptance.", "FAIL", "504,000 analytical rows were evaluated; 120 retained nondominated q111 rows meeting the generated 100-bit threshold all failed the two-transaction filter; no winner. [SP50] [CP3]", [SOURCES["SP50"], "research/fri-pareto/outputs/analytical-filter.json", "research/summaries/proof-ledger.csv"]),
        14: ("SP-51", "Hiding WHIR can provide a better private backend.", "C20", "Pinned upstream HidingWhirPcs native smoke.", "Exact PQTC relation, matching EVM verifier, QROM reduction and review.", "DEFERRED", "The smoke is UPSTREAM_BASELINE_NOT_PQTC; it is neither an integrated proof nor a candidate measurement. [SP51]", [SOURCES["SP51"], "research/candidates/C20-hvzk-whir/manifest.json"]),
        15: ("SP-52/SP-53", "STIR or Circle can establish a competitive hiding route.", "C30; C40", "Pinned STIR non-hiding lower-bound smoke and Circle source watch.", "Hiding PCS, comparable relation, complete verifier and transaction.", "DEFERRED", "STIR is non-hiding benchmark-only; Circle exposes no comparable hiding path at the pin. [SP52] [SP53]", [SOURCES["SP52"], SOURCES["SP53"]]),
        16: ("SP-60", "Structured Spartan-WHIR can exploit repeated computation with full ZK.", "C50", "Pinned native API and standalone Solidity-WHIR controls.", "Exact PQTC relation, full EVM Spartan path, executable gas harness and license clearance.", "DEFERRED", "Upstream controls exist, but exact relation/end-to-end reproduction and gas are absent; no integration. [SP60]", [SOURCES["SP60"], "research/candidates/C50-spartan-whir/manifest.json"]),
        17: ("SP-61", "Transparent recursion can compress the strongest inner proof.", "C60", "Upstream recursive architecture smoke.", "PQTC recursive Keccak ZK, hiding-WHIR in-circuit adapter, compatible pin, EVM verifier.", "DEFERRED", "Toy recursion is not PQTC; the ZK flag had no relevant effect and no EVM path exists. [SP61]", [SOURCES["SP61"], "research/candidates/C60-recursion/manifest.json"]),
        18: ("SP-62", "Flock/VEIL can combine conventional hashes with lightweight ZK.", "C70 Flock; C70 VEIL", "Source checks and experimental VEIL proof-of-concept controls.", "Executable historical benchmark, current Keccak relation, hiding Flock, EVM verifier, adapter.", "FAIL", "Flock stopped; historical batch-44 panicked at the pin and is not a published measurement. VEIL remains deferred and non-integrated. [SP62]", [SOURCES["SP62"], "research/candidates/C70-flock-veil/manifest.json"]),
        19: ("SP-70", "Aggregation can amortize a qualified individual proof.", "Product aggregation", "Deterministic safety/liveness model and isolated settlement components.", "Accepted individual proof, outer proof, prover/RSS, complete settlement gas/calldata.", "DEFERRED", "Stopped by dependency. Null aggregation metrics remain NOT_EVALUATED, not zero. [SP70]", [SOURCES["SP70"], "research/aggregation/outputs/results.json"]),
        20: ("SP-72", "A bounded A/B state machine can provide a robust fallback.", "Product robust-two-call", "Executable research state machine and attack model.", "Exact integrated proof binding, qualified security, live chain and required hardware.", "FAIL", "State semantics passed their model, but retained projections fail the gas gate and no integrated proof path exists. [SP72]", [SOURCES["SP72"], "research/two-call-state/outputs/results.json"]),
        21: ("SP-71/economic model", "An ordinary L2 route can preserve semantics and materially reduce cost.", "OP-family; Arbitrum-family; Scroll ordinary paths", "Signed transaction generation, source-pinned admission and synthetic fee projections.", "Required network receipts, exact verifier, live cost ratio, semantics evidence.", "FAIL", "A 210 KiB ordinary transaction was rejected by all selected admission-limit projections; required network measurements are incomplete and product gate NOT_EVALUATED. [SP71]", [SOURCES["SP71"], "research/economic-throughput/status.json"]),
        22: ("SP-73", "A finalist can meet practical proving and deployment operations gates.", "C00 operations reference", "Retained-record validation and H1 warm baseline distributions.", "H1 cold, H2/H3, portability, CLI, setup, cancellation, pressure and recovery.", "FAIL", "60 source records and 480 declared artifacts validated, but only H1 warm timing is complete and no finalist exists. [SP73]", [SOURCES["SP73"], "research/prover-operations/results.json"]),
        23: ("SP-01/SP-30/SP-80", "Composed security and cryptanalysis can justify integration.", "All candidate bundles", "Internal methods, structural gate review, source packets and bundle checks.", "External cryptographic acceptance, complete QROM/composition and exact-instance structural review.", "FAIL", "No security-qualified candidate or bundle; internal independent review is explicitly not external cryptographic acceptance. [CP1] [SP80]", [SOURCES["SEC_STATUS"], "research/cryptanalysis/review-packet/status.json", SOURCES["SP80"]]),
        24: ("SP-02", "Pinned advisories and analogous custom paths can be closed.", "Plonky3 and custom Rust/Solidity paths", "Applicability matrix and focused regression runner.", "Malformed-proof panic containment/panic-freedom and independent transcript/shape review.", "FAIL", "Archived failed: the native malformed-proof panic boundary is unresolved; integration remains blocked. [ADVISORY]", [SOURCES["ADVISORY"], "research/advisories/run_regressions.py"]),
    }
    for n in range(7, 25):
        sid, hyp, cand, completed, omitted, gate, raw, arts = generic[n]
        source_commit = "708adad" if n <= 12 else "6f40453"
        parts.append(spike_section(n, SECTIONS[n-1], card(
            sid, hyp, cand, source_commit, completed, omitted,
            gate, arts[0], "Not security-qualified; external acceptance open.",
            "Research/benchmark-only; no custody or deployment authorization.",
            "Close the named blocker only; do not promote."),
            "Apply the plan's common evidence classes and fail closed at missing dependencies.",
            "Use the committed package checker/model/harness named in its status; no component output is relabeled as an integrated result.",
            raw,
            "Where retained distributions exist, the complete CSV is linked. Otherwise the result is deterministic/status evidence and a confidence interval is not applicable. Missing distributions remain `NOT_EVALUATED`.",
            "C00 is the only complete reference path. Isolated kernels, toy relations, upstream smokes, and projections are not directly comparable to its complete pool calls.",
            "Dependency stops, differing relations/hardware, incomplete full paths, and absent external review limit comparison.",
            omitted,
            "The gate result applies to this spike. A local pass or useful negative control cannot satisfy integration, security, transaction, or product gates.",
            arts))

    parts.append(f"""## 25. Candidate Pareto frontiers

Hard gates precede weighted scores. With zero eligible candidates there is no promotable Pareto winner; the complete machine-readable tables are `research/summaries/*.csv` and the eight complete axes are in `research/report-synthesis/pareto/`. {citation('SP90')}

### Candidate master table

| Candidate | Hash | AIR/R1CS | PCS | ZK | Accepted security | Proof B | Tx gas current | Tx gas 64 | Tx gas 96 | Deposit gas | Prove p50 | RSS | Runtime max | Gate |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| C00 [BASE] | P2BB512 | horizontal AIR | hiding FRI q32 | yes | no | {d['raw_proof_bytes']['p50']:,.0f} median | {d['a_total']['p50']:,.1f} Part A median | NOT_EVALUATED | NOT_EVALUATED | 13,991,021 | {d['prove_wall_ms']['p50']:,.3f} ms | {d['peak_rss_bytes']['p50']:,.0f} B median | 17,827 B | FAIL |
| C10-fri [SP50] | frozen H0 | frozen AIR | hiding FRI sweep | yes | no | representative complete CSV | projected only | projected only | projected only | NOT_EVALUATED | anchor CSV | anchor CSV | NOT_EVALUATED | FAIL |
| C20 [SP51] | upstream synthetic | upstream smoke | HidingWhirPcs | yes | no | 36,767 anchor-scale | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | 5.562 ms anchor-scale | 6,389,760 B | NOT_EVALUATED | DEFERRED |
| Bundles A–F [SP80] | mixed | mixed | mixed | required | no | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | FAIL |

### Security table

| Candidate | Primitive generic | Structural review | Proven proof bound | Conjectural proof estimate | Batch term included | QROM | ZK theorem | Multi-target result | Lowest term |
|---|---:|---|---:|---:|---|---|---|---:|---|
| C00 q32 [SEC] | manifest cap only | incomplete | 37 unconditional / 56 conditional | 107 | regime-dependent | incomplete | NOT_EVALUATED | calculator scenarios retained | 37 unconditional |
| H1/H3/H7 [SECURITY] | heuristic ceilings | incomplete | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | incomplete | NOT_EVALUATED | configurable | NOT_ACCEPTED |
| Integrated bundles [SP80] | NOT_EVALUATED | incomplete | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | incomplete | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED |

### Gas decomposition table

| Candidate | Parse/transcript | AIR/R1CS | Openings | LDT/PCS | MMCS | State/payout | Calldata | Floor binding? | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| C00 Part A [BASE] | component ledger linked | component ledger linked | component ledger linked | component ledger linked | component ledger linked | included | exact measured ABI | active execution-bound; future not evaluated | {d['a_total']['p50']:,.1f} median |
| C00 Part B [BASE] | component ledger linked | component ledger linked | component ledger linked | component ledger linked | component ledger linked | included | exact measured ABI | active execution-bound; future not evaluated | {d['b_total']['p50']:,.1f} median |
| V9 [SP31] | isolated only | isolated only | isolated only | isolated only | isolated only | NOT_EVALUATED | projection input | NOT_EVALUATED | NOT_EVALUATED |

### Proof byte ledger

| Candidate | Header | Statement | Global | Queries | Paths/frontiers | Salts/masks | LDT | Final | ABI overhead | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| C00 [BASE] | complete CSV | complete CSV | complete CSV | complete CSV | frontier NOT_EVALUATED | complete CSV | complete CSV | complete CSV | 668 B median | {d['abi_calldata_bytes']['p50']:,.0f} ABI median |
| C10-fri q111 representative [PROOF] | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | included | included | included | included | included | NOT_EVALUATED | 484,577 raw anchor |
| Integrated bundles [SP80] | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED |

### Prover table

| Candidate | Hardware | Threads | Cold/warm | p50 | p95 | p99 | CPU s | RSS | Proof B |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|
| C00 [BASE] | macnch33z3.local-arm64 | 16 | warm | {d['prove_wall_ms']['p50']:,.3f} ms | {d['prove_wall_ms']['p95']:,.3f} ms | {d['prove_wall_ms']['p99']:,.3f} ms | NOT_EVALUATED | {d['peak_rss_bytes']['p50']:,.0f} B median | {d['raw_proof_bytes']['p50']:,.0f} median |
| C20 upstream smoke [PROVER] | H1-MAC16-5-M4MAX-48G | 16 | NOT_APPLICABLE | 5.562 ms (two-anchor median) | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | 6,389,760 B | 36,767 anchor-scale |
| C30 non-hiding smoke [PROVER] | H1-MAC16-5-M4MAX-48G | 16 | NOT_APPLICABLE | 10.686 ms single run | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | 8,962,048 B | 17,407 anchor-scale |

Empty cells in source CSVs and every `NOT_EVALUATED` above mean unknown/unperformed, never numeric zero. Representative C20/C30 values are upstream/synthetic anchor-scale diagnostics, not PQTC integrated measurements. Full tables: `research/summaries/candidate-master.csv`, `security-master.csv`, `gas-decomposition.csv`, `proof-byte-ledger-master.csv`, and `prover-master.csv`.
""")
    parts.append(f"""## 26. One-transaction feasibility conclusion

One-transaction verification does **not** appear feasible on the committed evidence. C00 fails current robust limits, q32 is not security-qualified, q111 analytical rows cannot be promoted to measurements, and no alternative has a complete integrated transaction under current, 64-gas, and 96-gas schedules. A null full-path result is not a zero-gas result. {citation('BASE')} {citation('CP3')} {citation('SP80')}
""")
    parts.append(f"""## 27. Two-transaction fallback conclusion

No robust two-transaction build is recommended. C00's approximate split is reference evidence only; the FRI frontier's retained security-feasible rows all fail the two-call filter, Bundle F is blocked, and SP-72's state machine passes only its abstract safety/liveness scope while the projected gas and full-path binding gates fail. {citation('CP3')} {citation('SP72')} {citation('SP80')}
""")
    parts.append(f"""## 28. Recommended next-build architecture, if any

**No architecture is recommended.** The outcome is `{OUTCOME}` and the decision token is exactly `{RECOMMENDATION}`. A full plan, robust two-call build, aggregation/L2 promotion, or lineage stop would overstate the evidence. Targeted research should close the three executive risks in dependency order; a new build may be reconsidered only after an accepted relation and hiding backend jointly produce exact complete-path evidence. {citation('CP4')}
""")

    stopped = []
    for row in read_csv("CANDIDATES"):
        if row["integration_eligible"] != "true":
            cid = row["candidate_id"]
            status = row["reported_status"] or row["hard_gate_status"]
            kind = row["candidate_kind"]
            category = "security/complexity/maturity"
            if cid.startswith("V") or cid in {"C00", "C00/v03-baseline", "Bundle-F"}:
                category = "gas/calldata/code size/security"
            elif cid in {"C20", "C30", "C40", "C50", "C60", "C70"}:
                category = "privacy/maturity/complexity"
            measurements = f"See `{row['scorecard_path']}` and `{row['artifact_path']}`; blank metrics are NOT_EVALUATED"
            revival = "Revisit only after the named hard-gate blocker has source-pinned evidence and an exact integrated common-protocol run."
            stopped.append(f"| {cid} | {status} | {kind} | {measurements} | {category} | {revival} |")
    parts.append("## 29. Rejected/deferred candidates\n\nEvery non-eligible scorecard is retained below; this intentionally preserves negative and deferred work rather than presenting only representative winners. The reason is the reported status/hard gate, the last stage is the scorecard kind, measurements link the complete record, category names the dominant failure class, and revival is explicit. [CANDIDATES] [SCORECARDS]\n\n| Candidate | Reason | Last completed stage | Measurements | Failure category | Revival condition |\n|---|---|---|---|---|---|\n" + "\n".join(stopped) + "\n")
    parts.append(f"""## 30. Unresolved decisions

The authoritative concise register is [`UNRESOLVED_QUESTIONS.md`](UNRESOLVED_QUESTIONS.md). None is silently assigned zero or treated as passed. The largest blockers are external composed-security acceptance, an eligible fixed relation, and complete integrated operational evidence. Until they close, Outcome D and `{RECOMMENDATION}` remain controlling. {citation('CP4')}
""")
    parts.append(f"""## 31. Raw evidence index

Numeric provenance is machine-readable in [`report-source-map.json`](report-source-map.json). Run-level exact SHA-256 and Keccak-256 hashes are in `research/summaries/run-index.csv` and `research/run-records/evidence-manifest.json`; SP-91's complete snapshot inventory is `research/reproduction/evidence-manifest.json`. The final package manifest is intentionally generated separately after review.

- Baseline run records: `research/runs/v03-*.json`; proof/gas distribution: `research/summaries/v03-distribution.csv`.
- Research run records: paths and both hashes in `research/summaries/run-index.csv`.
- Five master tables: `research/summaries/candidate-master.csv`, `security-master.csv`, `gas-decomposition.csv`, `proof-byte-ledger-master.csv`, `prover-master.csv`.
- Scorecards/frontiers: `research/report-synthesis/scorecards/*.json`, `research/report-synthesis/pareto/*.csv`.
- Negative evidence: section 29, `research/reproduction/negative-results.json`, candidate status files, and checkpoints.
- SP-80 bundle evidence: `research/integrated-finalists/status.json` and `outputs/results.json`.
- SP-91 independent result: `research/reproduction/independent-result.json` at clean commit `{sp91['snapshot']['commit']}`. {citation('SP91')}
""")
    parts.append("""## 32. Reproduction instructions

Run from repository root against the pinned environment. The exact already-recorded SP-91 commands are:

```sh
python3 research/reproduction/reproduce.py all-safe
python3 research/run-records/reproduce.py check
python3 research/report-synthesis/generate.py --check
python3 research/integrated-finalists/check.py
python3 research/candidates/air-geometry/check.py
python3 research/candidates/structured-relation/check.py
python3 research/final/generate.py --check
```

To regenerate only this package (except the separately owned final manifest), run:

```sh
python3 research/final/generate.py
python3 research/final/generate.py --check
```

For the frozen C00 action commands and prerequisites, use `python3 research/reproduction/reproduce.py commands C00`; the exact argv arrays are in `research/reproduction/command-registry.json`. Candidate actions unavailable because no finalist exists must fail closed as `NOT_AVAILABLE_NO_ELIGIBLE_FINALIST`; do not substitute component commands. No command in this section authorizes network broadcast, deployment, secret input, custody integration, or external cryptographic acceptance. [SP91] [REPRO_COMMANDS]
""")
    report = "\n".join(parts).rstrip() + "\n\n### Numeric source notes\n\n"
    for key, path in SOURCES.items():
        report += f"[{key}]: `{path}` (SHA-256 `{sha(path)}`)\n"
    report += "\n"
    return report


def build_matrix() -> str:
    rows = [
        ["outcome", OUTCOME, "no new full build yet", SOURCES["SP91"], sha(SOURCES["SP91"])],
        ["recommendation", RECOMMENDATION, "blocker-closing research only", SOURCES["CP4"], sha(SOURCES["CP4"])],
        ["frontier_status", FRONTIER, "separate SP-80 status", SOURCES["SP80"], sha(SOURCES["SP80"])],
        ["one_tx_feasible", "NO", "not demonstrated; baseline and frontier fail", SOURCES["CP3"], sha(SOURCES["CP3"])],
        ["best_candidate", "NONE", "zero eligible finalists", SOURCES["SP80"], sha(SOURCES["SP80"])],
        ["security_qualified_candidates", "0", "external acceptance open", SOURCES["SP80"], sha(SOURCES["SP80"])],
        ["eligible_finalists", "0", "all bundles blocked", SOURCES["SP80"], sha(SOURCES["SP80"])],
        ["complete_prototypes", "0", "prototype implementation unauthorized", SOURCES["SP80"], sha(SOURCES["SP80"])],
        ["robust_two_tx_build", "NO", "projection fails; full path not evaluated", SOURCES["SP72"], sha(SOURCES["SP72"])],
        ["full_engineering_plan", "NO", "targeted research first", SOURCES["CP4"], sha(SOURCES["CP4"])],
    ]
    out = io.StringIO(newline="")
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["field", "value", "interpretation", "artifact_path", "artifact_sha256"])
    writer.writerows(rows)
    return out.getvalue()


def build_questions() -> str:
    return f"""# Unresolved questions

Controlling outcome: `{OUTCOME}`. Controlling recommendation: `{RECOMMENDATION}`. SP-80 frontier: `{FRONTIER}`. No item below is a positive gate, finalist claim, or authorization to build/deploy.

| Priority | Question | Current state | Evidence needed to close | Blocking decision |
|---|---|---|---|---|
| UQ-01 | What conservative composed security bound is externally accepted for the exact transcript, MMCS, FRI/backend, batching, multi-target and QROM instance? | OPEN; q32 theorem regimes are below target and external review is open. | Written external concrete-security review over exact pinned construction. | Security qualification |
| UQ-02 | Can a fixed-length application compressor pass full semantic parity, misuse, structural and exact-instance review? | OPEN; SP-10 returned `NO_AIR_CANDIDATE`. | Full cross-language coverage, structural analysis, accepted mode, and eligible relation disposition. | Relation selection |
| UQ-03 | Can an accepted relation and hiding backend produce an exact complete pool-facing proof/verifier? | NOT_EVALUATED; zero eligible bundles. | Integrated native proof, native/EVM verification, exact ABI, and statement/hiding evidence. | Any architecture |
| UQ-04 | What are complete current/64/96 transaction totals and worst-case proof bounds? | NOT_EVALUATED for every new integrated candidate. | Exact complete transactions and theorem/validated worst-case byte bounds. | One-call or two-call feasibility |
| UQ-05 | Can robust two-call meet gas, cleanup, bounded-state and atomic-value gates with exact proof binding? | FAIL projection; full path not evaluated. | Integrated A/B receipts, attack tests, cleanup/liveness and exact binding. | Fallback architecture |
| UQ-06 | Can ordinary or explicitly redesigned L2 transport preserve semantics and pass measured cost/admission gates? | Required network scope incomplete; ordinary 210 KiB projections reject. | Exact verifier receipts and live fee/semantics evidence on required routes. | L2 strategy |
| UQ-07 | Can prover operations meet cold H1 and full H2/H3, portability, cancellation, recovery and privacy requirements? | NOT_EVALUATED beyond H1 warm reference. | Repeated retained distributions and operational fault exercises for an eligible finalist. | Product readiness |
| UQ-08 | Can deployment be bound to non-circular parameter/runtime identities and stay within exact creation gates? | Research binding only; top-level creation incomplete. | Canonical deployable artifacts, runtime hashes, constructor/link inputs, receipts and state/code observations. | Deployment |
| UQ-09 | Is malformed-proof panic containment complete for every codec-reachable input? | OPEN/FAIL. | Panic-freedom proof or independently reproduced containment and analogous-path review. | Advisory closure |

A null or `NOT_EVALUATED` answer is unknown, not zero. Revisit the architecture decision only after UQ-01 through UQ-04 have source-pinned closures; otherwise retain `{OUTCOME}` and `{RECOMMENDATION}`.
"""


def build_source_map() -> str:
    entries = []
    for claim_id, path in sorted(SOURCES.items()):
        entries.append({"claim_id": claim_id, "artifact_path": path, "artifact_sha256": sha(path)})
    obj = {
        "schema": "pqtc.sp92.report-source-map.v1",
        "outcome": OUTCOME,
        "recommendation": RECOMMENDATION,
        "frontier_status": FRONTIER,
        "numeric_claim_policy": "Every numeric report claim carries a bracketed claim ID resolving here or names an exact run/artifact path. NOT_EVALUATED is never zero.",
        "entries": entries,
    }
    return json.dumps(obj, indent=2, sort_keys=False) + "\n"


def outputs() -> dict[Path, bytes]:
    return {
        REPORT: build_report().encode(),
        MATRIX: build_matrix().encode(),
        QUESTIONS: build_questions().encode(),
        SOURCE_MAP: build_source_map().encode(),
    }


def validate(content: dict[Path, bytes]) -> None:
    report = content[REPORT].decode()
    headings = [line[3:] for line in report.splitlines() if line.startswith("## ")]
    expected = [f"{i}. {name}" for i, name in enumerate(SECTIONS, 1)]
    if headings != expected:
        raise ValueError("report must contain exactly the required 32 numbered H2 sections")
    required_headers = [
        "| Candidate | Hash | AIR/R1CS | PCS | ZK | Accepted security | Proof B | Tx gas current | Tx gas 64 | Tx gas 96 | Deposit gas | Prove p50 | RSS | Runtime max | Gate |",
        "| Candidate | Primitive generic | Structural review | Proven proof bound | Conjectural proof estimate | Batch term included | QROM | ZK theorem | Multi-target result | Lowest term |",
        "| Candidate | Parse/transcript | AIR/R1CS | Openings | LDT/PCS | MMCS | State/payout | Calldata | Floor binding? | Total |",
        "| Candidate | Header | Statement | Global | Queries | Paths/frontiers | Salts/masks | LDT | Final | ABI overhead | Total |",
        "| Candidate | Hardware | Threads | Cold/warm | p50 | p95 | p99 | CPU s | RSS | Proof B |",
    ]
    if any(header not in report for header in required_headers):
        raise ValueError("mandatory summary table header missing")
    card_header = "| Field | Content |"
    # SP-91 plus every experimental section 5 through 24.
    if report.count(card_header) != 21:
        raise ValueError("per-spike result card coverage drift")
    for token in (OUTCOME, RECOMMENDATION, FRONTIER, "zero security-qualified candidates", "zero eligible finalists", "zero complete prototypes"):
        if token not in report:
            raise ValueError(f"missing fail-closed invariant: {token}")
    if "No architecture is recommended" not in report:
        raise ValueError("architecture conclusion drift")
    if "| Candidate | Reason | Last completed stage | Measurements | Failure category | Revival condition |" not in report:
        raise ValueError("negative-results contract missing")
    matrix = content[MATRIX].decode()
    questions = content[QUESTIONS].decode()
    for token in (OUTCOME, RECOMMENDATION, FRONTIER):
        if token not in matrix or token not in questions:
            raise ValueError(f"cross-deliverable decision drift: {token}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if generated files differ")
    args = parser.parse_args()
    generated = outputs()
    validate(generated)
    if args.check:
        drift = []
        for path, data in generated.items():
            if not path.exists() or path.read_bytes() != data:
                drift.append(path.relative_to(ROOT).as_posix())
        if drift:
            print("SP-92 report drift: " + ", ".join(drift), file=sys.stderr)
            return 1
        print(f"SP-92 report check PASS ({len(generated)} deterministic outputs)")
        return 0
    HERE.mkdir(parents=True, exist_ok=True)
    for path, data in generated.items():
        path.write_bytes(data)
    print(f"generated {len(generated)} SP-92 outputs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
