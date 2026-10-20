#!/usr/bin/env python3
"""Smoke test of LRI_C5_d3: two fresh computations with the package's own code, compared with the shipped values.

Added for the public release (2026-10-13). Run from GFF/code/LRI_C5_d3 (or `make -f public.mk smoke`):

    python3 public/smoke_c5_d3.py [--work .work]

  S1  Q3, P4(3), P5(3) from the d = 3 reduction formulas at 90 working digits (inputs/general_d3/d3_reduction.py,
      unchanged; the settings N = 160, K = 64 of the stored 90-digit run), compared with the 90-digit run of
      inputs/general_d3/period_values.json.  About 15-20 s.  Needs mpmath.
  S2  K3 from the residue series gs:Kseries in Arb ball arithmetic (wf_K3/k3flint.py, unchanged) at reduced settings
      (400 bits, L = 100, N0 = 1500, KN = 90, KL = 140), compared with the 430-digit wf_K3/K3_value.json.
      About 3 s.  Needs python-flint; skipped (not failed) if it is missing.
Writes <work>/smoke/SMOKE_c5_d3.md; exits 1 on any FAIL.
"""
import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import mpmath as mp

PKG = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', default=str(PKG / '.work'))
    a = ap.parse_args()
    W = Path(a.work).resolve() / 'smoke'
    shutil.rmtree(W, ignore_errors=True)
    W.mkdir(parents=True)
    rows = []

    # S1: periods at 90 digits
    t = time.time()
    sys.path.insert(0, str(PKG / 'inputs' / 'general_d3'))
    from d3_reduction import amplitudes, periods   # noqa: E402  (the package's evaluator, imported read-only)
    mp.mp.dps = 90
    amp = amplitudes(160, 64)
    v = periods(160, 64, amp)
    ref = [r for r in json.load(open(PKG / 'inputs/general_d3/period_values.json'))['runs'] if r['dps'] == 90][0]['values']
    for k in ('Q3', 'P4_3', 'P5_3'):
        x = mp.re(mp.mpmathify(v[k])) if not isinstance(v[k], str) else mp.re(mp.mpmathify(v[k].replace(' ', '')))
        y = mp.re(mp.mpmathify(str(ref[k]).replace(' ', '')))
        d = abs(x - y)
        rows.append(('S1', k + ' at 90 digits', d <= mp.mpf('1e-85'), mp.nstr(x, 40), 'diff %s' % mp.nstr(d, 3), '1e-85 abs',
                     'd3_reduction.periods(160, 64) vs period_values.json run dps 90 (%.0f s)' % (time.time() - t)))
        print(rows[-1][:5], flush=True)

    # S2: K3 by the Arb residue series at reduced settings
    try:
        import flint  # noqa: F401
        have_flint = True
    except ImportError:
        have_flint = False
    if not have_flint:
        rows.append(('S2', 'K3 by k3flint.py', None, 'python-flint missing', '-', '-', 'pip install python-flint'))
    else:
        t = time.time()
        d = W / 'k3'; d.mkdir()
        shutil.copy2(PKG / 'wf_K3/k3flint.py', d)
        p = subprocess.run([sys.executable, 'k3flint.py', '400', '100', '1500', '90', '140', 'k3_smoke.json'], cwd=str(d),
                           capture_output=True, text=True)
        if p.returncode:
            rows.append(('S2', 'K3 by k3flint.py', False, 'rc=%d' % p.returncode, '-', '-', p.stderr[-300:]))
        else:
            mp.mp.dps = 460
            k = mp.mpf(json.load(open(d / 'k3_smoke.json'))['K3'])
            K3 = mp.mpf(json.load(open(PKG / 'wf_K3/K3_value.json'))['K3'])
            dd = abs(k - K3)
            rows.append(('S2', 'K3 by k3flint.py (400 bits)', dd <= mp.mpf('1e-90'), mp.nstr(k, 40), 'diff %s' % mp.nstr(dd, 3),
                         '1e-90 abs', 'k3flint.py 400 100 1500 90 140 vs wf_K3/K3_value.json (%.0f s)' % (time.time() - t)))
            print(rows[-1][:5], flush=True)

    st = lambda ok: 'SKIP' if ok is None else ('PASS' if ok else 'FAIL')
    lines = ['# LRI_C5_d3 smoke test', '', 'Python %s, mpmath %s.' % (sys.version.split()[0], mp.__version__), '',
             '| step | check | status | value | deviation | tolerance | source |', '|---|---|---|---|---|---|---|']
    for r in rows:
        lines.append('| %s | %s | %s | %s | %s | %s | %s |' % (r[0], r[1], st(r[2]), r[3], r[4], r[5], r[6]))
    (W / 'SMOKE_c5_d3.md').write_text('\n'.join(lines) + '\n')
    nf = sum(r[2] is False for r in rows)
    print('%s: %d checks, %d FAIL; table in %s' % ('FAIL' if nf else 'PASS', len(rows), nf, W / 'SMOKE_c5_d3.md'))
    sys.exit(1 if nf else 0)


if __name__ == '__main__':
    main()
