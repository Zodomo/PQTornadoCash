"""Instrument the frozen canonical Rust Reader, not a second proof parser.

Only cursor accounting changes. The emitted fork is never used for prover timing.
All replacement anchors fail closed when the pinned source changes.
"""
from pathlib import Path
import collections
import hashlib
import json


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"instrumentation anchor expected once: {old!r}")
    return text.replace(old, new, 1)


def instrument_codec(source):
    source = replace_once(source, "    cursor: usize,\n}", "    cursor: usize,\n    section: String,\n    spans: Vec<(String, usize, usize)>,\n}")
    source = replace_once(source, "    const fn new(bytes: &'a [u8]) -> Self {\n        Self { bytes, cursor: 0 }", "    fn new(bytes: &'a [u8]) -> Self {\n        Self { bytes, cursor: 0, section: \"common_header\".into(), spans: Vec::new() }")
    source = replace_once(source, "        self.cursor = end;\n        Ok(v.try_into().expect(\"length\"))", """        if let Some((label, _, previous_end)) = self.spans.last_mut() {
            if label == &self.section && *previous_end == self.cursor {
                *previous_end = end;
            } else {
                self.spans.push((self.section.clone(), self.cursor, end));
            }
        } else {
            self.spans.push((self.section.clone(), self.cursor, end));
        }
        self.cursor = end;
        Ok(v.try_into().expect("length"))""")
    # The A/B framing reads live outside Reader's methods.
    for anchor, label in [("let a_digest = a.take::<32>()?;", "global_digest"), ("if b.take::<32>()? != proof_id {", "proof_identifier"), ("let b_digest = b.take::<32>()?;", "global_digest"), ("if a.u32()? != PART_A_END {", "terminator"), ("if b.u32()? != PART_B_END {", "terminator")]:
        receiver = "a" if "a." in anchor else "b"
        source = replace_once(source, anchor, f'{receiver}.section = "{label}".into();\n    {anchor}')
    prefix, reader = source.split("impl<'a> Reader<'a> {", 1)
    def wrap(expression, label):
        nonlocal reader
        reader = replace_once(reader, expression, '{ self.section = "' + label + '".into(); ' + expression + ' }')
    for expression, label in [
        ("trace: self.cap()?", "commitment_trace"),
        ("quotient_chunks: self.cap()?", "commitment_quotient"),
    ]:
        field, value = expression.split(": ", 1)
        reader = replace_once(reader, expression, field + ': { self.section = "' + label + '".into(); ' + value + ' }')
    wrap("Some(self.cap()?)", "commitment_random")
    reader = replace_once(reader, "trace_local: self.exts(NUM_WITHDRAWAL_COLS)?,", 'trace_local: { self.section = "ood_trace_local".into(); self.exts(NUM_WITHDRAWAL_COLS)? },')
    wrap("Some(self.exts(NUM_WITHDRAWAL_COLS)?)", "ood_trace_next")
    wrap("(0..16).map(|_| self.exts(4)).collect::<Result<_, _>>()?", "ood_quotient")
    wrap("Some(self.exts(4)?)", "ood_random")
    for anchor, label in [("let points = [vec![1], vec![2], vec![1; 16]];", "hiding_mask_openings"), ("let commits = (0..s.fri_rounds())", "fri_commitments"), ("let pow = (0..s.fri_rounds())", "fri_grinding"), ("let final_poly = self.exts(1 << profile.fri().1)?;", "final_polynomial"), ("let query_pow = self.val()?;", "query_grinding"), ("let digest = self.take()?;", "checkpoint_identifiers"), ("let state = Digest512::from_bytes(self.take()?);", "checkpoint_transcript_state"), ("let air_alpha = self.ext()?;", "checkpoint_challenges"), ("if self.u16()? as usize != s.query_count {", "checkpoint_query_indices"), ("let start = self.u16()? as usize;", "half_query_indices")]:
        reader = replace_once(reader, anchor, f'self.section = "{label}".into();\n        {anchor}')
    # Split each opened input row into mathematical values and hiding masks.
    reader = replace_once(reader, "for batch in 0..3 {\n            inputs.push", "for batch in 0..3 {\n            self.section = format!(\"initial_batch_{batch}_rows\");\n            inputs.push")
    reader = replace_once(reader, "salts: self.rows(q, s.input_matrix_count(batch), MMCS_SALT_ELEMENTS)?,", 'salts: { self.section = format!("initial_batch_{batch}_salts"); self.rows(q, s.input_matrix_count(batch), MMCS_SALT_ELEMENTS)? },')
    reader = replace_once(reader, 'self.rows(q, s.input_matrix_count(batch), MMCS_SALT_ELEMENTS)? },\n                sibling_hashes: self.hashes()?,', 'self.rows(q, s.input_matrix_count(batch), MMCS_SALT_ELEMENTS)? },\n                sibling_hashes: { self.section = format!("initial_batch_{batch}_frontier"); self.hashes()? },')
    reader = replace_once(reader, "for _ in 0..s.fri_rounds() {\n            let sibling_values", 'for round in 0..s.fri_rounds() {\n            self.section = format!("fri_round_{round}_values");\n            let sibling_values')
    reader = replace_once(reader, "salts: self.rows(q, 1, 8)?,", 'salts: { self.section = format!("fri_round_{round}_salts"); self.rows(q, 1, 8)? },')
    reader = replace_once(reader, "sibling_hashes: self.hashes()?,\n            });", 'sibling_hashes: { self.section = format!("fri_round_{round}_frontier"); self.hashes()? },\n            });')
    reader = replace_once(reader, "if Digest512::from_bytes(self.take()?) != parameter {", 'self.section = "parameter_identifier".into();\n        if Digest512::from_bytes(self.take()?) != parameter {')
    reader = replace_once(reader, "if self.u16()? as usize != PUBLIC_VALUES_COUNT {", 'self.section = "public_header_length".into();\n        if self.u16()? as usize != PUBLIC_VALUES_COUNT {')
    reader = replace_once(reader, "let mut pv = [0; PUBLIC_VALUES_COUNT];", 'self.section = "public_statement_fields".into();\n        let mut pv = [0; PUBLIC_VALUES_COUNT];')
    reader = replace_once(reader, """        (0..q)
            .map(|_| {
                (0..m)
                    .map(|_| (0..w).map(|_| self.val()).collect())
                    .collect()
            })
            .collect()""", """        let label = self.section.clone();
        let masks = label.ends_with("_rows");
        (0..q)
            .map(|_| {
                (0..m)
                    .map(|_| (0..w).map(|column| {
                        self.section = if masks && column >= w - 4 {
                            label.replace("_rows", "_row_masks")
                        } else { label.clone() };
                        self.val()
                    }).collect())
                    .collect()
            })
            .collect()""")
    reader = replace_once(reader, "fn hashes(&mut self) -> Result<Vec<[u64; 8]>, StarkCodecError> {\n        let n = self.u32()? as usize;", 'fn hashes(&mut self) -> Result<Vec<[u64; 8]>, StarkCodecError> {\n        let label = self.section.clone();\n        self.section = format!("{label}_count");\n        let n = self.u32()? as usize;\n        self.section = label;')
    reader = replace_once(reader, "if self.cursor == self.bytes.len() {\n            Ok(())", '''if self.cursor == self.bytes.len() {
            if let Some(path) = std::env::var_os("R2_CODEC_LEDGER") {
                use std::io::Write;
                let mut file = std::fs::OpenOptions::new().create(true).append(true).open(path).expect("ledger output");
                let spans = self.spans.iter().map(|(label, start, end)| format!("[\\\"{}\\\",{},{}]", label, start, end)).collect::<Vec<_>>().join(",");
                writeln!(file, "{{\\\"bytes\\\":{},\\\"spans\\\":[{}]}}", self.bytes.len(), spans).expect("ledger write");
            }
            Ok(())''')
    return prefix + "impl<'a> Reader<'a> {" + reader


