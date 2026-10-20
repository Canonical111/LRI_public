"""M1 gate: C3 from the exact s=1 (Bethe-ansatz) flow plus the one-bubble delta-flow, no kink integrals.
Also prints C4, C5 as functions of the still-unknown two-bubble coefficients (blind targets for M2)."""
import mpmath as mp, sympy as sp, subprocess, re
from mscheme_invariants import C_list, fsym
from one_bubble import taylor_coeffs
mp.mp.dps = 50
ob = taylor_coeffs(N=4, nmax=4)
# Bethe-ansatz delta=0 coefficients: reuse ba_numeric (60 digits)
out = subprocess.run(['python3', '-c', 'exec(open("ba_numeric.py").read())'], capture_output=True, text=True,
                     executable=__import__('sys').executable).stdout
ba = {}
for line in out.splitlines():
    m_ = re.match(r'\((\d+), (\d+)\) (\S+)', line)
    if m_: ba[(int(m_.group(1)), int(m_.group(2)))] = mp.mpf(m_.group(3))
vals = {fsym(1, 0, 0): mp.mpf(1)}
for (m, n), v in ba.items():
    vals[fsym(m, n, 0)] = v
for (n, k), v in ob.items():
    if k >= 1: vals[fsym(0, n, k)] = v
Cs = C_list(3)
z2, z3, z4 = mp.zeta(2), mp.zeta(3), mp.zeta(4)
print('BA f_1_1_0 - 4 zeta(2) =', mp.nstr(vals[fsym(1, 1, 0)] - 4*z2, 5))
def num(expr):
    """Substitute the raw numerical coefficients (no recognition or simplification)."""
    e = expr.subs({sym: sp.Float(mp.nstr(vals[sym], 48), 48) for sym in expr.free_symbols if sym in vals})
    return sp.expand(e)
import sys
C3 = num(Cs[2])
if C3.free_symbols:
    print('FAIL: C3 has unresolved inputs', C3.free_symbols); sys.exit(2)
C3v = mp.mpf(str(sp.N(C3, 48)))
C3_exact = mp.mpf(39)/16 + 2*z2
diff = C3v - C3_exact
print('C3 (pipeline)  =', mp.nstr(C3v, 40))
print('C3 (compendium)=', mp.nstr(C3_exact, 40))
print('difference     =', mp.nstr(diff, 5))
TOL = mp.mpf('1e-30')
if not mp.isfinite(C3v) or abs(diff) > TOL:
    print('FAIL: |C3 - exact| > %s' % mp.nstr(TOL, 2)); sys.exit(1)
print('PASS: |C3 - exact| <= %s' % mp.nstr(TOL, 2))
C4 = num(Cs[3]); print('\nC4 in terms of unknowns:', sp.N(C4, 20))
C5 = num(Cs[4]); print('C5 unknown symbols:', sorted(map(str, C5.free_symbols)))
