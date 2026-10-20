#!/usr/bin/env python3
"""Exploratory: is the normalized r=3 zero mode c0hat(d; d/2) a Gamma product at non-integer d?
PSLQ of log|c0hat| against logs of pi, 2, 5, golden ratio, Gamma(1/5), Gamma(2/5) at d = 1.6, 2.4 (q = 2/5, 3/5)."""
import os, sys
import mpmath as mp
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Z'))
import Z_general as ZG
dps = int(sys.argv[1]) if len(sys.argv) > 1 else 30
mp.mp.dps = dps
for dstr in sys.argv[2:] or ['8/5', '12/5']:
    r = ZG.Z(dstr, dps, full=True)
    c0 = mp.re(r['c0hat'][0]); Q = r['Q']; R = mp.re(r['R'][0])
    with mp.workdps(dps):
        phi = (1 + mp.sqrt(5)) / 2
        names = ['log|c0|', 'log pi', 'log 2', 'log 5', 'log phi', 'log G(1/5)', 'log G(2/5)']
        vec = [mp.log(abs(c0)), mp.log(mp.pi), mp.log(2), mp.log(5), mp.log(phi), mp.loggamma(mp.mpf(1)/5), mp.loggamma(mp.mpf(2)/5)]
        rel = mp.pslq(vec, maxcoeff=10**6, maxsteps=10**6, tol=mp.mpf(10)**(-dps+5))
        print(dstr, 'c0hat =', mp.nstr(c0, 25), ' Q =', mp.nstr(Q, 20), ' R =', mp.nstr(R, 20))
        print('   pslq(log|c0|):', rel)
        vec2 = [mp.log(abs(Q))] + vec[1:]
        print('   control pslq(log Q):', mp.pslq(vec2, maxcoeff=10**6, maxsteps=10**6, tol=mp.mpf(10)**(-dps+5)))
