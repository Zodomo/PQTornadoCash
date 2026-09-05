"""Wire-derived byte arithmetic; PQTCC10R1 is NOT the production A/B codec."""
from __future__ import annotations

import hashlib

FIELD_BYTES = 4
EXT_BYTES = 16
DIGEST_BYTES = 64
MODULUS = 2013265921
UNITS = {
    "header_bytes": 1, "count_prefixes": 8, "cap_roots": DIGEST_BYTES,
    "trace_ood_ext": EXT_BYTES, "quotient_ood_ext": EXT_BYTES,
    "random_ood_ext": EXT_BYTES, "mask_ood_ext": EXT_BYTES,
    "input_base": FIELD_BYTES, "input_salt_base": FIELD_BYTES,
    "frontier_digests": DIGEST_BYTES, "fri_sibling_ext": EXT_BYTES,
    "fri_salt_base": FIELD_BYTES, "final_poly_ext": EXT_BYTES,
    "grinding_base": FIELD_BYTES,
}


def byte_model(counts: dict, exact_frontier: bool = True) -> dict:
    if set(counts) != set(UNITS) or any(type(v) is not int or v < 0 for v in counts.values()):
        raise ValueError("complete nonnegative integer wire inventory required")
    sections = {key: counts[key] * unit for key, unit in UNITS.items()}
    if not exact_frontier:
        sections["frontier_digests"] = 0
    return {"measurement_status": "MEASURED" if exact_frontier else "EXACT_ANALYTICAL_BOUND",
            "kind": "exact_serialized_length" if exact_frontier else "lower_bound_omitting_nonnegative_frontier",
            "sections": sections, "total_bytes": sum(sections.values()),
            "abi_bytes": None, "signed_envelope_bytes": None}


def c10_counts(shape: dict, input_frontiers: list[int], fri_frontiers: list[int]) -> dict:
    """Independent PQTCC10R1 formula for uniform full-query openings; no fitted coefficients."""
    q, width, quotient, random = (shape[k] for k in ("queries", "trace_width", "quotient_chunks", "random_codewords"))
    arities = shape["fri_log_arities"]
    rounds = len(arities)
    if len(input_frontiers) != 3 or len(fri_frontiers) != rounds:
        raise ValueError("frontier geometry mismatch")
    counts = dict.fromkeys(UNITS, 0)
    counts.update(header_bytes=9, cap_roots=(3+rounds)*(1 << shape.get("cap_height", 0)),
                  trace_ood_ext=2*width, quotient_ood_ext=quotient*4, random_ood_ext=4,
                  mask_ood_ext=(3+quotient)*random,
                  input_base=q*(4+random+width+random+quotient*(4+random)),
                  input_salt_base=q*(2+quotient)*8,
                  frontier_digests=sum(input_frontiers)+sum(fri_frontiers),
                  fri_sibling_ext=q*sum((1 << a)-1 for a in arities),
                  fri_salt_base=q*rounds*8, final_poly_ext=shape["final_poly_len"],
                  grinding_base=rounds+1)
    # Every u64 is accounted for: degree; caps; OOD vectors; masking batch/matrix/point
    # vectors; FRI caps/witnesses; full input rows/salts; per-round arity/values/salts; final.
    counts["count_prefixes"] = (
        1 + 3 + 2 + 1 + quotient + 1
        + 1 + 3 + (2+quotient) + (3+quotient)
        + 1 + rounds + 1
        + 1 + 9 + 2*q*(3+2+quotient)
        + 1 + rounds*(4+3*q) + 1
    )
    return counts


def frontier_work(indices: list[int], depth: int, cap_height: int = 0) -> dict:
    """Exact binary pruned frontier for supplied transcript-valid indices, not q*depth."""
    if not 0 <= cap_height <= depth or any(type(i) is not int or i < 0 or i >= 1 << depth for i in indices):
        raise ValueError("invalid tree/index geometry")
    nodes = set(indices)
    frontier = hashes = 0
    for _ in range(depth - cap_height):
        frontier += sum((i ^ 1) not in nodes for i in nodes)
        nodes = {i >> 1 for i in nodes}
        hashes += len(nodes)
    return {"frontier_digests": frontier, "internal_hashes": hashes, "opened_leaves": len(set(indices)),
            "cap_roots": 1 << cap_height}


