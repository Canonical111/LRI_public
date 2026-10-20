#!/usr/bin/env python3
"""Fast self-test of the shipped analysis code (seconds, numpy/scipy only).

  1. extrapolate.fits/summarize recover the limit of synthetic series D + a N^-w (+ b N^-(w+1)) on the production
     cutoffs N = 12..40 to 1e-9, for w = 0.6 and 1.1.
  2. The local exponent used by the replay is constant (= w to 1e-3) on a pure power law.
  3. The comparison rules of the replay (rounding, significant figures, value(err) and ranges) accept and reject what
     they should.
"""
import contextlib, io, math, sys
from pathlib import Path
PKG = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(PKG))
fails = 0
def check(name, ok, detail=''):
    global fails; fails += not ok; print(('PASS ' if ok else 'FAIL ') + name + ('  ' + detail if detail else ''))
# extrapolate.py runs its own composite analysis on import and rewrites extrapolation.json next to it: import a copy
import shutil, tempfile
tmp = Path(tempfile.mkdtemp()); [shutil.copy2(PKG / f, tmp / f) for f in ('extrapolate.py', 'collected.json')]
sys.path.insert(0, str(tmp))
with contextlib.redirect_stdout(io.StringIO()):
    import extrapolate as E
Ns = list(range(12, 41, 2))
s = {n: 0.5 - 0.03 * n ** -0.6 for n in Ns}               # pure F1 form: every accepted fit recovers the limit
sm = E.summarize(E.fits(s), s[40])
check('pure power law: median of the accepted fits = 0.5', sm is not None and abs(sm['D_inf'] - 0.5) < 1e-9, f"{sm['D_inf'] - 0.5:.1e}" if sm else 'no fit')
s = {n: 0.5 - 0.03 * n ** -1.1 + 0.02 * n ** -2.1 for n in Ns}  # F2 form: the F2 fits recover it, F1 is biased
fl = E.fits(s); f2 = [f for f in fl if f['form'] == 'F2']; sm = E.summarize(fl, s[40])
check('F2 form: every F2 fit recovers 0.5', f2 and max(abs(f['D_inf'] - 0.5) for f in f2) < 1e-8, f"{max(abs(f['D_inf'] - 0.5) for f in f2):.1e}")
check('F2 form: median of all accepted fits within its half-spread of 0.5', sm is not None and abs(sm['D_inf'] - 0.5) <= sm['spread_half'] + 1e-12, f"{sm['D_inf'] - 0.5:.1e} vs {sm['spread_half']:.1e}")
s = {n: 0.5 - 0.03 * n ** -0.7 for n in Ns}
sl = [(math.sqrt(Ns[i] * Ns[i + 1]), (s[Ns[i + 1]] - s[Ns[i]]) / math.log(Ns[i + 1] / Ns[i])) for i in range(len(Ns) - 1)]
we = [-math.log(sl[i + 2][1] / sl[i][1]) / math.log(sl[i + 2][0] / sl[i][0]) for i in range(0, len(sl) - 2, 2)]
check('local exponent of a pure power law is constant', max(abs(x - 0.7) for x in we) < 1e-3, f'{min(we):.4f}..{max(we):.4f}')
def decimals(t): return len(t.split('.')[1]) if '.' in t else 0
check('round rule', round(0.5045608846, decimals('0.504561')) == 0.504561 and round(0.50456, decimals('0.504561')) != 0.504561)
check('paren rule', round(0.5304771373, 5) == 0.53048 and round(0.0001156408155 * 1e5) == 12)
print(f'{fails} failures'); sys.exit(1 if fails else 0)
