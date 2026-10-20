#!/usr/bin/env python3
"""N6: the tau-jet circle (outside Omega_q), numerically (PROOF.md Section 6).

At tau on the circles used for the K_d tau-jet the lattice sum S_R diverges; the samples are R_part's analytic
continuation (regularized blocks).  Checked here:
 (i)  9 real nodes t_j = t0 + j/9 -> discrete Fourier modes |k| <= 4 of the continued Xi_R:
      |c_{+-3}|, |c_{+-4}| (and |c_{+-2}|) relative to max |c_k|  -> should vanish (Proposition 7);
 (ii) at complex t = x + i y the continued Xi_R equals the trigonometric polynomial (relative error printed),
      |Xi_R| e^{-2 pi |y|} (bounded, Proposition 7: <= C e^{4 pi|y|}, observed e^{2 pi |y|}),
      and the continued PARTS: P = max(|right|,|middle|,|left|) of S_R, printed as P |y|^{2 Re tau} and P/|S_R|:
      for Re tau <= 0 the parts do not decay, so no part-by-part (lattice-sum) estimate exists on the circle;
      the decay of S_R there is a cancellation between the parts.
usage: n6_jetdisc.py case_index
"""
import sys, json, time
sys.path.insert(0, '<PROJECT>/LRI_C5_general_d/K_general/R_part')
import mpmath as mp
import rblocks as rb

mp.mp.dps = 60
CASES = [('1.5', 'r', '-0.08'), ('1.5', 'i', '0.08'), ('0.8', 'p', '0.04'), ('2.5', 'r', '0.08'), ('3', 'r', '-0.08'),
         ('1.25', 'q', '0.08')]


def tau_of(kind, r):
    r = mp.mpf(r)
    if kind == 'r':
        return mp.mpc(r, 0)
    if kind == 'i':
        return mp.mpc(0, r)
    if kind == 'p':
        return r * mp.expj(3 * mp.pi / 4)
    if kind == 'q':
        return r * mp.expj(mp.pi / 3)


def evaluate(q, tau, t, K=24, M=400):
    Xi, p = rb.sample(q, t, tau, K, M, parts=True)
    g2 = mp.gamma(2 * q) ** 2
    return dict(right=g2 * p['PR'] * p['HR'], middle=g2 * p['PM'] * p['HM'], left=g2 * p['PL'] * p['HL'],
                S=Xi / p['D'], Xi=Xi)


if __name__ == '__main__':
    ci = int(sys.argv[1])
    ds, kind, rs = CASES[ci]
    q = mp.mpf(ds) / 4
    tau = tau_of(kind, rs)
    tstar = max(0, 2 * q - 1, mp.mpf(1) / 2 - 2 * q)
    print('d = %s, tau = %s (|tau| = %s), Re tau = %s, tau_*(q) = %s -> %s Omega_q'
          % (ds, mp.nstr(tau, 6), rs, mp.nstr(mp.re(tau), 4), mp.nstr(tstar, 4),
             'INSIDE' if mp.re(tau) > tstar else 'OUTSIDE'), flush=True)
    st = time.time()
    n = 9
    t0 = mp.mpf('0.0917')
    nodes = [t0 + mp.mpf(j) / n for j in range(n)]
    vals = [rb.sample(q, t, tau, 24, 400) for t in nodes]
    c = {k: mp.fsum(v * mp.expj(-2 * mp.pi * k * t) for v, t in zip(vals, nodes)) / n for k in range(-4, 5)}
    cmax = max(abs(c[k]) for k in c)
    print('  (i) modes |c_k|/max|c|: ' + '  '.join('k=%+d: %s' % (k, mp.nstr(abs(c[k]) / cmax, 3)) for k in range(-4, 5))
          + '   (%.0fs)' % (time.time() - st), flush=True)
    rows = []
    for ys in ('0.5', '1', '2', '3', '-2'):
        y = mp.mpf(ys)
        t = mp.mpc(mp.mpf('0.21'), y)
        st = time.time()
        v = evaluate(q, tau, t)
        w = evaluate(q, tau, t, 32, 560)
        pred = mp.fsum(c[k] * mp.expj(2 * mp.pi * k * t) for k in c)
        P = max(abs(v['right']), abs(v['middle']), abs(v['left']))
        row = dict(y=ys, rel_err_trigpoly=mp.nstr(abs(v['Xi'] - pred) / abs(v['Xi']), 3),
                   conv=mp.nstr(abs(v['S'] - w['S']) / abs(v['S']), 3),
                   Xi_e2pi=mp.nstr(abs(v['Xi']) * mp.exp(-2 * mp.pi * abs(y)), 8),
                   S_e4pi=mp.nstr(abs(v['S']) * mp.exp(4 * mp.pi * abs(y)), 8),
                   parts_y2retau=mp.nstr(P * abs(y) ** (2 * mp.re(tau)), 6), parts_over_S=mp.nstr(P / abs(v['S']), 4))
        rows.append(row)
        print('  (ii) y=%-4s |Xi - trigpoly|/|Xi| = %-9s |Xi|e^{-2pi|y|} = %-12s |S|e^{4pi|y|} = %-12s  max|part| |y|^{2Re tau} = %-10s'
              '  max|part|/|S| = %-10s conv = %s (%.0fs)'
              % (ys, row['rel_err_trigpoly'], row['Xi_e2pi'], row['S_e4pi'], row['parts_y2retau'], row['parts_over_S'],
                 row['conv'], time.time() - st), flush=True)
    json.dump(dict(d=ds, tau=mp.nstr(tau, 15), modes={k: mp.nstr(abs(c[k]), 10) for k in c}, rows=rows),
              open('n6_case%d.json' % ci, 'w'), indent=1)
