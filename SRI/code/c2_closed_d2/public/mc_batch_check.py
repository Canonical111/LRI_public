#!/usr/bin/env python3
"""Rerun of one production batch of the Monte Carlo (new tool, 2026-10-15). Run from code/c2_closed_d2/
(make -f public.mk mc-batch-check); about 3 min on one core, needs gcc with libquadmath and an x86-64-v3 (AVX2) CPU.

Builds mc/c2mc3.c with the flags of mc/prod.sbatch (-O2 -march=x86-64-v3 -DUSE_QUAD) in <work>/mc_batch and reruns the
first batch of chunk 1 of configuration A (seed 1001, eta 0.05, KAP 0.35, the weights mc/alpha_e0.05_L16_k35.txt,
1.5e7 samples, one batch). The first 1.5e7 samples of the production chunk form its batch 0, so the B (Gaussian slice),
BS (quartic slice) and BD (finite delta) lines of batch 0 in mc/run_A/out_1.txt must come back: equal to the printed
10 digits, or within 1e-8 of the line's largest entry (the extended-precision tiers of the integrand may round
differently on another CPU or libm).
Usage: python3 public/mc_batch_check.py [--work DIR] [--cc gcc]
"""
import argparse, os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
sys.path.insert(0, str(PKG.parent.parent/'verify'))
import sri_lib as L


def batch0(path):
    out = {}
    for line in open(path):
        t = line.split()
        if t and t[0] in ('B', 'BS', 'BD') and t[1] == '0':
            out[t[0]] = [float(x) for x in t[2:]]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', default=str(PKG/'.work'))
    ap.add_argument('--cc', default=os.environ.get('MCC', 'gcc'))
    a = ap.parse_args()
    w = Path(a.work).resolve()/'mc_batch'
    w.mkdir(parents=True, exist_ok=True)
    T = L.Table('c2_closed_d2 mc-batch-check')
    r = subprocess.run([a.cc, '-O2', '-w', '-march=x86-64-v3', '-DUSE_QUAD', '-o', str(w/'c2mc3'), str(PKG/'mc'/'c2mc3.c'),
                        '-lquadmath', '-lm'], capture_output=True, text=True)
    T.check('build', r.returncode == 0, 'exit %d' % r.returncode, 'exit 0', 'flags of mc/prod.sbatch')
    if r.returncode:
        print(r.stderr[-2000:])
        return T.report(w/'mc_batch_check.txt')
    env = dict(os.environ, LMIN='-16', ERRTOL='1e-2', KAP='0.35', NBATCH='1', ALPHAFILE=str(PKG/'mc'/'alpha_e0.05_L16_k35.txt'))
    with open(w/'batch0.txt', 'w') as f:
        r = subprocess.run([str(w/'c2mc3'), '0.05', '15000000', '1001'], cwd=w, env=env, stdout=f, stderr=subprocess.PIPE, text=True)
    T.check('run', r.returncode == 0, 'exit %d' % r.returncode, 'exit 0', 'eta 0.05, 1.5e7 samples, seed 1001')
    new, ref = batch0(w/'batch0.txt'), batch0(PKG/'mc'/'run_A'/'out_1.txt')
    for k in ('B', 'BS', 'BD'):
        x, y = new.get(k, []), ref.get(k, [])
        scale = max([abs(v) for v in y] or [1.0])
        diff = max([abs(u - v) for u, v in zip(x, y)] or [float('inf')])
        same = x == y
        T.check('batch 0 ' + k, len(x) == len(y) and diff <= 1e-8*scale,
                'identical' if same else 'max |diff| %.2g (%.1e of the largest entry)' % (diff, diff/scale),
                'mc/run_A/out_1.txt batch 0', 'equal, or within 1e-8 of the largest entry of the line')
    return T.report(w/'mc_batch_check.txt')


if __name__ == '__main__':
    sys.exit(main())
