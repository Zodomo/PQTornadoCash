#!/usr/bin/env python3
"""Check actual numeric commitment IDs and reject changed committed geometry."""
from copy import deepcopy
import json
from pathlib import Path
from run import inventory

ROOT = Path(__file__).resolve().parents[3]
base = json.loads((ROOT / 'research/security-model/manifests/v03-q32.json').read_text())
for name in ('C1-decomposed', 'C2-horizontal-02', 'C3-decomposed'):
    shape = json.loads((ROOT / 'research/r2/air/outputs' / name / 'shape.json').read_text())
    profile = {**base, **shape}
    assert inventory(profile)['observation_status'] == 'matched-native-proof'
    changed = deepcopy(profile)
    changed['observed_input_matrices'][1]['base_width'] += 1
    try:
        inventory(changed)
    except ValueError:
        pass
    else:
        raise AssertionError('changed committed trace width accepted')
print('Three observed inventories accepted; altered trace widths rejected')
