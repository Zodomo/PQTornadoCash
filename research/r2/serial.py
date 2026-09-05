#!/usr/bin/env python3
"""Execute an explicit finite R2 command list serially; retain each failed attempt."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--select', help='Comma-separated IDs, in manifest order')
    p.add_argument('--timeout', type=int, default=3600)
    args = p.parse_args()
    out = args.output.resolve()
    if out.exists() or not out.is_relative_to(ROOT / 'research/r2'):
        p.error('fresh R2 output required')
    manifest = json.loads(args.manifest.read_text())
    commands = manifest['commands']
    selected = set(args.select.split(',')) if args.select else {c['id'] for c in commands}
    if selected - {c['id'] for c in commands}:
        p.error('unknown command selection')
    out.mkdir(parents=True)
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    records = []
    for command in commands:
        name = command['id']
        if name not in selected:
            continue
        if Path(name).name != name or name in ('.', '..'):
            raise ValueError('unsafe command id')
        environment = {'RAYON_NUM_THREADS': '1', **command.get('env', {})}
        flags = [item for key, value in environment.items() for item in ('--env', f'{key}={value}')]
        argv = [sys.executable, str(ROOT / 'research/r2/execute.py'), '--output', str(out / name), '--timeout', str(args.timeout), *flags, '--', *command['argv']]
        result = subprocess.run(argv, cwd=ROOT)
        records.append({'id': name, 'exit_status': result.returncode, 'command_record': str((out / name / 'command.json').relative_to(ROOT)), 'scope': 'Command outcome; inspect domain artifacts for proof/correctness/measurement result'})
        (out / 'results.json').write_text(json.dumps(records, indent=2) + '\n')
    print(json.dumps(records))


if __name__ == '__main__':
    main()
