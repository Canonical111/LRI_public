#!/usr/bin/env python3
"""replay-full of lri_c8_hpc: the two RECORDED rows of public/replay_c8.py recomputed with the solver.

  full.export    `python -m lri_c8 export` of the 21 + 21 shipped outputs (data/HT_1d/c8/c8_L52-92/accepted) into
                 <work>/replay_full_c8/exports/: the export and its provenance sidecar must equal the shipped
                 data/HT_1d/c8/exports/{raw,vacuum_only}_L52-92{,.provenance}.json byte for byte (the export
                 revalidates every output with the solver's acceptance checks; the sidecar records the outputs'
                 configuration, not the current machine)
  full.original  scripts/compare_original.py --cutoff 60: the original eighth-order solver (reference/original_code)
                 against the optimized engine, stored and ranked, both prescriptions, as in validation job 569659.
                 Required: the script passes (its own tolerance atol 1e-7 + rtol 2e-11, stored = ranked bitwise), and
                 C8_original, C8_new agree with the receipt's values within 1e-7 + 2e-11 |ref| (bitwise on the
                 production stack); the max |dC| is reported against the quoted 2.0e-8 (raw), 7.5e-9 (vacuum_only).
Validation job 569659 took 278 s for this step on 40 threads; here about 13 min with the default 4 threads, 9 GiB
peak (symmetry job 575032, Xeon Gold 6148; bitwise equal to the receipt there and in job 575003).
usage: python3 public/replay_full_c8.py [--data ../../data/HT_1d] [--work .work] [--threads 4]"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
SRC16 = 'dd811aca899543c4'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', type=Path, default=PKG / '..' / '..' / 'data' / 'HT_1d')
    ap.add_argument('--work', type=Path, default=PKG / '.work')
    ap.add_argument('--threads', type=int, default=4)
    a = ap.parse_args()
    D = a.data.resolve() / 'c8'
    W = a.work.resolve() / 'replay_full_c8'
    shutil.rmtree(W, ignore_errors=True)
    W.mkdir(parents=True)
    env = dict(os.environ, PYTHONPATH=str(PKG / 'src'), OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
               OMP_NUM_THREADS='1', NUMBA_NUM_THREADS=str(a.threads), PYTHONDONTWRITEBYTECODE='1',
               NUMBA_CACHE_DIR=os.environ.get('NUMBA_CACHE_DIR', str(a.work.resolve() / 'numba_cache' / 'full')))
    rows = []

    # full.export
    t = time.time()
    good, msgs = True, []
    for s in ('raw', 'vacuum_only'):
        ins = sorted(str(p) for p in (D / 'c8_L52-92' / 'accepted').glob(f'{s}_L*_d8.json'))
        out = W / 'exports' / f'{s}_L52-92.json'
        r = subprocess.run([sys.executable, '-m', 'lri_c8', 'export', '--inputs', *ins, '--output', str(out)],
                           cwd=W, env=env, capture_output=True, text=True)
        same = (r.returncode == 0 and len(ins) == 21
                and out.read_bytes() == (D / 'exports' / out.name).read_bytes()
                and out.with_suffix('.provenance.json').read_bytes()
                == (D / 'exports' / f'{s}_L52-92.provenance.json').read_bytes())
        good = good and same
        msgs.append(f'{s}: {len(ins)} outputs, export + sidecar byte-identical: {same}'
                    + ('' if r.returncode == 0 else f' (exit {r.returncode}: {r.stderr.strip()[-300:]})'))
    rows.append(('full.export', good, '; '.join(msgs) + f' ({time.time() - t:.0f} s)'))

    # full.original
    t = time.time()
    rec = json.loads((D / 'validation' / f'receipt_{SRC16}.json').read_text())['payload']
    want = {json.loads(ln)['scheme']: json.loads(ln) for ln in
            rec['steps']['original_comparison']['tail'].strip().split('\n')}
    out = W / 'compare_original.json'
    r = subprocess.run([sys.executable, str(PKG / 'scripts' / 'compare_original.py'), '--cutoff', '60',
                        '--threads', str(a.threads), '--output', str(out)], cwd=W, env=env, capture_output=True,
                       text=True)
    (W / 'compare_original.log').write_text(r.stdout + r.stderr)
    good, msgs = r.returncode == 0 and out.exists(), []
    if out.exists():
        got = {x['scheme']: x for x in json.loads(out.read_text())['records']}
        for s in ('raw', 'vacuum_only'):
            g, w = got[s], want[s]
            close = all(abs(g[k] - w[k]) <= 1e-7 + 2e-11 * abs(w[k]) for k in ('C8_original', 'C8_new'))
            bit = all(g[k] == w[k] for k in ('C8_original', 'C8_new'))
            good = good and close and g['within_tolerance'] and g['stored_equals_ranked']
            msgs.append(f'{s}: original {g["C8_original"]!r}, new {g["C8_new"]!r} (receipt {w["C8_original"]!r}, '
                        f'{w["C8_new"]!r}; bitwise {bit}), max |dC| {g["max_abs"]["C"]:.1e} (receipt '
                        f'{w["max_abs"]["C"]:.1e}), stored = ranked {g["stored_equals_ranked"]}, '
                        f'{g["seconds"]["original"]:.0f}/{g["seconds"]["stored"]:.0f}/{g["seconds"]["ranked"]:.0f} s')
    else:
        msgs.append(f'compare_original.py exit {r.returncode}: {r.stderr.strip()[-500:]}')
    rows.append(('full.original', good, '; '.join(msgs) + f' ({time.time() - t:.0f} s)'))

    lines = [f'{rid:13s}  {"PASS" if ok else "FAIL"}  {det}' for rid, ok, det in rows]
    nf = sum(not r[1] for r in rows)
    lines.append(f'# replay_full_c8: {len(rows) - nf} PASS, {nf} FAIL')
    text = '\n'.join(lines) + '\n'
    print(text, end='')
    (a.work.resolve() / 'replay_full_lri_c8_hpc.txt').write_text(text)
    sys.exit(1 if nf else 0)


if __name__ == '__main__':
    main()
