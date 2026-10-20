"""Verifier's own implementation of the model-independent lens's primary family (mode E: exact lower limits; level
'full': omega_1..omega_{n-3} fixed (window-free set), top omega free via l*T2; lead T2 or x = L^-1/2 with l^0, l^1;
tails L^-p l^j, p = 1..pmax (step 1/2), j = 0..J), its adequacy selection (maxres <= FAC*floor, gain*floor/2 <=
NOISE*|c|, floor = 5th percentile of maxres over the family at that hi) and the pre-declared calibration
C8cal = c8 (1 - mean_{n=4..7} b_n), b_n = (c_n - ref_n)/|ref_n|. Own code (arb least squares), own tables.
"""
import math, itertools, sys
import numpy as np
from flint import arb
from mylsq import solve
from myjoint import C2X, C3X

A_ = arb.pi() + 4 * arb(2).log()
W_RAW3, W_RAW4, W_RAW5 = 556.2011107308521, -13455.32792429696, 376987.01090272394
DOM3 = -(2 * A_ + 3) / 81 + arb(1) / 27
WF = {1: arb('3.5'), 2: -5 * A_, 3: arb(W_RAW3) + DOM3, 4: arb(W_RAW4), 5: arb(W_RAW5)}
REF = {4: 45.42488010356, 5: -731.13947662454, 6: 14331.68703277, 7: -322550.0, 8: 8066723.0}
LOS = (8, 10, 12, 16, 20, 24, 32, 40, 50)
TAILSETS = []
for pmax in (1.5, 2, 2.5, 3):
    for J in (0, 1, 2, 3):
        TAILSETS.append(('p%s_J%d' % (pmax, J), [(q / 2, j) for q in range(2, int(round(2 * pmax)) + 1) for j in range(J + 1)]))


def eser(l, w, m):
    e = [arb(1)]
    for k in range(1, m + 1):
        e.append(l * sum((j * w[j] * e[k - j] for j in range(1, k + 1) if j in w), arb(0)) / k)
    return e


def run_family(L, C, hi, c7ref=REF[7], los=LOS):
    """Returns dict key=(tails, lead, lo) -> {n: (c, maxres, gain)} for n = 4..8 (n=8 only if hi <= 92)."""
    lims = {2: C2X, 3: C3X}
    for k in (4, 5, 6):
        lims[k] = arb(REF[k])
    lims[7] = arb(c7ref)
    out = {}
    Lall = [int(x) for x in L]
    row = {l: i for i, l in enumerate(Lall)}
    for (tn, terms), lead, lo in itertools.product(TAILSETS, ('T2', 'x'), los):
        if lo >= hi:
            continue
        Lw = [l for l in Lall if lo <= l <= hi]
        if len(Lw) < 1 + 2 + len(terms) + 3:
            continue
        res = {}
        for n in range(4, 9):
            Ls = [l for l in Lw if l <= 92] if n == 8 else Lw
            if n == 8 and hi > 92:
                continue
            if len(Ls) < 1 + 2 + len(terms) + 3:
                continue
            w = {j: WF[j] for j in range(1, n - 2)}
            S = []
            cols = [[] for _ in range(3 + len(terms))]
            for l in Ls:
                i = row[l]
                la = arb(l); z = la.log()
                e = eser(z, w, n - 2)
                s = arb(float(C[i, n]))
                for j in range(1, n - 1):
                    s += e[j] * (arb(float(C[i, n - j])) - lims[n - j])
                S.append(s)
                b = (arb(float(C[i, 2])) - C2X) if lead == 'T2' else la ** arb(-0.5)
                cols[0].append(arb(1)); cols[1].append(b); cols[2].append(b * z)
                for t, (p, j) in enumerate(terms):
                    cols[3 + t].append(la ** arb(-p) * z ** j)
            r = solve(cols, S, want_pinv0=True)
            res[n] = (float(r['coef'][0].mid()), float(np.max(np.abs(r['res']))), float(np.sum(np.abs(r['p0']))))
        out[(tn, lead, lo)] = res
    return out


def analyze(F, FAC=10., NOISE=1e-4, BMAX=1e-3, c7ref=REF[7]):
    ref = dict(REF); ref[7] = c7ref
    fl = {}
    for n in range(4, 9):
        v = [F[k][n][1] for k in F if n in F[k]]
        if v:
            fl[n] = float(np.percentile(v, 5))
    adq = lambda k, n: n in F[k] and F[k][n][1] <= FAC * fl[n] and F[k][n][2] * 0.5 * fl[n] <= NOISE * abs(F[k][n][0])
    b = lambda k, n: (F[k][n][0] - ref[n]) / abs(ref[n])
    out = dict(floors=fl)
    if 8 in fl:
        A8 = [k for k in F if adq(k, 8)]
        cal = [k for k in A8 if all(n in F[k] and abs(b(k, n)) < BMAX for n in range(4, 8))]
        c8 = np.array([F[k][8][0] for k in cal])
        B = np.array([[b(k, n) for n in range(4, 8)] for k in cal]) if cal else np.zeros((0, 4))
        out['C8'] = dict(nadq=len(A8), ncal=len(cal), cal=sorted(cal),
                         uncal=float(np.median(c8)) if cal else None,
                         calib=float(np.median(c8 * (1 - B.mean(axis=1)))) if cal else None,
                         per=[(k, F[k][8][0], float(F[k][8][0] * (1 - B[i].mean()))) for i, k in enumerate(cal)],
                         adq_median=float(np.median([F[k][8][0] for k in A8])) if A8 else None,
                         bias_med=[float(np.median(B[:, i])) for i in range(4)] if cal else None)
    for n in (6, 7):
        A = [k for k in F if adq(k, n)]
        low4 = list(range(4, n))
        cal = [k for k in A if all(abs(b(k, j)) < BMAX for j in low4)]
        c = np.array([F[k][n][0] for k in cal])
        bl = np.array([np.mean([b(k, j) for j in low4]) for k in cal])
        out['C%d' % n] = dict(nadq=len(A), ncal=len(cal), uncal=float(np.median(c)) if cal else None,
                              calib=float(np.median(c - bl * np.abs(c))) if cal else None)
    return out
