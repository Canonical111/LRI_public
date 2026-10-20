#!/usr/bin/env python3
"""Spin-summed finite-mode check: Xi_R(t) (regularized Horn blocks) is a trigonometric polynomial with |k|<=2,
and <t^2 R_tau> from two different 5-node sets agrees."""
import sys
import mpmath as mp
import rblocks as rb
mp.mp.dps = 40
for ds, ts in (('2.5', '0.1'), ('1.25', '0.3'), ('0.8', '0.15'), ('2.75', '0.05+0.07j')):
    d = mp.mpf(ds); q = d / 4; tau = mp.mpmathify(ts)
    nodes = rb.default_nodes(mp.mpf('0.0917'))
    vals = [rb.sample(q, t, tau, 20, 220) for t in nodes]
    M = mp.matrix([[mp.expj(2 * mp.pi * k * t) for k in range(-2, 3)] for t in nodes])
    c = mp.lu_solve(M, mp.matrix(vals))
    errs = []
    for t in (mp.mpf('0.0331'), mp.mpf('0.4471'), mp.mpf('0.7777')):
        pred = mp.fsum(c[k + 2] * mp.expj(2 * mp.pi * k * t) for k in range(-2, 3))
        x = rb.sample(q, t, tau, 20, 220)
        errs.append(mp.nstr(abs(pred - x) / abs(x), 3))
    v1 = mp.fsum(w * x for w, x in zip(rb.weights(q, tau, nodes), vals))
    nodes2 = rb.default_nodes(mp.mpf('0.0433'))
    v2 = rb.tR(q, tau, 20, 220, nodes2)
    print('d', ds, 'tau', ts, ' mode-check rel errs', errs, ' |c_k|', [mp.nstr(abs(c[i]), 6) for i in range(5)],
          ' <t2R> nodesA', mp.nstr(v1, 25), ' nodesB', mp.nstr(v2, 25), ' diff', mp.nstr(abs(v1 - v2), 3), flush=True)
