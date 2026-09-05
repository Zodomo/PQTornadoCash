#!/usr/bin/env python3
"""Index retained R2 files without treating commands as successful experiments."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
EXCLUDED = {HERE / 'EVIDENCE_MANIFEST.json', HERE / 'checkpoint-validation.json'}
SKIP = {'.git', 'target', '.target', '.work', 'work', 'build', 'node_modules', 'cache', 'out', '__pycache__'}


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    state = json.loads((ROOT / 'research/r2/governance/resume-status.json').read_text())
    active = [ROOT / p for p in state.get('active_output_roots', [])]
    paths = []
    for directory, dirs, files in (ROOT / 'research/r2').walk():
        dirs[:] = [d for d in dirs if d not in SKIP and not d.startswith(('target-', 'resume-gas-work-')) and d != 'resume-build' and directory / d not in active]
        for name in files:
            path = directory / name
            if path in EXCLUDED or name.startswith('.env') or name == '.anchor.lock' or name.endswith('.pyc') or any(path.is_relative_to(p) for p in active):
                continue
            if path.is_symlink():
                raise ValueError(f'evidence symlink not permitted: {path}')
            paths.append(path)
    paths.extend(ROOT / 'pqtc-independent-review' / name for name in ('FINDINGS.json', 'FOLLOW_UP_RESEARCH_PLAN.md', 'RESEARCH_RETURN_TEMPLATE.md'))
    status = state['status']
    commands = []
    for path in sorted(paths):
        if path.name == 'command.json' and 'halt-bc71758' not in path.parts:
            commands.append({'path': str(path.relative_to(ROOT)), 'sha256': digest(path), 'record': json.loads(path.read_text())})
    (HERE / 'RUN_MANIFEST.json').write_text(json.dumps({'schema': 'pqtc.r2.runs.v2', 'status': status, 'scope': 'Commands are execution records, not automatic scientific successes; historical source epochs remain unchanged.', 'commands': commands}, indent=2) + '\n')
    rows = [{'path': str(path.relative_to(ROOT)), 'bytes': path.stat().st_size, 'sha256': digest(path)} for path in sorted(set(paths))]
    manifest = {'schema': 'pqtc.r2.evidence.v2', 'status': status, 'resumed_from': 'bc7175895ebef241914bb15f2902a55683d5485b', 'active_outputs_not_yet_frozen': [str(p.relative_to(ROOT)) for p in active], 'excluded': sorted(str(p.relative_to(ROOT)) for p in EXCLUDED), 'files': rows}
    (HERE / 'EVIDENCE_MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'files': len(rows), 'commands': len(commands), 'status': status}))

if __name__ == '__main__':
    main()
