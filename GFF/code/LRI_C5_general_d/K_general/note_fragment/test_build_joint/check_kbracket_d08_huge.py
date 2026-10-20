#!/usr/bin/env python3
"""Companion of check_kbracket_d08.py (repair round 1 of the joint-review fixes; first version kept as
check_kbracket_d08_huge_r0.py/.log).  The literal gs:Kseries bracket and gc:Kcancelled at the very large radial
indices n reached by the log-map n-tail of refcheck/routeB_residue.py, through that code's own init, g_at and
tail parameters (read-only import; routeB_residue.py is not changed).

  1. Production values: K from the literal and the cancelled bracket in every diagonal refcheck/runs/B_d*_dps*_L20.json.
  2. Reach of the n-tail in inner_sum: x = N + exp(w - e^{-w}) up to w = whi = log(|l|+N+1) + 1.15 Dd/p + 6,
     Dd = (dps+8) log 10, p = slow_n_exponent(); production used N = 8 (default Nn).  The reach is about
     10^394 at d = 0.8 (p = 0.2) and 10^93 at d = 1.25 (p = 0.875) at dps 60, not 10^100 for both.
  3. n*literal and n*cancelled up to that reach.  The trapezoid weight of a node is about hw*n, so n*g(n) is the
     size of a node's contribution.  The individual terms of the bracket decay like n^{-d} (T^2, S^2 ~ n^{-4q}), so at
     d < 1 a fixed relative error makes n*literal grow like n^{1-d}.
  4. The cause: init() fixes the constants (M, psi values, Rinf, ...) at dps+20 digits, and the literal bracket loses
     about one digit per decade of n; with the constants at higher precision the two brackets agree again at 1e100.
  5. (repair round 2) The same as 3 at dps 40, the precision of the other stored d = 0.8 failure (K = 70.3): the
     constants are then at 60 digits, the literal bracket has no correct digit from about n = 1e60, and n*literal at
     the 40-digit reach (about 1e279.5) is O(0.04), with the sign opposite to the dps-60 case; d = 1.25 for contrast.
     Sections 1-4 are unchanged from repair round 1 (copy prerepair2/check_kbracket_d08_huge_r1.py and its log).
  6. (repair round 2) max of n*|literal - cancelled| at d = 1.25 (l = 0) over the corrupted range, from n = 10^(dps+20)
     (no correct digit left) to the reach, on a grid of 0.25 decades, at dps 60 and 40; and the same over the whole
     range from n = 10, where the error is the rounding error of the working precision; and the small-n part
     (n = 10 to 1e25) for the spins l = 0, 1, 2, 5, 20, 100.
"""
import os, sys, json
import mpmath as mp
RC = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'refcheck'))
sys.path.insert(0, RC)
sys.argv = ['x']
import routeB_residue as B

mp.mp.dps = 80
print('1. production route-B runs (refcheck/runs): K from the literal bracket vs the cancelled bracket')
mb = json.load(open(os.path.join(RC, '..', 'position_space', 'K_d_values_mb_D100.json')))['values']
import glob, re
runs = []
for f in glob.glob(os.path.join(RC, 'runs', 'B_d*_dps*_L20.json')):
    m = re.fullmatch(r'B_d([0-9.]+)_dps(\d+)_L20\.json', os.path.basename(f))   # diagonal runs only (no _b..._)
    if m:
        runs.append((float(m.group(1)), int(m.group(2)), m.group(1), f))
for _, dps, d, f in sorted(runs):
    F = json.load(open(f))['final']
    K, Kc, KM = mp.mpf(F['K']), mp.mpf(F['K_cancelled']), mp.mpf(mb[d]['K'])
    print('  d=%-4s dps %d  K(literal)=%s  K(cancelled)=%s  (lit-canc)/canc=%s  (canc-MB)/MB=%s' % (
        d, dps, mp.nstr(K, 12), mp.nstr(Kc, 12),
        'identical stored strings' if F['K'] == F['K_cancelled'] else mp.nstr((K - Kc) / Kc, 3), mp.nstr((Kc - KM) / KM, 3)))

print('2. reach of the n-tail of inner_sum (l = 0, N = 8 as in production)')
reach = {}
for d in ('0.8', '1', '1.25', '1.5'):
    for dps in (40, 60):
        B.init(d, dps)
        N = 8
        hw = mp.mpf(1) / 12 if dps <= 45 else mp.mpf(1) / 16
        Dd = (dps + 8) * mp.log(10)
        p = B.slow_n_exponent()
        whi = mp.log(0 + N + 1) + Dd * mp.mpf('1.15') / p + 6
        wmax = mp.floor(whi / hw) * hw
        nmax = N + mp.exp(wmax - mp.exp(-wmax))
        reach[(d, dps)] = nmax
        print('  d=%-4s dps %d  p=%s  whi=%s  last node n=%s (log10 n = %s)' % (
            d, dps, mp.nstr(p, 4), mp.nstr(whi, 6), mp.nstr(nmax, 4), mp.nstr(mp.log10(nmax), 5)))

