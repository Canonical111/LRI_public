#!/usr/bin/env python3
"""`make -f public.mk replay-full` (R1): recompute the records behind note Section 20 with the package's own scripts.

About 1 core-hour; on a node with 16 or more cores about 10 minutes (the longest single task, one dimension of
dump_samples.py at 60 digits, took 183 s on symmetry). Run on a cluster node, not a laptop (see CLUSTER_CHECKS.md).
Everything runs in a copy of the package (public/out/work_full/LRI_C5_general_d; the scripts write their records into
their own folders), next to a link to the sibling GFF/code/LRI_C5_d3 (Z/compare_refs.py reads its 250-digit Z3).
Every recomputed record is written under its original name in the copy, so the re-analyses at the end read the new
values, and is compared with the shipped record:

  job            script (as it ran in production; arguments from the job logs)                 compared with
  samples        review/joint/numerics-end-to-end/dump_samples.py ROOT 60                      samples_dps60.json
  e2e            e2e.py samples_dps60.json (on the recomputed samples)                         e2e_report.json (bytes)
  c5_assembly    specialize/c5_assembly.py 50                                                   results/c5_assembly_dps50.json
  taylor         specialize/check_taylor.py 30                                                  results/check_taylor_dps30.log
  gamma_c0       specialize/gamma_c0.py 80        (PSLQ, optional: --pslq)                      results/gamma_c0_dps80.json
  pslq_L         specialize/pslq_L.py 110         (PSLQ, optional: --pslq)                      results/pslq_L_dps110.json
  L_val50        L/run_validation.py results/val50.json 50 0.8,1,1.25,1.5,2,2.5,2.75,3          L/results/val50.json
  L_val70        L/run_validation.py results/val70.json 70 1,2,3,1.5,2.5                        L/results/val70.json
  Z_jets60/60x/90  Z/z_jets.py results/zj{60,60x,90}.json {60,60,90} <dims> 2                   Z/results/zj*.json
  Z_cauchy60/60x Z/z_cauchy.py results/zc{60,60x}.json 60 64 <dims>                             Z/results/zc*.json
  Z_refs         Z/compare_refs.py results/zj90.json results/zj60.json results/zc60.json results/zc60x.json
                 results/zj60x.json             (values; deviations only shrink, see below)    Z/results/compare_refs.log
  Z_formulas     Z/check_formulas.py                                                            Z/results/check_formulas.log

Comparison: JSON records field by field with run times, host data and paths ignored (keys seconds, sec, time, wall,
cpu, root), by the precision-aware rule stated above cmp_json() below: value fields agree to dps-10 digits of the size
of their record entry (identical strings with the gmpy2 backend the records were written with; the pure-Python backend
moves the last guard digits), c5_assembly's deviation fields stay below the bounds note Section 20.7 prints, and the
PSLQ probes keep their conclusion. Text logs: line for line after removing timing tokens. Exception: Z/results/compare_refs.log was written against the
45-digit reference strings that references/reference_values.json held before it was rebuilt with 50 digits (2026-10-03
01:21); its Z values must be identical, its deviations from the references may only shrink (<= 5e-50 at the
non-integer dimensions for the exact-jet engine, as note Section 20.7 states for the current file). The same rebuild
explains why the dev_*_ref fields of c5_assembly_dps50.json change (from up to 4.2e-45 to at most 3.7e-50).
Output: table on stdout and public/out/replay_full.json; exit 1 on any FAIL. Workers: SLURM_CPUS_PER_TASK (default: all cores).
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import mpmath as mp

PKG = Path(__file__).resolve().parents[1]
E2E = 'review/joint/numerics-end-to-end'
IGNORE = {'seconds', 'sec', 'time', 'wall', 'cpu', 'root'}
NUM = re.compile(r'^\(?[-+]?\d[\d.]*(?:e[-+]?\d+)?(?:\s*[-+]\s*[\d.]+(?:e[-+]?\d+)?j)?\)?$')


def flat(x, p=''):
    if isinstance(x, dict):
        for k, v in x.items():
            if k not in IGNORE:
                yield from flat(v, '%s.%s' % (p, k) if p else k)
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from flat(v, '%s[%d]' % (p, i))
    else:
        yield p, x


# Precision-aware comparison (after the first cluster run, 2026-10-13: symmetry, Python 3.12.9, mpmath 1.3.0 without
# gmpy2). The records were written with the gmpy2 backend; the pure-Python backend changes the last guard digits of the
# Cauchy-circle and jet evaluations (verified on macOS: gmpy2 with mpmath 1.2.1 or 1.3.0 and 4 or 64 workers reproduce
# Z/results/zc60x.json string for string; the pure-Python backend, with Python 3.10 or 3.12, moves 23 of its 31 fields at
# 1e-53..1e-61 absolute). Fields that are tiny because they vanish or nearly vanish (the M1 block at the resonant
# d = 4/3, about 1e-44; dW, which must vanish) then differ by a large RELATIVE amount at the same absolute level. Rule:
#   value fields   identical strings, or |new - shipped| <= 10^-(dps-10) * max(|shipped|, scale), where scale is the
#                  largest |value| in the same record entry (one dimension, one key): agreement to dps-10 digits of
#                  the entry's own size; a field printed with fewer digits than dps (c5_assembly prints 30) may move
#                  only in its last digit (relative 10^-(digits-2));
#   deviation fields (dev_*, *_vs_*, relerr) of specialize/c5_assembly_dps50.json: at most the bound the note prints
#                  (Section 20.7: compact forms <= 2.1e-48, reduced block <= 1.2e-48; references: d = 1, 2 <= 4e-50, d = 3
#                  <= 6e-34 (block) and 1e-33 (single masters, 33-digit references), non-integer d <= 5e-50). The shipped
#                  dev_*_ref at non-integer d were written against the 45-digit reference strings that
#                  references/reference_values.json held before 2026-10-03 01:21 (record: up to 4.2e-45); recomputed
#                  against the current 50-digit file they are <= 2.6e-50 (verified on macOS at d = 4/5);
#   PSLQ outputs   (gamma_c0, pslq_L): the integer relations of a negative search are not reproducible digit for digit;
#                  the conclusion is checked instead (no relation with max coefficient below 1e11, resp. 3e3 with
#                  differing relations at the two precisions), and the input values by the value rule;
#   run times, host data and paths are ignored.
DEV_BOUND = {'dev_P4_compact': '2.1e-48', 'dev_L_compact': '2.1e-48', 'dev_Z_Qform': '2.1e-48', 'dev_Q_c0form': '2.1e-48',
             'dev_Bred_vs_B': '1.2e-48'}


def _num(x):
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return mp.mpf(x)
    if isinstance(x, str) and NUM.match(x.replace(' ', '')):
        return mp.mpmathify(x.replace(' ', ''))
    return None


def _ndig(x):
    """significant digits of the first number in a printed field"""
    m = re.search(r'\d[\d.]*', str(x).replace(' ', ''))
    return len(m.group(0).replace('.', '').lstrip('0')) if m else 0


def _group(k):
    parts = k.split('.')
    return '.'.join(parts[:2]) if parts[0] in ('results', 'values') else parts[0]


def _dev_bound(k):
    """bound for a deviation field of c5_assembly_dps50.json (key '<d>.<field>')"""
    d, f = k.split('.', 1)
    if f in DEV_BOUND:
        return mp.mpf(DEV_BOUND[f])
    if f.startswith('dev_') and f.endswith('_ref'):
        if d in ('1', '2'):
            return mp.mpf('4e-50')
        if d == '3':
            return mp.mpf('6e-34') if f == 'dev_B_ref' else mp.mpf('1e-33')
        return mp.mpf('5e-50')
    return None


def cmp_json(new, old, dps, kind=''):
    A, B = dict(flat(json.loads(Path(new).read_text()))), dict(flat(json.loads(Path(old).read_text())))
    if set(A) != set(B):
        return False, 'keys differ: %s' % sorted(set(A) ^ set(B))[:4]
    mp.mp.dps = dps + 20
    scale = {}
    for k, b in B.items():
        v = _num(b)
        if v is not None and not k.split('.')[-1].startswith('dev_'):
            scale[_group(k)] = max(scale.get(_group(k), mp.mpf(0)), abs(v))
    tol = mp.mpf(10) ** (-(dps - 10))
    bad, inexact, worst, devs = [], 0, mp.mpf(0), []
    for k, b in B.items():
        a = A[k]
        leaf = re.sub(r'\[\d+\]', '', k.split('.')[-1])
        if kind == 'c5_assembly' and _dev_bound(k) is not None:
            x, bd = _num(a), _dev_bound(k)
            devs.append((x, k))
            if x is None or x > bd:
                bad.append('%s = %s > %s' % (k, a, mp.nstr(bd, 2)))
            continue
        if kind == 'pslq' and (leaf.startswith('pslq') or 'maxcoeff' in leaf or leaf.startswith('residual')
                               or leaf.startswith('control')):
            continue                      # judged by the conclusion below
        if a == b:
            continue
        x, y = _num(a), _num(b)
        if x is None or y is None:
            bad.append(k)
            continue
        nd = _ndig(b)
        if nd < dps - 10 and y != 0:      # a field printed with far fewer digits: only its last digit may move
            ref, lim = abs(y), mp.mpf(10) ** (-(nd - 2))
        else:
            ref, lim = max(abs(y), scale.get(_group(k), mp.mpf(0))), tol
        r = abs(x - y) / ref if ref else abs(x - y)
        inexact += 1
        worst = max(worst, r)
        if r > lim:
            bad.append('%s (|diff| %s, entry scale %s)' % (k, mp.nstr(abs(x - y), 2), mp.nstr(ref, 3)))
    if kind == 'pslq':
        mc = [int(v) for k, v in A.items() if 'maxcoeff' in k and 'log_Q' not in k and 'log_R' not in k]
        if 'pslq_hi' in ' '.join(A):
            hi = {k.split('.')[0]: v for k, v in A.items() if k.endswith('pslq_hi')}
            lo = {k.split('.')[0]: v for k, v in A.items() if k.endswith('pslq_lo')}
            if not (min(mc) >= 3000 and all(hi[d] != lo[d] for d in hi)):
                bad.append('PSLQ conclusion changed: min max-coefficient %d, relations %s' % (
                    min(mc), 'differ' if all(hi[d] != lo[d] for d in hi) else 'agree'))
        elif min(mc) < 10 ** 11:
            bad.append('PSLQ conclusion changed: a relation with max coefficient %d < 1e11' % min(mc))
    if bad:
        return False, '%d fields outside the rule, e.g. %s' % (len(bad), bad[:2])
    msg = 'value fields identical' if not inexact else 'tol: %d value fields differ in the last digits (worst %s of the entry scale)' % (
        inexact, mp.nstr(worst, 2))
    if devs:
        x, k = max(devs, key=lambda t: t[0] / _dev_bound(t[1]))
        msg += '; deviations within the note bounds (closest: %s = %s)' % (k, mp.nstr(x, 3))
    if kind == 'pslq':
        msg += '; PSLQ conclusion unchanged'
    return True, msg


def clean_lines(s):
    return [re.sub(r'\s*\(\d+(\.\d+)?\s*s\)|\[\s*\d+(\.\d+)?\s*s\]', '', x).rstrip() for x in s.strip().splitlines()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='public/out')
    ap.add_argument('--pslq', action='store_true', help='also rerun the two PSLQ probes (several minutes more)')
    ap.add_argument('--only', default='', help='comma-separated job names')
    a = ap.parse_args()
    out = (PKG / a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    work = out / 'work_full'
    if work.exists():
        shutil.rmtree(work)
    dst = work / 'LRI_C5_general_d'
    skip = (PKG / 'public' / 'out').resolve()
    shutil.copytree(PKG, dst, ignore=lambda d, n: [x for x in n if (Path(d) / x).resolve() == skip or x == '__pycache__'])
    d3 = (PKG.parent / 'LRI_C5_d3').resolve()
    if d3.exists():
        os.symlink(d3, work / 'LRI_C5_d3')
    py = sys.executable
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1')
    env.setdefault('SLURM_CPUS_PER_TASK', str(os.cpu_count() or 4))
    D8 = '1,1.5,2,2.5,3,0.8,1.25,2.75'
    jobs = [  # name, folder, command, kind, shipped record (relative to the package), dps
        ('samples', E2E, ['dump_samples.py', str(dst), '60', 'samples_dps60.json'], 'json', E2E + '/samples_dps60.json', 60),
        ('e2e', E2E, ['e2e.py', 'samples_dps60.json'], 'bytes', E2E + '/e2e_report.json', 60),
        ('c5_assembly', 'specialize', ['c5_assembly.py', '50'], 'json', 'specialize/results/c5_assembly_dps50.json', 50),
        ('taylor', 'specialize', ['check_taylor.py', '30'], 'log', 'specialize/results/check_taylor_dps30.log', 30),
        ('gamma_c0', 'specialize', ['gamma_c0.py', '80'], 'json', 'specialize/results/gamma_c0_dps80.json', 80),
        ('pslq_L', 'specialize', ['pslq_L.py', '110'], 'json', 'specialize/results/pslq_L_dps110.json', 110),
        ('L_val50', 'L', ['run_validation.py', 'results/val50.json', '50', '0.8,1,1.25,1.5,2,2.5,2.75,3'], 'json', 'L/results/val50.json', 50),
        ('L_val70', 'L', ['run_validation.py', 'results/val70.json', '70', '1,2,3,1.5,2.5'], 'json', 'L/results/val70.json', 70),
        ('Z_jets60', 'Z', ['z_jets.py', 'results/zj60.json', '60', D8, '2'], 'json', 'Z/results/zj60.json', 60),
        ('Z_jets60x', 'Z', ['z_jets.py', 'results/zj60x.json', '60', '1.75,3.5,3.75,0.7', '2'], 'json', 'Z/results/zj60x.json', 60),
        ('Z_jets90', 'Z', ['z_jets.py', 'results/zj90.json', '90', D8 + ',1.75,3.5,3.75,0.7', '2'], 'json', 'Z/results/zj90.json', 90),
        ('Z_cauchy60', 'Z', ['z_cauchy.py', 'results/zc60.json', '60', '64', D8], 'json', 'Z/results/zc60.json', 60),
        ('Z_cauchy60x', 'Z', ['z_cauchy.py', 'results/zc60x.json', '60', '64', '4/3,8/3,1.75,3.5'], 'json', 'Z/results/zc60x.json', 60),
        ('Z_refs', 'Z', ['compare_refs.py', 'results/zj90.json', 'results/zj60.json', 'results/zc60.json', 'results/zc60x.json',
                         'results/zj60x.json'], 'log_refs', 'Z/results/compare_refs.log', 60),
        ('Z_formulas', 'Z', ['check_formulas.py'], 'log', 'Z/results/check_formulas.log', 90),
    ]
    only = set(a.only.split(',')) - {''}
    rows, t_all = [], time.time()
    for name, folder, cmd, kind, rec, dps in jobs:
        if (only and name not in only) or (name in ('gamma_c0', 'pslq_L') and not a.pslq and name not in only):
            continue
        t0 = time.time()
        p = subprocess.run([py] + cmd, cwd=dst / folder, env=env, capture_output=True, text=True)
        sec = time.time() - t0
        if p.returncode:
            ok, msg = False, 'rc %d: %s' % (p.returncode, (p.stderr.strip().splitlines() or [''])[-1][:90])
        elif kind == 'json':
            new = dst / rec
            ok, msg = cmp_json(new, PKG / rec, dps, 'c5_assembly' if name == 'c5_assembly' else
                               'pslq' if name in ('gamma_c0', 'pslq_L') else '')
        elif kind == 'bytes':
            ok = (dst / rec).read_bytes() == (PKG / rec).read_bytes()
            msg = 'identical' if ok else 'differs'
        elif kind == 'log_refs':
            # compare_refs.log was written against the 45-digit reference strings that references/reference_values.json
            # held until 2026-10-03 01:21; the shipped file has 50 digits. The values (Z, |dW/db|) must be identical; the
            # deviations from the references may only shrink, and must be <= 5e-50 at the five non-integer dimensions.
            (dst / rec).write_text(p.stdout)
            strip = lambda L: [re.sub(r'relerr\(\w+\)=\S+\s*', '', x) for x in L]
            new, old = clean_lines(p.stdout), clean_lines((PKG / rec).read_text())
            rel = lambda L: [[float(v) for v in re.findall(r'relerr\(\w+\)=(\S+)', x)] for x in L]
            hdr, nonint = '', []
            for x, r in zip(new, rel(new)):  # exact-jet sections only (the Cauchy engine is circle-limited, 1e-45)
                hdr = x if x.startswith('==') else hdr
                if r and 'engine jets' in hdr and re.match(r'd=(0\.8|1\.25|1\.5|2\.5|2\.75)\s', x):
                    nonint.append(max(r))
            shrink = all(not a or max(a) <= max(b) * 1.0001 for a, b in zip(rel(new), rel(old)))
            ok = strip(new) == strip(old) and shrink and max(nonint) <= 5e-50
            msg = ('values identical; deviations from the current references <= %.1e at the non-integer d (shipped log: '
                   'against the earlier 45-digit strings)' % max(nonint)) if ok else 'differs'
        else:
            (dst / rec).write_text(p.stdout)
            ok = clean_lines(p.stdout) == clean_lines((PKG / rec).read_text())
            msg = 'identical (timings removed)' if ok else 'differs'
        rows.append(dict(job=name, cmd='%s/ %s' % (folder, ' '.join(cmd)), record=rec, status='PASS' if ok else 'FAIL',
                         detail=msg, seconds=round(sec, 1)))
        print('%-12s %-5s %7.1f s  %-45s %s' % (name, rows[-1]['status'], sec, rec, msg), flush=True)
    nf = sum(r['status'] == 'FAIL' for r in rows)
    (out / 'replay_full.json').write_text(json.dumps(dict(python=sys.version.split()[0], mpmath=mp.__version__,
                                                          workers=env['SLURM_CPUS_PER_TASK'], rows=rows), indent=1) + '\n')
    print('\nreplay-full: %d PASS, %d FAIL in %.0f s (python %s, mpmath %s, %s workers)' % (
        len(rows) - nf, nf, time.time() - t_all, sys.version.split()[0], mp.__version__, env['SLURM_CPUS_PER_TASK']))
    sys.exit(1 if nf else 0)


if __name__ == '__main__':
    main()