class Reader:
    def __init__(self, raw: bytes):
        self.raw, self.pos = raw, 0
        self.counts = dict.fromkeys(UNITS, 0)
        self.sections = []

    def take(self, n: int, section: str):
        if n < 0 or self.pos + n > len(self.raw):
            raise ValueError(f"truncated {section} at {self.pos}, need {n}")
        start = self.pos
        self.pos += n
        self.sections.append({"section": section, "offset": start, "bytes": n})
        return self.raw[start:self.pos]

    def count(self):
        self.counts["count_prefixes"] += 1
        n = int.from_bytes(self.take(8, "count_prefixes"), "big")
        if n > len(self.raw):
            raise ValueError("unbounded wire count")
        return n

    def fields(self, n: int, category: str, extension: bool = False):
        self.counts[category] += n
        payload = self.take(n * (EXT_BYTES if extension else FIELD_BYTES), category)
        if any(int.from_bytes(payload[i:i+4], "big") >= MODULUS for i in range(0, len(payload), 4)):
            raise ValueError(f"noncanonical BabyBear in {category}")

    def vector(self, category: str, extension: bool = False):
        n = self.count()
        self.fields(n, category, extension)
        return n

    def hashes(self, category: str):
        n = self.count()
        self.counts[category] += n
        self.take(DIGEST_BYTES * n, category)
        return n

    def rows(self, category: str):
        return [[self.vector(category) for _ in range(self.count())] for _ in range(self.count())]


def parse_c10(raw: bytes) -> dict:
    r = Reader(raw)
    if r.take(9, "header_bytes") != b"PQTCC10R1":
        raise ValueError("unsupported research codec magic")
    r.counts["header_bytes"] = 9
    degree_bits = r.count()
    caps = [r.hashes("cap_roots") for _ in range(3)]
    trace = [r.vector("trace_ood_ext", True) for _ in range(2)]
    quotient = [r.vector("quotient_ood_ext", True) for _ in range(r.count())]
    random = r.vector("random_ood_ext", True)
    masks = [[[r.vector("mask_ood_ext", True) for _ in range(r.count())]
              for _ in range(r.count())] for _ in range(r.count())]
    fri_caps = [r.hashes("cap_roots") for _ in range(r.count())]
    r.fields(r.count(), "grinding_base")
    inputs = []
    for _ in range(r.count()):
        inputs.append({"rows": r.rows("input_base"), "salts": r.rows("input_salt_base"),
                       "frontier_digests": r.hashes("frontier_digests")})
    rounds = []
    for _ in range(r.count()):
        log_arity = r.count()
        siblings = [r.vector("fri_sibling_ext", True) for _ in range(r.count())]
        if log_arity < 1 or log_arity > 4 or any(n != (1 << log_arity) - 1 for n in siblings):
            raise ValueError("FRI sibling count must be arity minus one")
        rounds.append({"log_arity": log_arity, "sibling_counts": siblings,
                       "salts": r.rows("fri_salt_base"), "frontier_digests": r.hashes("frontier_digests")})
    final = r.vector("final_poly_ext", True)
    r.fields(1, "grinding_base")
    if r.pos != len(raw) or len(fri_caps) != len(rounds):
        raise ValueError("trailing data or inconsistent FRI rounds")
    model = byte_model(r.counts)
    if model["total_bytes"] != len(raw) or sum(x["bytes"] for x in r.sections) != len(raw):
        raise ValueError("wire formula/parser length disagreement")
    return {"schema": "pqtc.r2.models.codec-ledger.v1", "codec": "PQTCC10R1",
            "proof_sha256": hashlib.sha256(raw).hexdigest(), "wire_counts": r.counts,
            "ledger": model, "parser_sections": r.sections,
            "geometry": {"degree_bits": degree_bits, "caps": caps, "trace_ood_widths": trace,
                         "quotient_ood_widths": quotient, "random_ood_width": random,
                         "mask_ood_widths": masks, "inputs": inputs, "fri_caps": fri_caps,
                         "fri_rounds": rounds, "final_poly_len": final}}


