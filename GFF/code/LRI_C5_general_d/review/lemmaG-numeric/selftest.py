#!/usr/bin/env python3
"""Self-tests of lg_engine against closed forms (quick; run locally at low dps, on the cluster at full dps)."""
import sys
import time
import mpmath as mp
import lg_engine as E

dps = int(sys.argv[1]) if len(sys.argv) > 1 else 30
D = int(sys.argv[2]) if len(sys.argv) > 2 else dps - 4
hden = int(sys.argv[3]) if len(sys.argv) > 3 else 16
ngl = int(sys.argv[4]) if len(sys.argv) > 4 else 20
mp.mp.dps = dps
K = int(sys.argv[5]) if len(sys.argv) > 5 else 10
cfg = E.Cfg(K=K, D=D, hden=hden, ngl=ngl)
print('dps', dps, cfg, flush=True)

# 1. LogProd against direct Gamma ratios
pairs = [(mp.mpc('0.37', '0.2'), mp.mpc('1.17', '0.3')), (mp.mpf('-0.4'), mp.mpf('0.25'))]
lins = [(mp.mpf('0.65'), 1)]
LP = E.LogProd(pairs, lins, const=mp.mpf('0.3'))
worst = 0
for z in [mp.mpf(3), mp.mpc(7.5, 2), mp.mpf(40), mp.mpc(40, -13), mp.mpf(500), mp.mpc(2e3, 7), mp.mpf('1e9'), mp.mpc('1e40', '3')]:
    with mp.extradps(60):
        ref = mp.exp(mp.mpf('0.3')) * (z + mp.mpf('0.65'))
        for a, b in pairs:
            ref *= mp.gamma(z + a) / mp.gamma(z + b)
    v = LP.val(z)
    worst = max(worst, abs(v / ref - 1))
print('LogProd ZA=%.1f max rel err %s' % (LP.ZA, mp.nstr(worst, 3)), flush=True)

# 2. Abel-Plana 1D: sum_{n>=0} Gamma(n+K+a)/Gamma(n+K+a+gam) = Gamma(K+a)/((gam-1) Gamma(K+a+gam-1))
for a, gam in [(mp.mpf('0.3'), mp.mpf('1.35')), (mp.mpc('0.3', '0.4'), mp.mpc('1.6', '-0.3'))]:
    Lf = E.LogProd([(a, a + gam)])
    f = lambda x: mp.exp(Lf(x))
    K = mp.mpf(cfg.K)
    rule = E.ts01(mp.re(gam) - 1, cfg.D, cfg.h)
    JR = E.jrule(cfg.D, cfg.ngl)
    real = mp.im(a) == 0 and mp.im(gam) == 0
    val = E.I_apply(f, K, rule) + f(K) / 2 + E.J_apply(f, K, JR, real)
    ref = mp.gamma(K + a) / ((gam - 1) * mp.gamma(K + a + gam - 1))
    print('AP1D a=%s gam=%s nodes I=%d J=%d rel err %s' % (a, gam, len(rule), len(JR), mp.nstr(abs(val / ref - 1), 3)), flush=True)

# 3. quadrant closed form: W=e_q=(d-1)_q/q!, V=f_g(m+a), U=f_hh(p+a+g-d+1)
for (d, g, a, hh) in [(mp.mpf('1.3'), mp.mpf('0.8'), mp.mpf('0.37'), mp.mpf('0.9')),
                      (mp.mpf('2.4'), mp.mpc('1.7', '0.15'), mp.mpc('0.37', '0.2'), mp.mpc('0.8', '-0.25')),
                      (mp.mpf('3.1'), mp.mpf('2.45'), mp.mpf('-0.6'), mp.mpf('0.9'))]:
    LW = E.LogProd([(d - 1, 1)], const=-mp.loggamma(d - 1))
    LV = E.LogProd([(a, a + g)])
    c = a + g - d + 1
    LU = E.LogProd([(c, c + hh)])
    real = all(mp.im(x) == 0 for x in (d, g, a, hh))
    Q = E.Quadrant(LU, LV, LW, -mp.re(hh), -mp.re(g), d - 2, real)
    t0 = time.time()
    val, det = Q.total(cfg, details=True)
    gam = g - d + 1 + hh
    ref = mp.gamma(g - d + 1) / mp.gamma(g) * mp.gamma(a) / ((gam - 1) * mp.gamma(a + gam - 1))
    print('Quadrant d=%s g=%s a=%s hh=%s : rel err %s  (%.1fs)' % (d, g, a, hh, mp.nstr(abs(val / ref - 1), 3), time.time() - t0),
          flush=True)
    print('   parts', {k: mp.nstr(v, 8) for k, v in det.items()}, flush=True)
