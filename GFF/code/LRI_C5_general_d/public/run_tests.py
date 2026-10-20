#!/usr/bin/env python3
"""`make -f public.mk test`: the package's own quick checks, run unchanged, with a PASS/FAIL table (added for the release).

The package ships no test suite; these are its own unit and consistency scripts, each run from its folder with its
default precision, and judged by the numbers it prints (thresholds well above the printed values, well below anything
a broken formula would give). About 90 s on one core (Python 3.10.11, mpmath 1.2.1, sympy 1.11.1, macOS, 2026-10-13).
Nothing is written into the package (PYTHONDONTWRITEBYTECODE=1; z_jets.py writes to public/out/).

  foundation/check_topG.py          product-form top-mode theorem at four mixed points (30 digits)
  L/test_jet_sums.py, test_jet_cauchy.py   jet arithmetic of the five-Horn engine against plain sums and Cauchy circles
  L/check_closed_coeffs.py          printed closed-form coefficients of the L_d formula vs sympy, 11 dimensions
  L/sym_L.py, L/sym_functional.py   sympy derivation of the residue functional and the three-node formula
  L/L_general.py 2 20, 1.5 20       P4 and L_d at 20 digits vs the closed form (d = 2) and the spectral reference (d = 1.5)
  Z/check_weights.py                polygamma weights of the jet series vs numerical differentiation
  Z/z_jets.py ... 30 1.5,2 2        Z_d by exact jets at 30 digits vs the 90-digit record Z/results/Z_values.json
  specialize/sym_taylor.py, sym_twonode4.py   pole-node weights and the Gauss-type two-node form (sympy)
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import mpmath as mp

PKG = Path(__file__).resolve().parents[1]
OUT = PKG / 'public' / 'out'
PY = sys.executable
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', SLURM_CPUS_PER_TASK=os.environ.get('SLURM_CPUS_PER_TASK', '2'))
F = r'([-+]?\d+(?:\.\d+)?(?:e[-+]?\d+)?)'


def nums_after(text, word):
    return [float(x) for x in re.findall(word + r'\s*' + F, text)]


def lt(xs, tol):
    return bool(xs) and max(abs(x) for x in xs) < tol, 'max %.3g (< %g, %d values)' % (max(map(abs, xs)) if xs else -1, tol, len(xs))


def t_topG(o):
    big, ctrl, r = [], [], None
    for line in o.splitlines():
        m = re.match(r'\s+[A-D] d=\S+ r=(\d)', line)
        if m:
            r = int(m.group(1))
        c = re.search(r'\(\s*(\d+),\s*(\d+)\)', line)
        if r and c and c.group(1) == '110':
            md = {int(a): float(b) for a, b in re.findall(r'([+-]\d):(\S+)', line)}
            (ctrl if 'control' in line else big).extend([md[-(r - 1)], md[r - 1]])
    ok = big and ctrl and max(big) < 1e-14 and min(ctrl) > 1e-11
    return ok, 'top modes <= %.1e, controls >= %.1e' % (max(big), min(ctrl))


def t_Lgen(d, ref):
    def f(o):
        m = re.search(r'P4 = (\S+)\s+L_d = (\S+)', o)
        P4, L = mp.mpf(m.group(1)), mp.mpf(m.group(2))
        e = max(abs(P4 - ref[0]) / abs(ref[0]), abs(L - ref[1]) / abs(ref[1]))
        return e < 1e-17, 'P4 %s, L %s; rel dev %.1e (< 1e-17)' % (mp.nstr(P4, 12), mp.nstr(L, 12), float(e))
    return f


def refs():
    mp.mp.dps = 40
    g4 = mp.gamma(mp.mpf(1) / 4) ** 4
    Bm = g4 * mp.hyper([0.25, 0.25, 0.5, 0.5], [0.75, 0.75, 1], 1)
    Bp = 64 * mp.pi ** 4 / g4 * mp.hyper([0.75, 0.75, 0.5, 0.5], [1.25, 1.25, 1], 1)
    P42 = (Bm ** 2 - Bp ** 2) / (4 * mp.pi ** 3)
    r15 = json.loads((PKG / 'references/reference_values.json').read_text())['values']['d=1.5']
    zv = json.loads((PKG / 'Z/results/Z_values.json').read_text())['values']
    return (P42, -2 * mp.log(2) * P42), (mp.mpf(r15['P4']['value']), mp.mpf(r15['L']['value'])), zv


def t_zjets(zv):
    def f(o):
        got = dict(re.findall(r'd=(\S+)\s+W=.*?Z=(\S+)', o))
        e = max(abs(mp.mpf(got[d]) - mp.re(mp.mpmathify(zv[d]['Z']))) / abs(mp.re(mp.mpmathify(zv[d]['Z']))) for d in ('1.5', '2'))
        return e < 1e-28, 'Z(1.5), Z(2) vs Z_values.json: rel dev %.1e (< 1e-28)' % float(e)
    return f


def contains(*subs):
    return lambda o: (all(s in o for s in subs), 'found: ' + '; '.join(subs)[:70])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (L2, L15, zv) = refs()
    tests = [
        ('check_topG', 'foundation', ['check_topG.py'], t_topG),
        ('test_jet_sums', 'L', ['test_jet_sums.py'], lambda o: lt(nums_after(o, r'(?:err|diff)'), 1e-30)),
        ('test_jet_cauchy', 'L', ['test_jet_cauchy.py'], lambda o: lt(nums_after(o, 'rel diff'), 1e-30)),
        ('check_closed_coeffs', 'L', ['check_closed_coeffs.py'], lambda o: lt(nums_after(o, 'worst'), 1e-12)),
        ('sym_L', 'L', ['sym_L.py'], lambda o: lt(nums_after(o, 'diff'), 1e-20)),
        ('sym_functional', 'L', ['sym_functional.py'],
         contains('foundation W4 explicit check: 0', 'three-node formula check: 0', 'B_{4,3} = -20*pi**3/sin(pi*sigma)**3')),
        ('L_general d=2', 'L', ['L_general.py', '2', '20'], t_Lgen('2', L2)),
        ('L_general d=1.5', 'L', ['L_general.py', '1.5', '20'], t_Lgen('1.5', L15)),
        ('check_weights', 'Z', ['check_weights.py'], lambda o: lt([float(x) for x in re.findall(F + r'\s*$', o, re.M)], 1e-25)),
        ('z_jets 30 digits', 'Z', ['z_jets.py', str(OUT / 'test_zjets30.json'), '30', '1.5,2', '2'], t_zjets(zv)),
        ('sym_taylor', 'specialize', ['sym_taylor.py'], contains('G_r = 2*pi*(-3*lambda1/tan(theta) + pi)',
                                                                'omega_2 = cos(theta)/(pi**3*sin(theta)**5)')),
        ('sym_twonode4', 'specialize', ['sym_twonode4.py'], contains('z: 3*c/(2*c**2 + 1)')),
    ]
    rows, t_all = [], time.time()
    for name, cwd, cmd, judge in tests:
        t0 = time.time()
        p = subprocess.run([PY] + cmd, cwd=PKG / cwd, env=ENV, capture_output=True, text=True, timeout=600)
        if p.returncode:
            ok, msg = False, 'rc %d: %s' % (p.returncode, (p.stderr.strip().splitlines() or [''])[-1][:80])
        else:
            try:
                ok, msg = judge(p.stdout)
            except Exception as exc:  # a changed output format is a failure, not a crash
                ok, msg = False, 'could not read the output: %r' % exc
        rows.append(dict(test=name, cmd=' '.join([cwd + '/'] + cmd), status='PASS' if ok else 'FAIL', detail=msg,
                         seconds=round(time.time() - t0, 1)))
        print('%-20s %-5s %6.1f s  %s' % (name, rows[-1]['status'], rows[-1]['seconds'], msg), flush=True)
    nf = sum(r['status'] == 'FAIL' for r in rows)
    (OUT / 'test.json').write_text(json.dumps(dict(python=sys.version.split()[0], mpmath=mp.__version__, rows=rows), indent=1) + '\n')
    print('\ntest: %d PASS, %d FAIL in %.0f s (python %s, mpmath %s)' % (len(rows) - nf, nf, time.time() - t_all,
                                                                       sys.version.split()[0], mp.__version__))
    sys.exit(1 if nf else 0)


if __name__ == '__main__':
    main()