def canonical_v3_model(shape: dict) -> dict:
    """Exact implicit-width codec.rs:42-51,163-228,678-738 for its supported shape.

    Frontier counts must come from the actual independently pruned query halves.
    Omitting them yields a rigorous lower bound, never a fitted frontier estimate.
    """
    q, random = shape["queries"], shape["random_codewords"]
    if q <= 0 or q % 2 or random < 1 or shape.get("trace_width", 190) != 190:
        raise ValueError("canonical v3 requires even queries and frozen width190 H0")
    rounds, width, quotient = 9, 190, 16
    unique = shape["unique_queries"]
    if not 1 <= unique <= q:
        raise ValueError("invalid unique query count")
    global_sections = {
        "commitments": (3 + rounds) * 64,
        "trace_ood": 2 * width * 16,
        "quotient_ood": quotient * 4 * 16,
        "random_ood": 4 * 16,
        "mask_ood": (1 + 2 + quotient) * random * 16,
        "grinding": (rounds + 1) * 4,
        "final_polynomial": 16,
    }
    # checkpoint digest32 + global32 + transcript state64 + three challenges + betas + counts.
    checkpoint = 32 + 32 + 64 + (3 + rounds) * 16 + 4 + (q + unique) * 4
    parts = []
    exact = shape.get("half_frontier_digests") is not None
    for half in range(2):
        frontiers = shape["half_frontier_digests"][half] if exact else [0] * 12
        if len(frontiers) != 12 or any(type(n) is not int or n < 0 for n in frontiers):
            raise ValueError("three input and nine FRI frontier counts required per half")
        n = q // 2
        sections = {"common_header": 338, "global_digest": 32,
                    "proof_id": 32 if half else 0, "checkpoint": checkpoint,
                    "half_indices": 4 + 4*n, "input_rows": n*(4 + random + width + random + quotient*(4 + random))*4,
                    "input_salts": n*(1+1+quotient)*8*4,
                    "fri_siblings": n*rounds*16, "fri_salts": n*rounds*8*4,
                    "frontier_count_prefixes": 12*4, "frontiers": sum(frontiers)*64,
                    "terminator": 4, **{"repeated_global_"+k: v for k, v in global_sections.items()}}
        total = sum(sections.values())
        abi_sections = {"selector": 4, "statement": 224, "proof_identifier": 32 if half else 0,
                        "dynamic_offset": 32, "dynamic_length": 32, "proof": total, "alignment": (-total) % 32}
        parts.append({"sections": sections, "total_bytes": total, "abi_sections": abi_sections,
                      "abi_bytes": sum(abi_sections.values())})
    return {"schema": "pqtc.r2.models.canonical-v3.v1", "parts": parts,
            "total_bytes": sum(p["total_bytes"] for p in parts),
            "measurement_status": "MEASURED" if exact else "EXACT_ANALYTICAL_BOUND",
            "kind": "exact_length_from_observed_frontiers" if exact else "lower_bound_omitting_frontiers",
            "abi_bytes": sum(p["abi_bytes"] for p in parts), "signed_envelope_bytes": None}