def extend_prepare(source):
    source = replace_once(source, 'if out.exists() { fs::remove_dir_all(out).context("remove previous prepared inputs")?; }', 'ensure!(!out.exists(), "R2 never overwrites prepared inputs");')
    source = replace_once(source, '.filter(|case| case.tree_depth == TREE_DEPTH).take(30)', '.filter(|case| case.tree_depth == TREE_DEPTH)')
    source = replace_once(source, 'ensure!(selected.len() == 30, "fewer than 30 supported depth-20 corpus cases");', 'ensure!(!selected.is_empty(), "no supported depth-20 corpus cases");')
    source = replace_once(source, '"count":60,"fixed_proofs":30,"distinct_corpus_witnesses":30', '"count":30+selected.len(),"fixed_proofs":30,"distinct_corpus_witnesses":selected.len()')
    return source


def byte_ledger(fixture, instrumentation_path):
    parsed = [json.loads(line) for line in instrumentation_path.read_text().splitlines()]
    if len(parsed) != 2:
        raise ValueError("canonical decoder must emit exactly one A and B ledger")
    result = {"measurement_class": "MEASURED", "method": "instrumented frozen canonical Reader::take; full decode and native verification required", "parts": {}, "shared_sections": []}
    global_labels = {"commitment_trace", "commitment_quotient", "commitment_random", "ood_trace_local", "ood_trace_next", "ood_quotient", "ood_random", "hiding_mask_openings", "fri_commitments", "fri_grinding", "final_polynomial", "query_grinding"}
    payloads = {}
    for part, ledger in zip(("a", "b"), parsed):
        raw = (fixture / f"part-{part}.pqtc").read_bytes()
        abi = (fixture / f"part-{part}.calldata").read_bytes()
        cursor = 0
        totals = collections.Counter()
        sections = []
        for label, start, end in ledger["spans"]:
            if start != cursor or end <= start or end > len(raw):
                raise ValueError(f"non-partitioning canonical span {label}:{start}:{end}")
            cursor = end
            totals[label] += end - start
            sections.append({"section": label, "start": start, "end": end, "bytes": end-start, "sha256": hashlib.sha256(raw[start:end]).hexdigest()})
            payloads[(part, label)] = payloads.get((part, label), b"") + raw[start:end]
        if cursor != len(raw) or ledger["bytes"] != len(raw):
            raise ValueError("canonical parser ledger does not sum to complete proof")
        words = 8 if part == "a" else 9
        offset = 4 + words * 32 + 32
        if int.from_bytes(abi[4+(words-1)*32:4+words*32], "big") != words*32 or int.from_bytes(abi[offset-32:offset], "big") != len(raw) or abi[offset:offset+len(raw)] != raw or any(abi[offset+len(raw):]):
            raise ValueError("noncanonical ABI payload framing")
        alignment = (-len(raw)) % 32
        abi_sections = {"selector":4, "statement":224, "proof_identifier":32 if part == "b" else 0, "dynamic_offset":32, "dynamic_length":32, "proof":len(raw), "alignment":alignment}
        if sum(abi_sections.values()) != len(abi):
            raise ValueError("ABI ledger does not sum")
        result["parts"][part] = {"raw_bytes":len(raw), "abi_bytes":len(abi), "sections":sections, "section_totals":dict(totals), "repeated_global_bytes":sum(totals[k] for k in global_labels), "abi_sections":abi_sections, "zero_bytes":abi.count(0), "nonzero_bytes":len(abi)-abi.count(0), "raw_alignment_bytes":0}
    for label in sorted(set(label for part,label in payloads if part == "a") & set(label for part,label in payloads if part == "b")):
        a, b = payloads[("a",label)], payloads[("b",label)]
        if a == b:
            result["shared_sections"].append({"section":label,"bytes_per_part":len(a),"copies":2,"duplicated_bytes":len(b),"global":label in global_labels})
    result["raw_bytes"] = sum(p["raw_bytes"] for p in result["parts"].values())
    result["abi_bytes"] = sum(p["abi_bytes"] for p in result["parts"].values())
    result["transaction_envelope"] = {"measurement_class":"NOT_EVALUATED", "bytes":None, "note":"Filled from retained signed RLP, never inferred from ABI bytes"}
    return result
