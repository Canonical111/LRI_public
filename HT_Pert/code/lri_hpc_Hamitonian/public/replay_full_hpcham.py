#!/usr/bin/env python3
"""replay-full of HT_Pert/code/lri_hpc_Hamitonian: recompute, with the shipped engines, the two window records that
the quoted numbers lean on most and that `replay` only reads, then redo the dependent numbers.

  full.topsum   analysis/identity_checks/challenge-num/topsum.py at every Lambda of top_a.jsonl (108 even cutoffs
                4..288; closed-form top-level eps^4 vacuum sums, numba): every field except the run time 'sec' within
                1e-12 relative of top_a.jsonl (bitwise on the production stack; prange reductions may reorder sums).
                Then the shipped fit.py on the regenerated file: the top-level shift limit (basis g, Lambda 24..96)
                within 1e-9 of the shipped fit_out.txt (0.0186909946), hence \\HTpWinCfourInf unchanged.
  full.ht5      the independent from-scratch engine analysis/eps5_window/challenge-num/ht5.py at Lambda 6..16 and
                runbig.py at 18..28 (Engine(L, 10, 11)), as the analysis ran them: every number of the four
                variants within 1e-11 absolute of ht5_out_6_8_10_12_14_16.json and big_18_20_22_24_26_28.json
                (float64 sparse algebra); dims equal. Then the engine agreement (iii) of a1.engine is recomputed from
                the regenerated outputs: max |Delta C5(ht5) - dC5_Dconn(dC_reconciled)| <= 3e-12.
Runs in <work>/full/ on copies of the scripts (they write into their working directory). Cost on symmetry defq
(Xeon Gold 6148, 8 threads): see public.mk. Exit 1 on any FAIL. Table to stdout and <work>/replay_full_lri_hpc_Hamitonian.txt.
usage: python3 public/replay_full_hpcham.py [--work .work] [--threads 8]"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', default=os.path.join(PKG, '.work'))
    ap.add_argument('--threads', type=int, default=8)
    a = ap.parse_args()
    W = os.path.abspath(os.path.join(a.work, 'full'))
    if os.path.exists(W):
        shutil.rmtree(W)
    os.makedirs(W)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
               OMP_NUM_THREADS='1', NUMBA_NUM_THREADS=str(a.threads))
    env.setdefault('NUMBA_CACHE_DIR', os.path.join(os.path.abspath(a.work), 'numba_cache'))
    rows = []

    def run(cmd, wd):
        r = subprocess.run([sys.executable] + cmd, cwd=wd, env=env, capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(f'{cmd} failed: {r.stderr[-800:]}')
        return r.stdout

    # ---------------------------------------------------------------- topsum + fit
    t0 = time.time()
    cn = os.path.join(AN, 'identity_checks', 'challenge-num')
    wd = os.path.join(W, 'topsum')
    os.makedirs(wd)
    for f in ('topsum.py', 'fit.py'):
        shutil.copy2(os.path.join(cn, f), wd)
    ref = [json.loads(ln) for ln in open(os.path.join(cn, 'top_a.jsonl'))]
    try:
        out = run(['topsum.py'] + [str(r['L']) for r in ref], wd)
        new = [json.loads(ln) for ln in out.split('\n') if ln.startswith('{')]
        nd = {r['L']: r for r in new}
        worst, bitwise, bad = 0.0, True, []
        for r in ref:
            for k, v in r.items():
                if k in ('sec', 'L'):
                    continue
                x = nd.get(r['L'], {}).get(k)
                if x is None:
                    bad.append(f"{r['L']} {k}")
                    continue
                d = abs(x - v) / max(abs(v), 1e-300)
                worst, bitwise = max(worst, d), bitwise and x == v
                if d > 1e-12:
                    bad.append(f"{r['L']} {k}")
        with open(os.path.join(wd, 'top_a.jsonl'), 'w') as fh:
            for r in new:
                fh.write(json.dumps(r) + '\n')
        fo = run(['fit.py', 'top_a.jsonl'], wd)
        pat = r'lo= 24 hi= 96 n= 37 g \{[^}]*\}\s+c0=([0-9.]+)'
        s_new = float(re.search(pat, fo).group(1))
        s_ref = float(re.search(pat, open(os.path.join(cn, 'fit_out.txt')).read()).group(1))
        ok = not bad and len(new) == len(ref) and abs(s_new - s_ref) <= 1e-9
        rows.append(('full.topsum', 'PASS' if ok else 'FAIL',
                     f'{len(new)} cutoffs {ref[0]["L"]}..{ref[-1]["L"]} regenerated: max rel diff vs top_a.jsonl '
                     f'{worst:.1e} (<= 1e-12; bitwise {bitwise}){"; bad " + str(bad[:4]) if bad else ""}; fit.py on the '
                     f'regenerated file: shift4 limit (basis g, 24..96) {s_new:.10f} vs shipped {s_ref:.10f} '
                     f'({time.time() - t0:.0f} s)'))
    except Exception as e:  # noqa: BLE001
        rows.append(('full.topsum', 'FAIL', str(e)[-600:]))
    print(f'replay-full  {rows[-1][0]:12s} {rows[-1][1]}  {rows[-1][2]}', flush=True)

    # ---------------------------------------------------------------- ht5 + runbig, then F1 (iii)
    t0 = time.time()
    e5 = os.path.join(AN, 'eps5_window', 'challenge-num')
    wd = os.path.join(W, 'ht5')
    os.makedirs(wd)
    for f in ('ht5.py', 'runbig.py'):
        shutil.copy2(os.path.join(e5, f), wd)
    try:
        run(['ht5.py', '6', '8', '10', '12', '14', '16'], wd)
        run(['runbig.py', '18', '20', '22', '24', '26', '28'], wd)
        worst, n, bad = 0.0, 0, []
        regen = {}
        for name in ('ht5_out_6_8_10_12_14_16.json', 'big_18_20_22_24_26_28.json'):
            new = json.load(open(os.path.join(wd, name)))
            ref = json.load(open(os.path.join(e5, name)))
            regen.update(new)
            for L in ref:
                if list(new[L]['dims']) != list(ref[L]['dims']):
                    bad.append(f'{L} dims')
                for var in ('raw', 'g2D3W', 'Dconn', 'Dfull'):
                    A, B = dict(leaves(new[L][var])), dict(leaves(ref[L][var]))
                    if A.keys() != B.keys():
                        bad.append(f'{L} {var} keys')
                        continue
                    for k in B:
                        n += 1
                        worst = max(worst, abs(A[k] - B[k]))
        rec = {int(k): v for k, v in json.load(open(os.path.join(AN, 'eps5_window', 'reconcile',
                                                                 'dC_reconciled.json'))).items()}
        iii = max(abs(v['Dconn']['C'][5] - v['raw']['C'][5] - rec[int(L)]['dC5_Dconn']) for L, v in regen.items())
        ok = not bad and worst <= 1e-11 and iii <= 3e-12
        rows.append(('full.ht5', 'PASS' if ok else 'FAIL',
                     f'ht5.py 6..16 and runbig.py 18..28 regenerated: {n} numbers, max |diff| {worst:.1e} (<= 1e-11)'
                     f'{"; bad " + str(bad[:4]) if bad else ""}; engine agreement (iii) from the regenerated outputs: '
                     f'max |Delta C5 - dC5_Dconn| at Lambda 6..28 = {iii:.2e} (<= 3e-12) ({time.time() - t0:.0f} s)'))
    except Exception as e:  # noqa: BLE001
        rows.append(('full.ht5', 'FAIL', str(e)[-600:]))
    print(f'replay-full  {rows[-1][0]:12s} {rows[-1][1]}  {rows[-1][2]}', flush=True)
    nf = sum(r[1] == 'FAIL' for r in rows)
    summ = f'# replay-full lri_hpc_Hamitonian: {len(rows) - nf} PASS, {nf} FAIL'
    print(summ)
    open(os.path.join(os.path.abspath(a.work), 'replay_full_lri_hpc_Hamitonian.txt'), 'w').write(
        '\n'.join(f'{r:12s} {v} {d}' for r, v, d in rows) + '\n' + summ + '\n')
    sys.exit(1 if nf else 0)


if __name__ == '__main__':
    main()
