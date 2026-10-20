"""Verifier (hi72) own linked joint-tail fitter and table builder.
Y_n = C_n + sum_{j=1}^{n-2} e_j(l) [C_{n-j} - lim_{n-j}] = lim_n + a T2 + sum c z^-p l^q  (+ -w l T2 when the top omega is free)
e_j: coefficients of exp(l sum_k w_k eps^k); lim_2, lim_3 exact; z = L + shift, l = log z; order 8 always frees w6.
modes: fixed | free (w3..w5 freed at orders 5..7 and fed upward) | FL (L^-1/2, l L^-1/2 at orders <= 7) | FL5 (orders 5..7).
Optional weights per order (rows multiplied by 1/sigma). Tables built from raw sources + dC (own loader).
"""
import math, json, csv
import numpy as np
from flint import arb
import mylsq
from mylsq import solve
from myload import load, SCR

PI = arb.pi(); LN2 = arb(2).log()
C2X = (PI + 4 * LN2) / 9
C3X = (PI ** 2 + 6 * PI * LN2 + 12 * LN2 ** 2 - 6 * arb(0.25).gamma() ** 4 / PI) / 81
A_ = math.pi + 4 * math.log(2)
W_ORIG = {1: 3.5, 2: -29.552388360629354, 3: 556.2143040434153, 4: -13457.689278726075, 5: 376964.56135577295}
W_EXT = {1: 3.5, 2: -29.552388360629354, 3: 556.2011107308521, 4: -13455.32792429696, 5: 376987.01090272394}
W_WF = {1: 3.5, 2: -5 * A_, 3: 556.2011107308521 - 0.14603, 4: -13455.32792429696, 5: 376987.01090272394}
GAPS = {'orig': W_ORIG, 'ext': W_EXT, 'wf': W_WF}
BASES = {
    'A': [(1, 0), (1.5, 0), (1.5, 1), (2, 0)],
    'B': [(1, 0), (1.5, 0), (1.5, 1), (2, 0), (2, 1)],
    'C': [(1, 0), (1.5, 0), (1.5, 1), (1, 1)],
    'D': [(1, 0), (1.5, 0), (1.5, 1), (2, 0), (2.5, 0)],
    'Dj': [(1, 0), (1, 1), (1.5, 0), (1.5, 1), (2, 0)],
    'E': [(1, 0), (1, 1), (1.5, 0), (1.5, 1), (2, 0), (2, 1)],
    'F': [(1, 0), (1.5, 0), (1.5, 1), (1.5, 2), (2, 0)],
    'BD': [(1, 0), (1.5, 0), (1.5, 1), (2, 0), (2, 1), (2.5, 0)],
    'S': [(1, 0), (1, 1), (1.5, 0), (1.5, 1), (1.5, 2), (2, 0), (2, 1)],
    'Bp': [(1, 0), (1.5, 0), (1.5, 1), (2, 0), (2, 1), (2.5, 0), (2.5, 1)],
}
REF = {4: 45.42488010356, 5: -731.13947662454, 6: 14331.68703277, 7: -322550.0, 8: 8066723.0}


def terms(base, mode, n):
    nm, *mods = base.split('+')
    t = list(BASES[nm])
    for m in mods:
        if m == 'tower1':
            t += [(1, j) for j in range(1, n - 3) if (1, j) not in t]
        elif m == 'tower15':
            t += [(1.5, j) for j in range(2, n - 3) if (1.5, j) not in t]
        elif m == 'L075':
            t.append((0.75, 0))
        elif m == 'p25':
            t.append((2.5, 0)) if (2.5, 0) not in t else None
        else:
            raise ValueError(m)
    if (mode == 'FL' and n <= 7) or (mode == 'FL5' and 5 <= n <= 7):
        t += [(0.5, 0), (0.5, 1)]
    return t


def eser(l, w, m):
    e = [[arb(1)] * len(l)]
    for k in range(1, m + 1):
        e.append([l[i] * sum((j * arb(w.get(j, 0.)) * e[k - j][i] for j in range(1, k + 1)), arb(0)) / k for i in range(len(l))])
    return e


