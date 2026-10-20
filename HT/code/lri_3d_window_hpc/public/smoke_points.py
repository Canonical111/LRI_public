#!/usr/bin/env python3
"""`make -f public.mk smoke`: re-solve a few low-cutoff production points and compare them with the records.

For each (x, L) below, the point driver (code/hpc_run.py) is run with the configuration stored in the shipped
record (cutoff, x, n_z, window scheme, tolerances, bath limit) and the same continuation inputs (--basis: the shipped
teacher_L6 record; --seed: the shipped record the production step was seeded from, as named in the record). The new Delta_E, r and g must match the record to 1e-9
(the production tuning tolerance is 3e-11; the margin absorbs BLAS/CPU differences). Minutes on 4 cores.
"""
import argparse, json, os, subprocess, sys, time
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
POINTS = [(0.7, 8), (0.7, 10), (0.518149, 8), (0.518149, 10)]

def shipped(root, original):
    """The record names its inputs by production path (<SCRATCH>/ht3d/campaigns/...); use the shipped copy."""
    s = str(original); i = s.find('/campaigns/')
    return root / s[i + len('/campaigns/'):]

def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--campaigns', default=str(PKG / '../../data/HT_3d/campaigns'))
    ap.add_argument('--threads', type=int,
                    default=int(os.environ.get('NUMBA_NUM_THREADS') or os.environ.get('SLURM_CPUS_PER_TASK') or 4))
    ap.add_argument('--tol', type=float, default=1e-9)
    a = ap.parse_args()
    root = Path(a.campaigns).resolve(); work = PKG / '.work' / 'smoke'; work.mkdir(parents=True, exist_ok=True)
    rows = []
    for x, L in POINTS:
        camp = 'grid18sri' if x == 0.518149 else 'grid18'
        base = root / camp / 'results' / 't16' / f'x{x:g}'
        rec = json.loads((base / f'window_L{L}.json').read_text()); c = rec['configuration']
        out = work / f'x{x:g}_L{L}.json'
        for p in (out, out.with_name(out.name + '.checkpoint.json')):
            if p.exists(): p.unlink()
        argv = [sys.executable, '-B', 'code/hpc_run.py', '--L', str(L), '--x', repr(x), '--nz', str(c['nz']), '--osc', str(c['osc']),
                '--backend', c['backend'], '--window', c['window'], '--window-mode', c['window_mode'],
                '--diagnostics', 'none', '--threads', str(a.threads), '--ncv', str(c['ncv']), '--eig-tol', repr(c['eig_tol']),
                '--residual-tol', repr(c['residual_tol']), '--tuning-tol', repr(c['tuning_tol']), '--maxiter', str(c['maxiter']),
                '--max-bath-states', str(c['max_bath_states']), '--memory-limit-gib', '8',
                '--basis', str(shipped(root, c['basis'])), '--seed', str(shipped(root, c['seed'])),
                '--output', str(out)]
        t = time.time()
        env = {**os.environ, 'NUMBA_NUM_THREADS': str(a.threads)}   # numba refuses more threads than this cap
        rc = subprocess.run(argv, cwd=PKG, env=env, stdout=open(work / f'x{x:g}_L{L}.log', 'w'), stderr=subprocess.STDOUT).returncode
        if rc != 0 or not out.exists():
            rows.append((x, L, None, None, 'FAIL', time.time() - t)); continue
        new = json.loads(out.read_text())
        d = max(abs(new[k] - rec[k]) for k in ('Delta_thermal', 'r', 'g'))
        rows.append((x, L, rec['Delta_thermal'], d, 'PASS' if d <= a.tol else 'FAIL', time.time() - t))
    print(f"{'x':<9} {'L':>2}  {'record Delta_E':<18} {'max |diff| (D, r, g)':<20} status  seconds")
    for x, L, D, d, s, sec in rows:
        Ds = '-' if D is None else f'{D:.15f}'; ds = '-' if d is None else f'{d:.1e}'
        print(f"{x:<9} {L:>2}  {Ds:<18} {ds:<20} {s:<6}  {sec:6.1f}")
    bad = [r for r in rows if r[4] != 'PASS']
    print(f"{len(rows) - len(bad)}/{len(rows)} points reproduced to {a.tol:g}; logs in {work}")
    return 1 if bad else 0

if __name__ == '__main__':
    sys.exit(main())
