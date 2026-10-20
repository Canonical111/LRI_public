#!/usr/bin/env python3
"""error budget of route B relative to route A, node by node, using the identical spin-level Abel-Plana nodes:
   direct part, x-integral (weight dx/du * h), y-integral (-2 Im f / (e^{2 pi y}-1) * dy/du * h)."""
import json, sys, mpmath as mp
mp.mp.dps = 60
fa, fb = sys.argv[1], sys.argv[2]
A = json.load(open(fa)); B = json.load(open(fb))
L = int(A['L']); assert int(B['L']) == L
dps = int(A['dps'])
ra = {tuple(r[:3]): [mp.mpmathify(x) for x in r[3]] for r in A['results']}
rb = {tuple(r[:3]): [mp.mpmathify(x) for x in r[3]] for r in B['results']}
sc = [1, 1, 1, 1, mp.mpf(1) / 4, mp.mpf(1) / 4]      # route A Kint -> K bracket (/4); B is already K bracket
names = ['W3', 'W4', 'L', 'Z', 'K', 'Kc']
h = mp.mpf(1) / 16
Dd = (dps + 8) * mp.log(10)
d = mp.mpf(A['d'])
def dif(k, i):
    return rb[k][i] - ra[k][i if i < 5 else 4] * sc[i]
# direct
out = {}
for i in range(6):
    dd = sum(dif(('dir', str(l), '0'), i) for l in range(L))
    half = dif(('dir', str(L), '0'), i) / 2
    # x nodes
    xs = 0; xmax = (0, None)
    for k in ra:
        if k[0] != 'x':
            continue
    # rebuild weights exactly as the drivers do
    import importlib.util
    out[names[i]] = [dd, half]
# x-integral weights: x = L + L exp(pi/2 sinh u); w = (x-L) pi/2 cosh u * h  -> recover u from x
def xweight(x):
    e = x - L
    if e <= 0:
        return mp.mpf(0)
    u = mp.asinh(2 / mp.pi * mp.log(e / L))
    return e * mp.pi / 2 * mp.cosh(u) * h
def ywt(y):
    # y = exp(u - e^{-u}): solve for u
    u = mp.findroot(lambda u: u - mp.exp(-u) - mp.log(y), mp.log(y) if y > 1 else -mp.log(-mp.log(y)))
    return y * (1 + mp.exp(-u)) * h
for i in range(6):
    xs = 0; worst = []
    for k in ra:
        if k[0] == 'x':
            x = mp.mpf(k[1]); c = dif(k, i) * xweight(x); xs += c; worst.append((abs(c), x))
    ys = 0; worsty = []
    for k in ra:
        if k[0] == 'y':
            y = mp.mpf(k[2]); c = -2 * mp.im(dif(k, i)) / mp.expm1(2 * mp.pi * y) * ywt(y); ys += c; worsty.append((abs(c), y))
    worst.sort(reverse=True); worsty.sort(reverse=True)
    dd, half = out[names[i]]
    print('%-3s B-A: direct %-10s f(L)/2 %-10s x-int %-10s (largest node %s at x=%s)  y-int %-10s (largest %s at y=%s)  total %s' % (
        names[i], mp.nstr(dd, 3), mp.nstr(half, 3), mp.nstr(xs, 3), mp.nstr(worst[0][0], 3), mp.nstr(worst[0][1], 4),
        mp.nstr(ys, 3), mp.nstr(worsty[0][0], 3), mp.nstr(worsty[0][1], 4), mp.nstr(dd + half + xs + ys, 3)))
