#!/usr/bin/env python3
"""Fit-window probe of the flagged moments of the C8 direct finite-cutoff comparison (2026-10-07).

Reads out/C8_ABC/direct_C8_ABC_offsets.json (engine/tests/direct_C8.py, production tiers first) and reruns the direct
component's GLS tool (direct/src/compare_engine.py --offset-fit) on every moment whose verdict is OFFSET, TENSION or
MODEL-FAIL, at eps_max = 0.011, 0.016, 0.051 (the central run uses 0.021), with the same engine series
(direct_C8_ABC_engine.json).  As in the phase-2 assembly (direct_check.py; direct/review/gate2_struct_probe.py): a
verdict that flips, or a d0 that moves by more than its u0, under a change of eps_max is tail-model dependent.
Writes out/C8_ABC/direct_probe_emax<em>.{json,txt} (+ _offsets.json).  No archive file is read.  ~1 min.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
OUT8 = os.path.join(HERE, 'out', 'C8_ABC')
CE = os.path.join(ROOT, 'direct', 'src', 'compare_engine.py')
WINDOWS = ('0.011', '0.016', '0.051')


def main():
    rows = json.load(open(os.path.join(OUT8, 'direct_C8_ABC_offsets.json')))
    flagged = sorted(r['name'] for r in rows if r['verdict'] in ('OFFSET', 'TENSION', 'MODEL-FAIL'))
    print('flagged moments:', flagged)
    if not flagged:
        return
    eng = os.path.join(OUT8, 'direct_C8_ABC_engine.json')
    for em in WINDOWS:
        out = os.path.join(OUT8, f'direct_probe_emax{em}.json')
        with open(out.replace('.json', '.txt'), 'w') as fh:
            subprocess.run([sys.executable, CE, eng, '--offset-fit', '--quiet-raw', '--only', ','.join(flagged),
                            '--fit-eps-max', em, '--out', out], stdout=fh, stderr=subprocess.STDOUT, check=True,
                           cwd=os.path.join(ROOT, 'direct', 'src'))
        for r in json.load(open(out.replace('.json', '_offsets.json'))):
            c = r.get('central') or {}
            print(f"  eps_max {em}: {r['name']:10s} {r['verdict']:12s} d0 {c.get('d0')} +- {c.get('u0')} X2 {c.get('joint_X2')}")


if __name__ == '__main__':
    main()
