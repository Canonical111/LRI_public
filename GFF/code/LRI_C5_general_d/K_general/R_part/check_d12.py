#!/usr/bin/env python3
"""d=2: J_{2tau} = pi^2 [F(tau)^2 + F(1-tau)^2]  (gc:K2master);  d=1: J_t (t=2tau) = eq:KproofTwoFunctions.
Compare with the generic-d finite-sample formula (rblocks)."""
import sys
import mpmath as mp
import rblocks as rb
mp.mp.dps = 30
F = lambda x: mp.hyp3f2(mp.mpf(1)/2, mp.mpf(1)/2, x, 1, 1, 1)
G = lambda x: mp.hyp3f2(x, x, x, mp.mpf(1)/2 + x, mp.mpf(1)/2 + x, 1)
for tau in (mp.mpf('0.3'), mp.mpf('0.17')):
    q = mp.mpf(1)/2
    Jb = rb.Cfac(q, tau) * rb.tR(q, tau, 14, 160)
    Jc = mp.pi**2 * (F(tau)**2 + F(1 - tau)**2)
    print('d=2 tau', tau, 'blocks', mp.nstr(Jb, 25), 'closed', mp.nstr(Jc, 25), 'diff', mp.nstr(abs(Jb - Jc), 3), flush=True)
    q = mp.mpf(1)/4
    t = 2 * tau
    Jb = rb.Cfac(q, tau) * rb.tR(q, tau, 14, 160)
    Jc = 2*mp.pi*(1 + mp.cos(mp.pi*t) + 2*mp.sin(mp.pi*t)) * mp.gamma(t)**2 / mp.gamma(mp.mpf(1)/2 + t)**2 * G(t) + 2*mp.pi**2*(2 + mp.tan(mp.pi*t/2)) * F(t)
    print('d=1 tau', tau, 'blocks', mp.nstr(Jb, 25), 'closed', mp.nstr(Jc, 25), 'diff', mp.nstr(abs(Jb - Jc), 3), flush=True)
