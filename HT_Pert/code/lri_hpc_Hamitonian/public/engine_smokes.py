#!/usr/bin/env python3
"""Small-cutoff smokes of the three window engines of the d = 1 analysis (HT_Pert/code/lri_hpc_Hamitonian).

Each engine is a standalone shipped script; it is copied into <work>/smokes/<name>/ and run there (they write their
output into the current directory), then compared with the shipped record:
  ht5      analysis/eps5_window/challenge-num/ht5.py 2 4 (independent from-scratch engine through eps^5, numpy/scipy)
           vs ht5_out_2_4.json: every number of C, r, g, chk1, chk3, Xref in the four variants within 1e-11 absolute
           (float64 sparse algebra; measured 1.1e-13 across machines); dims equal.
  htb5x    analysis/eps5_window/B/htb5_exact.py 16 (engine B in exact rational arithmetic, cut4 = 16, i.e. Lambda = 4)
           vs B/exact5_c16.json: every field except the run time 'seconds' identical (exact rationals as strings).
  topsum   analysis/identity_checks/challenge-num/topsum.py 8 16 32 64 (closed-form top-shell sums, numba) vs the
           rows L = 8, 16, 32, 64 of top_a.jsonl: every field except 'sec' within 1e-13 relative (bitwise on the
           production stack).
usage: python3 public/engine_smokes.py [--work .work]   (about 20 s with numba compilation; exit 1 on any FAIL)"""
import argparse
import json
import math
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
AN = os.path.join(PKG, 'analysis')


def leaves(x, path=()):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from leaves(v, path + (k,))
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from leaves(v, path + (i,))
    else:
        yield path, x


def run(script, args, wd, env):
    os.makedirs(wd, exist_ok=True)
    shutil.copy2(script, wd)
    r = subprocess.run([sys.executable, os.path.basename(script)] + args, cwd=wd, env=env, capture_output=True,
                       text=True)
    if r.returncode:
        raise RuntimeError(f'{script} failed:\n{r.stderr[-2000:]}')
    return r.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', default=os.path.join(PKG, '.work'))
    a = ap.parse_args()
    W = os.path.abspath(os.path.join(a.work, 'smokes'))
    if os.path.exists(W):
        shutil.rmtree(W)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
               OMP_NUM_THREADS='1')
    env.setdefault('NUMBA_CACHE_DIR', os.path.join(os.path.abspath(a.work), 'numba_cache'))
    rows = []
    # ht5
    run(os.path.join(AN, 'eps5_window', 'challenge-num', 'ht5.py'), ['2', '4'], os.path.join(W, 'ht5'), env)
    new = json.load(open(os.path.join(W, 'ht5', 'ht5_out_2_4.json')))
    ref = json.load(open(os.path.join(AN, 'eps5_window', 'challenge-num', 'ht5_out_2_4.json')))
    worst, bad, n = 0.0, [], 0
    for L in ref:
        for var in ('raw', 'g2D3W', 'Dconn', 'Dfull'):
            a_, b_ = dict(leaves(new[L][var])), dict(leaves(ref[L][var]))
            if a_.keys() != b_.keys():
                bad.append(f'{L}/{var} keys')
                continue
            for k in b_:
                n += 1
                worst = max(worst, abs(a_[k] - b_[k]))
        if list(new[L]['dims']) != list(ref[L]['dims']):
            bad.append(f'{L} dims')
    rows.append(('ht5 2 4', not bad and worst <= 1e-11, f'{n} numbers, max |diff| {worst:.1e} (<= 1e-11); {bad}'))
    # htb5_exact
    run(os.path.join(AN, 'eps5_window', 'B', 'htb5_exact.py'), ['16'], os.path.join(W, 'htb5x'), env)
    new = json.load(open(os.path.join(W, 'htb5x', 'exact5_c16.json')))
    ref = json.load(open(os.path.join(AN, 'eps5_window', 'B', 'exact5_c16.json')))
    new.pop('seconds', None)
    ref.pop('seconds', None)
    nl = len(list(leaves(ref)))
    rows.append(('htb5_exact 16', new == ref, f'{nl} exact fields (rationals as strings) identical: {new == ref}'))
    # topsum
    out = run(os.path.join(AN, 'identity_checks', 'challenge-num', 'topsum.py'), ['8', '16', '32', '64'],
              os.path.join(W, 'topsum'), env)
    new = {r['L']: r for r in (json.loads(ln) for ln in out.split('\n') if ln.startswith('{'))}
    ref = {r['L']: r for r in (json.loads(ln) for ln in open(os.path.join(AN, 'identity_checks', 'challenge-num',
                                                                          'top_a.jsonl')))}
    worst, bitwise = 0.0, True
    for L in (8, 16, 32, 64):
        for k, v in ref[L].items():
            if k in ('sec', 'L'):
                continue
            d = abs(new[L][k] - v) / max(abs(v), 1e-300)
            worst = max(worst, d)
            bitwise &= new[L][k] == v
    rows.append(('topsum 8 16 32 64', sorted(new) == [8, 16, 32, 64] and worst <= 1e-13,
                 f'max rel diff {worst:.1e} (<= 1e-13); bitwise {bitwise}'))
    for name, ok, det in rows:
        print(f"engine_smokes  {name:18s} {'PASS' if ok else 'FAIL'}  {det}")
    nf = sum(not r[1] for r in rows)
    print(f'# engine smokes: {len(rows) - nf} PASS, {nf} FAIL')
    sys.exit(1 if nf else 0)


if __name__ == '__main__':
    main()
