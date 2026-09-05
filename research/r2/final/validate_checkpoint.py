#!/usr/bin/env python3
"""Validate retained research records only; never execute proofs or contact RPC."""
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
    goal = load(ROOT / 'research/r2/goal.json')
    status = load(ROOT / 'research/r2/governance/resume-status.json')
    states = {'paused_by_user': 'PAUSED_BY_USER', 'research_in_progress': 'RESEARCH_IN_PROGRESS',
              'research_return_with_dispositions': 'RESEARCH_RETURN_WITH_DISPOSITIONS'}
    assert states[goal['status']] == status['status'] == manifest['status']
    assert goal['security_qualification'] == 'SECURITY_NOT_QUALIFIED'
    assert status['packages'][5]['id'] == 'R2-05'
    assert status['packages'][5]['status'] == 'INCOMPLETE_DEFERRED_BY_USER'

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

    proof_hashes = {row['sha256']: row['bytes'] for row in manifest['files']
                    if row['path'].endswith(('.postcard', '.bin', '.pqtc'))}
    anchor_proofs = set()
    resumed_air_proofs = set()
    for relative in paths:
        path = ROOT / relative
        if path.name == 'samples.json' and '/models/outputs/resume-' in relative:
            samples = load(path)
            assert len({r['proof_sha256'] for r in samples}) == len(samples)
            for row in samples:
                assert row['complete_native_verified'] is True
                assert row['proof_bytes'] == proof_hashes[row['proof_sha256']]
                assert row['structural_bytes_residual'] == 0
                assert row['complete_transaction_gas'] is None and row['physical_feasibility'] == 'UNKNOWN'
                anchor_proofs.add(row['proof_sha256'])
        if path.name == 'results.json' and ('/air/outputs/resume-' in relative or '/models/outputs/resume-' in relative):
            row = load(path)
            if isinstance(row, dict) and row.get('native_verified') is True and row.get('proof_path') and row.get('byte_ledger_path'):
                proof = path.parent / row['proof_path']
                assert proof.stat().st_size == row['raw_proof_bytes']
                assert byte_sum(load(path.parent / row['byte_ledger_path'])) == row['raw_proof_bytes']
                resumed_air_proofs.add(digest(proof))

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
              'resumed_anchor_proofs': len(anchor_proofs), 'resumed_air_proofs': len(resumed_air_proofs),
              'reconciled_receipts': len(receipts), 'manifest_sha256': digest(HERE / 'EVIDENCE_MANIFEST.json')}
    (HERE / 'checkpoint-validation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
