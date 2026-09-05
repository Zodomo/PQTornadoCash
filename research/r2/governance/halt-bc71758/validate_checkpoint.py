#!/usr/bin/env python3
"""Validate retained halt records only; never execute research or contact RPC."""
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def load(path):
    return json.loads(path.read_text())


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def byte_sum(node):
    if node['children']:
        assert sum(byte_sum(child) for child in node['children']) == node['bytes'], node['name']
    return node['bytes']


def main():
    manifest = load(HERE / 'EVIDENCE_MANIFEST.json')
    paths = [row['path'] for row in manifest['files']]
    assert len(paths) == len(set(paths))
    for row in manifest['files']:
        path = ROOT / row['path']
        assert path.resolve().is_relative_to(ROOT), row['path']
        assert path.stat().st_size == row['bytes'], row['path']
        assert digest(path) == row['sha256'], row['path']
    assert load(ROOT / 'research/r2/goal.json')['status'] == 'paused_by_user'
    assert load(ROOT / 'research/r2/governance/resume-status.json')['status'] == 'PAUSED_BY_USER'

    originals = load(ROOT / 'pqtc-independent-review/FINDINGS.json')['findings']
    findings = load(HERE / 'FINDINGS.json')['findings']
    assert len(findings) == len(originals) == 20
    current = {row['id']: row for row in findings}
    assert len(current) == 20
    for original in originals:
        row = current[original['id']]
        for key, value in original.items():
            assert row[key] == value, (original['id'], key)
        assert row['tracking']['status'] != 'OPEN'
        for evidence in row['tracking']['correction_evidence']:
            assert evidence in paths, evidence

    baseline = ROOT / 'research/r2/baseline/outputs/r2-main'
    records = load(baseline / 'results.json')['proofs']
    for record in records:
        directory = baseline / 'proofs' / Path(record['fixture']).name
        ledger = load(directory / 'byte-ledger.json')
        metadata = load(directory / 'proof-metadata.json')
        assert metadata['native_verified'] and metadata['codec_roundtrip_verified']
        for part, values in ledger['parts'].items():
            assert sum(values['section_totals'].values()) == values['raw_bytes']
            assert sum(values['abi_sections'].values()) == values['abi_bytes']
            assert (directory / f'part-{part}.pqtc').stat().st_size == values['raw_bytes']
        assert sum(v['raw_bytes'] for v in ledger['parts'].values()) == ledger['raw_bytes']
        assert sum(v['abi_bytes'] for v in ledger['parts'].values()) == ledger['abi_bytes']

    for folder in ('C1-decomposed', 'C2-horizontal-02', 'C3-decomposed'):
        directory = ROOT / 'research/r2/air/outputs' / folder
        result = load(directory / 'results.json')
        assert result['native_verified'] is True
        assert byte_sum(load(directory / 'byte-ledger.json')) == result['raw_proof_bytes']
        assert (directory / 'proof.postcard').stat().st_size == result['raw_proof_bytes']

    totals = defaultdict(int)
    receipts = {}
    with (HERE / 'GAS_LEDGER.csv').open(newline='') as stream:
        for row in csv.DictReader(stream):
            key = row['regime'], row['transaction']
            if row['kind'] == 'exclusive_receipt_component':
                totals[key] += int(row['gas'])
            else:
                assert row['kind'] == 'total_not_additive'
                assert key not in receipts
                receipts[key] = int(row['gas'])
    assert totals and dict(totals) == receipts
    for row in load(HERE / 'RUN_MANIFEST.json')['commands']:
        assert row['path'] in paths
        assert digest(ROOT / row['path']) == row['sha256']
    result = {'status': 'PASS', 'scope': 'Offline retained-record integrity only; no experiments rerun',
              'evidence_files': len(paths), 'original_findings': len(findings),
              'baseline_proof_records': len(records), 'air_proof_records': 3,
              'reconciled_receipts': len(receipts), 'manifest_sha256': digest(HERE / 'EVIDENCE_MANIFEST.json')}
    (HERE / 'checkpoint-validation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