def fit(L, C, lo, hi, base='A', mode='fixed', shift=0., gap='ext', maxorder=8, hi_low=None, sig=None, want=False):
    """L: array of cutoffs; C: (nL, 9). sig: optional {n: array over L} row sigmas for weighted LS.
    Returns dict lim[n], diag[n] (rms, maxres, npts, p0 row for noise propagation if want)."""
    w = dict(GAPS[gap])
    lim = {2: C2X, 3: C3X}
    out = {}; diag = {}
    for n in range(4, maxorder + 1):
        top = hi_low if (hi_low is not None and n <= 7) else hi
        idx = [i for i in range(len(L)) if lo <= L[i] <= top]
        z = [arb(float(L[i])) + arb(shift) for i in idx]
        l = [x.log() for x in z]
        Ca = {k: [arb(float(C[i, k])) for i in idx] for k in range(2, n + 1)}
        T2 = [Ca[2][r] - C2X for r in range(len(idx))]
        free = (n == 8) or (mode == 'free' and 5 <= n <= 7)
        wn = dict(w)
        if free:
            wn[n - 2] = 0.
        e = eser(l, wn, n - 2)
        y = [Ca[n][r] + sum((e[j][r] * (Ca[n - j][r] - lim[n - j]) for j in range(1, n - 1)), arb(0)) for r in range(len(idx))]
        cols = [[arb(1)] * len(idx), T2] + [[z[r] ** arb(-p) * l[r] ** q for r in range(len(idx))] for p, q in terms(base, mode, n)]
        if free:
            cols.append([l[r] * T2[r] for r in range(len(idx))])
        if len(idx) <= len(cols):
            raise ValueError('too few points')
        wt = None if sig is None else 1.0 / np.asarray(sig[n])[idx]
        r = solve(cols, y, wt, want_pinv0=want)
        lim[n] = arb(r['coef'][0].mid())
        if free and n < 8:
            w[n - 2] = -float(r['coef'][-1].mid())
        out[n] = float(lim[n].mid())
        d = dict(rms=float(np.sqrt(np.mean(r['res'] ** 2))), maxres=float(np.max(np.abs(r['res']))), npts=len(idx), ncol=len(cols))
        if want:
            d['p0'] = r['p0']; d['idx'] = idx; d['res'] = r['res']
        diag[n] = d
    return dict(lim=out, diag=diag, w=w)


def tables():
    """Own tables on L = 2..118: raw, and corrected with exact dC to 72 and a choice of continuation beyond.
    Returns L, raw, dict of corrected tables: 'fmean' (delta floor-mean smooth table), 'fmedoid', 'median', 'mine'
    (verifier continuation median), 'old' (archived delta-v1 hi=44 floor-mean, rebuilt from archived variants), 's46'."""
    D = load()
    th, c8, rc, dC = D['th'], D['c8'], D['rc'], D['dC678']
    Ls = sorted(th)
    L = np.array(Ls, float)
    raw = np.full((len(L), 9), np.nan)
    for i, l in enumerate(Ls):
        raw[i, :8] = th[l][:8]
        if l in c8:
            raw[i, 8] = c8[l][8]
    base = raw.copy()
    for i, l in enumerate(Ls):
        base[i, 4] += rc[l]['dC4_Dconn']; base[i, 5] += rc[l]['dC5_Dconn']
    # exact dC6..8 to 72
    ex = base.copy()
    for i, l in enumerate(Ls):
        for k in (6, 7, 8):
            if l <= 72 and l >= 2 and k in dC.get(l, {}):
                ex[i, k] += dC[l][k]
            elif l > 72:
                ex[i, k] = np.nan
    out = {}
    tab = {}
    for r in csv.DictReader(open(SCR + '/delta/out/delta_v1_hi72_smooth_table.csv')):
        tab[(int(r['k']), int(r['L']))] = r
    my = json.load(open(SCR + '/verify/out/mycont_dC678.json'))
    Lp = list(range(74, 119, 2))
    for name, col in (('fmean', 'floormean'), ('fmedoid', 'floormedoid'), ('median', 'median'), ('mimedoid', 'medoid'), ('mine', None)):
        T = ex.copy()
        for i, l in enumerate(Ls):
            if l > 72:
                for k in (6, 7, 8):
                    if np.isfinite(raw[i, k]):
                        v = float(tab[(k, l)][col]) if col else my[str(k)]['summary']['median'][Lp.index(l)]
                        T[i, k] = raw[i, k] + v
        out[name] = T
    return L, raw, out, D


def old_table(L, raw, qf=3.0):
    """Archived run1 primary: exact dC to 44 (S10) + mean of floor-level delta-v1 kept fits (hi=44) beyond, rebuilt
    from the archived corrected json (raw/exact flags) and the archived variants (L >= 46 only)."""
    A = '<PROJECT>/lri_1d_coefficient_flow_review/step1_dconn_refit/delta/out/'
    d = json.load(open(A + 'delta_v1_corrected.json'))
    V = json.load(open(A + 'delta_v1_variants.json'))
    Ls = [int(x) for x in L]
    T = raw.copy()
    for k in range(9):
        for r in d['sequences']['C%d' % k]:
            i = Ls.index(r['L'])
            T[i, k] = r['corrected']
    for k in (6, 7, 8):
        b = V['dC%d' % k]
        P = np.array(b['pred']); mr = np.array(b['maxres'])
        lo = np.array([int(s.split('lo=')[1].split('|')[0]) for s in b['labels']])
        best = {x: mr[lo == x].min() for x in set(lo)}
        fl = np.array([mr[i] <= qf * best[lo[i]] for i in range(len(mr))])
        for j, l in enumerate(b['L']):
            if l in Ls and l > 44:
                i = Ls.index(l)
                if np.isfinite(raw[i, k]):
                    T[i, k] = raw[i, k] + P[fl, j].mean()
    return T
