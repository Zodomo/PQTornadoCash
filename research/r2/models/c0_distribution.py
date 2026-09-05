#!/usr/bin/env python3
"""One fresh frozen C0 proof, exported to the shared native postcard comparison."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]
PROVER = ROOT / 'research/r2/baseline/outputs/r2-main/target-clean/release/v03-baseline-reproducer'
EXPORTER = ROOT / 'research/r2/operations/target/release/verify-worker'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists() or not out.is_relative_to(ROOT / 'research/r2'):
        parser.error('fresh R2 output required')
    out.mkdir(parents=True)
    env = {k: v for k, v in os.environ.items() if k in ('PATH', 'HOME', 'TMPDIR', 'RAYON_NUM_THREADS')}
    env['RAYON_NUM_THREADS'] = '1'
    fixture = out / 'canonical'
    command = ['/usr/bin/time', '-l' if platform.system() == 'Darwin' else '-v', str(PROVER), 'prove', '--input', str(args.input.resolve()), '--out', str(fixture)]
    proc = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True)
    (out / 'prove.stdout.log').write_text(proc.stdout)
    (out / 'prove.stderr.log').write_text(proc.stderr)
    record = {'argv': command, 'cwd': str(ROOT), 'environment': env, 'exit_status': proc.returncode, 'prover_sha256': hashlib.sha256(PROVER.read_bytes()).hexdigest(), 'exporter_sha256': hashlib.sha256(EXPORTER.read_bytes()).hexdigest()}
    (out / 'command.json').write_text(json.dumps(record, indent=2) + '\n')
    proc.check_returncode()
    metadata = json.loads((fixture / 'proof-metadata.json').read_text())
    assert metadata['native_verified'] and metadata['codec_roundtrip_verified']
    export = out / 'postcard'
    export_command = [str(EXPORTER), '--statement', str(fixture / 'statement.json'), '--parameter', metadata['parameter_id'], '--part-a', str(fixture / 'part-a.pqtc'), '--part-b', str(fixture / 'part-b.pqtc'), '--export-dir', str(export)]
    exported = subprocess.run(export_command, cwd=ROOT, env=env, capture_output=True, text=True)
    (out / 'export.stdout.log').write_text(exported.stdout)
    (out / 'export.stderr.log').write_text(exported.stderr)
    exported.check_returncode()
    assert json.loads(exported.stdout)['status'] == 'ACCEPTED'
    info = json.loads((export / 'export.json').read_text())
    assert info['native_verified'] and info['roundtrip_verified']
    pattern = r'(\d+)\s+maximum resident set size' if platform.system() == 'Darwin' else r'Maximum resident set size \(kbytes\):\s*(\d+)'
    match = re.search(pattern, proc.stderr)
    rss = int(match[1]) * (1 if platform.system() == 'Darwin' else 1024) if match else None
    result = {'candidate_id': 'R2-C0', 'native_verified': True, 'prove_ms': metadata['prove_ms'], 'verify_ms': metadata['native_verify_ms'], 'raw_proof_bytes': info['raw_proof_bytes'], 'raw_ABI_bytes': metadata['abi_calldata_bytes'], 'peak_rss_bytes': rss, 'rss_scope': 'external time maximum for frozen prover process; postcard export excluded', 'codec': 'postcard1.1.3', 'security': 'SECURITY_NOT_QUALIFIED', 'proof_path': 'postcard/proof.postcard', 'canonical_metadata': 'canonical/proof-metadata.json'}
    (out / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    (out / 'configuration.json').write_text(json.dumps({'experimental_id': metadata['parameter_id'], 'prover_sha256': record['prover_sha256'], 'exporter_sha256': record['exporter_sha256'], 'codec': 'postcard1.1.3'}, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
