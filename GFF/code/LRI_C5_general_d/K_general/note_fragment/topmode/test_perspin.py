#!/usr/bin/env python3
"""Validation of perspin_topmode.S_spin against a brute-force evaluation (direct sum to |n|~1500 plus
mpmath sumem (Euler-Maclaurin with numerical integral/derivatives) on the reflected tails)."""
import time
import mpmath as mp
import perspin_topmode as P
mp.mp.dps = 30
case = P.cases()['R1']
G, rG = mp.gamma, mp.rgamma
sig, left, right = case['sigma'], case['left'], case['right']

def term(l, n, t):
    v = mp.mpf(1)
    for al, g in left:
        v *= G(l + sig + al + n + t) * rG(l + sig + al + g + n + t)
    for be, h in right:
        v *= G(be - n - t) * rG(be + h - n - t)
    return v

def brute(l, t, N=1500):
    # direct
    s = mp.fsum(term(l, n, t) for n in range(-N, N))
    TR = 1
    for be, h in right:
        TR *= mp.sin(mp.pi * (be + h - t)) / mp.sin(mp.pi * (be - t))
    TL = 1
    for al, g in left:
        TL *= mp.sin(mp.pi * (sig + al + g + t)) / mp.sin(mp.pi * (sig + al + t))
    def fr(x):
        v = TR
        for al, g in left:
            a = l + sig + al + t
            v *= mp.exp(mp.loggamma(x + a) - mp.loggamma(x + a + g))
        for be, h in right:
            v *= mp.exp(mp.loggamma(x + 1 - be - h + t) - mp.loggamma(x + 1 - be + t))
        return v
    def fl(x):
        v = TL
        for al, g in left:
            v *= mp.exp(mp.loggamma(x + 1 - l - sig - al - g - t) - mp.loggamma(x + 1 - l - sig - al - t))
        for be, h in right:
            v *= mp.exp(mp.loggamma(x + be - t) - mp.loggamma(x + be + h - t))
        return v
    rt = mp.sumem(fr, [N, mp.inf])
    lt = mp.sumem(fl, [N + 1, mp.inf])
    return s + rt + lt

for l, t in ((0, mp.mpf('0.0731')), (3, mp.mpf('0.4731')), (17, mp.mpf('0.2731'))):
    st = time.time()
    a, chk = P.S_spin(case, l, t)
    t1 = time.time() - st
    b = brute(l, t)
    print('l=%d t=%s  S_spin=%s  brute=%s  rel.diff=%s  tail-consistency=%s  (%.2fs vs %.1fs)'
          % (l, t, mp.nstr(a, 20), mp.nstr(b, 20), mp.nstr(abs(a / b - 1), 3), mp.nstr(chk, 3), t1, time.time() - st - t1), flush=True)
