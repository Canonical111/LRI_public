#!/usr/bin/env python3
"""Smoke rerun of one blind-solver point: Ds = 0.2, N = 12, raw, started 1e-3 away from its shipped tuned couplings.

Runs the shipped indep_ht.py unchanged on a one-point task file and compares Delta_eps with results/indep_results.json
(tolerance 1e-10: tuning to |F| <= 1e-12, grid error <= 1e-11). About 1-2 min on one core.
"""
import argparse, json, subprocess, sys
from pathlib import Path
PKG = Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser(); ap.add_argument('--work', default=str(PKG / '.work')); a = ap.parse_args()
W = Path(a.work).resolve(); W.mkdir(parents=True, exist_ok=True)
ref = next(p for p in json.loads((PKG / 'results/indep_results.json').read_text())['points']
           if p['delta'] == 0.2 and p['N'] == 12 and p['prescription'] == 'raw')
task = {'points': [{'delta': 0.2, 'N': 12, 'presc': 'raw', 'verify': False, 'r0': ref['r'] * 1.001, 'g0': ref['g'] * 0.999}]}
(W / 'smoke_task.json').write_text(json.dumps(task)); out = W / 'smoke_out.json'
if out.exists(): out.unlink()
pr = subprocess.run([sys.executable, str(PKG / 'indep_ht.py'), '--task', str(W / 'smoke_task.json'), '--out', str(out), '--log', str(W / 'smoke.log')],
                    capture_output=True, text=True)
if pr.returncode != 0: print(pr.stdout[-2000:], pr.stderr[-2000:]); sys.exit(1)
new = next(x for x in json.loads(out.read_text()) if 'Delta_eps' in x)
d = abs(new['Delta_eps'] - ref['Delta_eps']); ok = d <= 1e-10
print(f"smoke Ds=0.2 N=12 raw: Delta_eps {new['Delta_eps']:.12f} vs shipped {ref['Delta_eps']:.12f}, |diff| {d:.1e} (tol 1e-10): {'PASS' if ok else 'FAIL'}")
sys.exit(0 if ok else 1)