def validate_baseline_ledger(ledger: dict) -> dict:
    """Cross-check independent formula against the native Reader::take ledger."""
    a = ledger["parts"]["a"]["section_totals"]
    q = 2 * ((a["half_query_indices"] - 4) // 4)
    unique = (a["checkpoint_query_indices"] - 4) // 4 - q
    frontiers = []
    for part in ("a", "b"):
        totals = ledger["parts"][part]["section_totals"]
        counts = [totals.get(f"initial_batch_{i}_frontier", 0) // 64 for i in range(3)]
        counts += [totals.get(f"fri_round_{i}_frontier", 0) // 64 for i in range(9)]
        frontiers.append(counts)
    predicted = canonical_v3_model({"queries": q, "unique_queries": unique,
                                   "random_codewords": a["hiding_mask_openings"] // (19*16),
                                   "half_frontier_digests": frontiers})
    residuals = []
    for index, part in enumerate(("a", "b")):
        observed = ledger["parts"][part]
        residuals.append({"part": part, "raw_residual": observed["raw_bytes"]-predicted["parts"][index]["total_bytes"],
                          "abi_residual": observed["abi_bytes"]-predicted["parts"][index]["abi_bytes"]})
    if any(r["raw_residual"] or r["abi_residual"] for r in residuals):
        raise ValueError(f"canonical native-parser/formula mismatch: {residuals}")
    return {"formula": predicted, "parser_residuals": residuals, "measurement_status": "MEASURED",
            "signed_envelope_bytes": None}


def postcard_model(raw: bytes, ledger: dict, proof: dict) -> dict:
    """Re-encode the pinned proof schema independently of the native byte ledger.

    MontyField31 binary serde is four little-endian bytes, NOT a postcard varint.
    Digest u64s, vector lengths and usize use ULEB128; extension arrays are fixed.
    """
    def leaves(node, prefix=""):
        name = prefix + "/" + node["name"]
        children = node["children"]
        if children:
            if sum(child["bytes"] for child in children) != node["bytes"]:
                raise ValueError("postcard section children do not partition parent length")
            return [row for child in children for row in leaves(child, name)]
        return [{"section": name, "bytes": node["bytes"]}]
    sections = leaves(ledger)
    if ledger["bytes"] != len(raw) or sum(s["bytes"] for s in sections) != len(raw):
        raise ValueError("native postcard ledger length mismatch")
    encoded = bytearray()
    histogram = dict.fromkeys(range(1, 11), 0)
    fixed_field_bytes = 0
    def uint(value):
        if not isinstance(value, int) or not 0 <= value < 1 << 64:
            raise ValueError("unsigned postcard scalar outside u64")
        start = len(encoded)
        while value >= 128:
            encoded.append((value & 127) | 128)
            value >>= 7
        encoded.append(value)
        histogram[len(encoded)-start] += 1
    def field(value):
        nonlocal fixed_field_bytes
        if not isinstance(value, int) or not 0 <= value < 2013265921:
            raise ValueError("noncanonical Montgomery field representation")
        encoded.extend(value.to_bytes(4, "little"))
        fixed_field_bytes += 4
    def extension(value):
        if len(value["value"]) != 4:
            raise ValueError("quartic extension required")
        for coefficient in value["value"]:
            field(coefficient)
    def vector(values, item):
        uint(len(values))
        for value in values:
            item(value)
    def nested(values, depth, item):
        vector(values, item if depth == 1 else lambda v: nested(v, depth-1, item))
    def option(value, item):
        encoded.append(int(value is not None))
        histogram[1] += 1
        if value is not None:
            item(value)
    def digest(value):
        if len(value) != 8:
            raise ValueError("eight u64 digest words required")
        for word in value:
            uint(word)
    def cap(value):
        vector(value["cap"], digest)
    def opening(value):
        nested(value[0], 3, field)
        vector(value[1]["sibling_hashes"], digest)
    commitments = proof["commitments"]
    cap(commitments["trace"])
    cap(commitments["quotient_chunks"])
    option(commitments["random"], cap)
    opened = proof["opened_values"]
    vector(opened["trace_local"], extension)
    for key in ("trace_next", "preprocessed_local", "preprocessed_next"):
        option(opened[key], lambda v: vector(v, extension))
    nested(opened["quotient_chunks"], 2, extension)
    option(opened["random"], lambda v: vector(v, extension))
    masks, fri = proof["opening_proof"]
    nested(masks, 4, extension)
    vector(fri["commit_phase_commits"], cap)
    vector(fri["commit_pow_witnesses"], field)
    def input_batch(value):
        nested(value["opened_values"], 3, field)
        opening(value["opening_proof"])
    vector(fri["input_openings"], input_batch)
    def fri_round(value):
        uint(value["log_arity"])
        nested(value["sibling_values"], 2, extension)
        opening(value["opening_proof"])
    vector(fri["commit_phase_openings"], fri_round)
    vector(fri["final_poly"], extension)
    field(fri["query_pow_witness"])
    uint(proof["degree_bits"])
    if encoded != raw:
        raise ValueError(f"independent typed postcard encoding differs: expected {len(encoded)} bytes, observed {len(raw)}")
    exact = len(encoded)
    return {"schema": "pqtc.r2.models.postcard.v1", "measurement_status": "MEASURED",
            "kind": "exact_value_dependent_wire_length", "total_bytes": exact,
            "scalar_width_histogram": histogram, "fixed_field_bytes": fixed_field_bytes, "native_sections": sections,
            "lower_bound": {"measurement_status": "EXACT_ANALYTICAL_BOUND",
                            "bytes": fixed_field_bytes + sum(histogram.values()),
                            "assumption": "same typed inventory; Montgomery fields occupy four bytes, variable scalars/counts and option tags at least one"},
            "structural_bytes_residual": len(raw)-exact, "abi_bytes": None,
            "frontier_policy": "Native ledger retains actual shared frontier; no q*capHeight subtraction",
            "signed_envelope_bytes": None}