print('3. n*literal and n*cancelled up to the reach (dps 60, l = 0 and 5)')
for d in ('0.8', '1.25'):
    B.init(d, 60)
    top = int(mp.floor(mp.log10(reach[(d, 60)])))
    exps = sorted(set([20, 40, 60, 80, 100] + [e for e in (150, 200, 300, 390) if e <= top] + [top]))
    print('  d =', d, ' tail exponent p =', mp.nstr(B.slow_n_exponent(), 4), ' last node 10^%s' % mp.nstr(mp.log10(reach[(d, 60)]), 5))
    for e in exps:
        for l in (0, 5):
            n = mp.mpf(10) ** e
            v = B.g_at(mp.mpf(l), n)
            print('    l=%d n=1e%-3d n*literal=%-12s n*cancelled=%-12s rel.diff=%s' % (
                l, e, mp.nstr(n * v[4], 4), mp.nstr(n * v[5], 4), mp.nstr(abs(v[4] - v[5]) / abs(v[5]), 3)))

print('4. cause: constants of init() at dps+20 digits.  Same points with init at dps 500 (constants at 520 digits)')
for d in ('0.8', '1.25'):
    B.init(d, 500)
    for e in (80, 100, 390):
        v = B.g_at(mp.mpf(0), mp.mpf(10) ** e)
        print('  d=%-4s l=0 n=1e%d  rel.diff literal-cancelled = %s' % (d, e, mp.nstr(abs(v[4] - v[5]) / abs(v[5]), 3)))

print('5. n*literal and n*cancelled at dps 40 up to the 40-digit reach (l = 0 and 5)')
for d in ('0.8', '1.25'):
    B.init(d, 40)
    top = int(mp.floor(mp.log10(reach[(d, 40)])))
    exps = sorted(set([e for e in (20, 40, 50, 60, 80, 100, 150, 200, 250) if e <= top] + [top]))
    print('  d =', d, ' tail exponent p =', mp.nstr(B.slow_n_exponent(), 4), ' last node 10^%s' % mp.nstr(mp.log10(reach[(d, 40)]), 5))
    for e in exps:
        for l in (0, 5):
            n = mp.mpf(10) ** e
            v = B.g_at(mp.mpf(l), n)
            print('    l=%d n=1e%-3d n*literal=%-12s n*cancelled=%-12s rel.diff=%s' % (
                l, e, mp.nstr(n * v[4], 4), mp.nstr(n * v[5], 4), mp.nstr(abs(v[4] - v[5]) / abs(v[5]), 3)))
    n = reach[(d, 40)]
    v = B.g_at(mp.mpf(0), n)
    print('    l=0 at the last node n=%s: n*literal=%s n*cancelled=%s' % (mp.nstr(n, 4), mp.nstr(n * v[4], 4), mp.nstr(n * v[5], 4)))

print('6. d = 1.25, l = 0: max of n*|literal - cancelled| on a 0.25-decade grid')
for dps in (60, 40):
    B.init('1.25', dps)
    top = mp.log10(reach[('1.25', dps)])
    for lo in (1, dps + 20):
        worst, at = mp.mpf(0), None
        e = mp.mpf(lo)
        while e <= top:
            n = mp.mpf(10) ** e
            v = B.g_at(mp.mpf(0), n)
            err = n * abs(v[4] - v[5])
            if err > worst:
                worst, at = err, e
            e += mp.mpf('0.25')
        print('  dps %d  n from 1e%d to 1e%s: max n*|lit-canc| = %s at n = 1e%s' % (
            dps, lo, mp.nstr(top, 5), mp.nstr(worst, 3), mp.nstr(at, 4)))
for dps in (60, 40):
    B.init('1.25', dps)
    worst, at = mp.mpf(0), None
    for l in (0, 1, 2, 5, 20, 100):
        e = mp.mpf(1)
        while e <= 25:
            n = mp.mpf(10) ** e
            v = B.g_at(mp.mpf(l), n)
            err = n * abs(v[4] - v[5])
            if err > worst:
                worst, at = err, (l, e)
            e += mp.mpf('0.25')
    print('  dps %d  spins l = 0, 1, 2, 5, 20, 100, n from 1e1 to 1e25: max n*|lit-canc| = %s at l = %d, n = 1e%s' % (
        dps, mp.nstr(worst, 3), at[0], mp.nstr(at[1], 4)))
