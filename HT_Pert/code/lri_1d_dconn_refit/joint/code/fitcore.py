#!/usr/bin/env python3
"""Linked joint tail model, high precision (python-flint arb), with exact first-order propagation of data perturbations.

Model (LRI_HT_note eq. joint; ljm.py of the C8 linked-joint lens):
   Y_n(L) = C_n(L) + sum_{j=1}^{n-2} e_j(ell) [C_{n-j}(L) - lim_{n-j}]  =  lim_n + a_n T2(L) + sum_b c_b z^-p ell^q
with z = L + shift, ell = log z, T2 = C2(L) - C2(inf), e_j the eps-coefficients of exp(ell * sum_k omega_k eps^k),
omega_1..omega_5 from the phi6 gap fits; lim_2 = C2, lim_3 = C3 exact controls; lim_4..lim_8 fitted sequentially.
Order 8: omega_6 unknown -> extra column ell*T2 whose coefficient is -omega_6 (unless fixed_omega6 given).
free_orders: order n<8 gets omega_{n-2}=0 in e and the column ell*T2 (coef -omega_{n-2}); the fitted omega feeds e_j at
higher orders (the 'free exponents' variant of analyze_joint / ljm).

This file is a re-implementation of linked-joint/ljm_hp.py (C8 lens) with three additions:
  * extra basis modifiers (FL = freed leading tail L^-1/2, L^-1/2 log L at orders <= 7; Dj = analyze_joint's D; extra
    subleading powers),
  * full pseudo-inverse rows in float -> exact first-order response of every intercept to arbitrary data perturbations
    (delta-model variants and band edges), including the feed of freed omegas into higher-order e_j,
  * residual vectors on request.
Data enter as float64 and are converted exactly to arb; LS by column-scaled normal equations in arb (cond^2 << 2^-prec).
"""
import math
import numpy as np
from flint import arb, arb_mat, ctx

C2A = C3A = None
PREC = None


def set_prec(bits):
    global C2A, C3A, PREC
    ctx.prec = bits
    PREC = bits
    C2A = (arb.pi() + 4 * arb(2).log()) / 9
    C3A = (arb.pi() ** 2 + 6 * arb.pi() * arb(2).log() + 12 * arb(2).log() ** 2 - 6 * arb(0.25).gamma() ** 4 / arb.pi()) / 81


set_prec(256)
C2F = (math.pi + 4 * math.log(2)) / 9
C3F = -3.71985632290183342248988571266
A_ = math.pi + 4 * math.log(2)

OMEGA_ORIG = [0., 3.5, -29.552388360629354, 556.2143040434153, -13457.689278726075, 376964.56135577295, 0., 0., 0.]
OMEGA_EXT = [0., 3.5, -29.552388360629354, 556.2011107308521, -13455.32792429696, 376987.01090272394, 0., 0., 0.]
# window-free gap sensitivity (LRI_HT_note Secs. 3.8, 5.10; eps5_window/challenge-theory/omega_consistency.py):
# omega2 = -5A (continuum), omega3 = ext - 0.14603; omega4, omega5 = ext (their window shifts are unknown)
OMEGA_WF = [0., 3.5, -5 * A_, 556.2011107308521 - 0.14603, -13455.32792429696, 376987.01090272394, 0., 0., 0.]
GAPS = {'orig': OMEGA_ORIG, 'ext': OMEGA_EXT, 'wf': OMEGA_WF}

REF = {2: C2F, 3: C3F, 4: 45.42488010356, 5: -731.13947662454, 6: 14331.68703277, 7: -322550.0, 8: 8066723.0}
REF_ERR = {4: 1e-10, 5: 1e-10, 6: 4.9e-7, 7: 41.0, 8: 8015.0}
C7_ALT = -322524.0   # post hoc truncation-aware C7 (+-38)

BASES = {
    'A': [(1, 0), (1.5, 0), (1.5, 1), (2, 0)],
    'B': [(1, 0), (1.5, 0), (1.5, 1), (2, 0), (2, 1)],
    'C': [(1, 0), (1.5, 0), (1.5, 1), (1, 1)],
    'D': [(1, 0), (1.5, 0), (1.5, 1), (2, 0), (2.5, 0)],          # C8-code naming (extrapolate.py / ljm.py)
    'Dj': [(1, 0), (1, 1), (1.5, 0), (1.5, 1), (2, 0)],           # analyze_joint naming of D (thermal campaign)
    'E': [(1, 0), (1, 1), (1.5, 0), (1.5, 1), (2, 0), (2, 1)],
    'F': [(1, 0), (1.5, 0), (1.5, 1), (1.5, 2), (2, 0)],
    'BD': [(1, 0), (1.5, 0), (1.5, 1), (2, 0), (2, 1), (2.5, 0)],
    'S': [(1, 0), (1, 1), (1.5, 0), (1.5, 1), (1.5, 2), (2, 0), (2, 1)],
    'Bp': [(1, 0), (1.5, 0), (1.5, 1), (2, 0), (2, 1), (2.5, 0), (2.5, 1)],
}


def terms_for(spec, n):
    """spec 'NAME+mod+mod'. mods: tower1 (l^j/L, j=1..n-4), tower15 (l^j/L^1.5, j=2..n-4), L075, L1l2,
    FL (freed leading tail (0.5,0),(0.5,1) at orders n<=7), FL5 (same at 5<=n<=7 only), FL8 (at every order incl. 8),
    p25 (2.5,0), p25l (2.5,1), p3 (3,0)."""
    name, *mods = spec.split('+')
    t = list(BASES[name])

    def add(x):
        if x not in t:
            t.append(x)
    for m in mods:
        if m == 'tower1':
            for j in range(1, n - 3):
                add((1, j))
        elif m == 'tower15':
            for j in range(2, n - 3):
                add((1.5, j))
        elif m == 'L075':
            add((0.75, 0))
        elif m == 'L1l2':
            add((1, 2))
        elif m == 'FL':
            if n <= 7:
                add((0.5, 0)); add((0.5, 1))
        elif m == 'FL5':
            if 5 <= n <= 7:
                add((0.5, 0)); add((0.5, 1))
        elif m == 'FL8':
            add((0.5, 0)); add((0.5, 1))
        elif m == 'p25':
            add((2.5, 0))
        elif m == 'p25l':
            add((2.5, 1))
        elif m == 'p3':
            add((3, 0))
        else:
            raise ValueError(m)
    return t


def af(x):
    return float(x.mid())


def eseries_a(ell, omega, nmax):
    e = [[arb(1)] * len(ell)]
    for n in range(1, nmax + 1):
        e.append([ell[i] / n * sum((j * arb(omega[j]) * e[n - j][i] for j in range(1, n + 1)), arb(0)) for i in range(len(ell))])
    return e


def lsq_a(cols, y):
    """Column-scaled normal equations in arb (midpoint solves). Returns coef (arb list), pinv (float, ncol x m, unscaled),
    cond (float, of the scaled design)."""
    m = len(y); k = len(cols)
    scale = [sum((c[i] ** 2 for i in range(m)), arb(0)).sqrt() for c in cols]
    X = arb_mat([[cols[j][i] / scale[j] for j in range(k)] for i in range(m)])
    Xt = X.transpose()
    G = Xt * X
    Gi = G.solve(arb_mat([[arb(1) if i == j else arb(0) for j in range(k)] for i in range(k)]), algorithm='approx')
    P = Gi * Xt                       # pinv of the scaled design
    Y = arb_mat([[v] for v in y])
    b = P * Y
    coef = [b[j, 0] / scale[j] for j in range(k)]
    Pf = np.array([[af(P[j, i] / scale[j]) for i in range(m)] for j in range(k)])
    Gf = np.array([[af(G[i, j]) for j in range(k)] for i in range(k)])
    Gif = np.array([[af(Gi[i, j]) for j in range(k)] for i in range(k)])
    cond = float(np.sqrt(abs(np.max(np.linalg.eigvalsh(Gf)) * np.max(np.linalg.eigvalsh(Gif)))))
    return coef, Pf, cond


def fit(L, C, lo, hi, spec='A', shift=0., omega=OMEGA_EXT, maxorder=8, free_orders=(), fixed_omega6=None, hi_low=None,
        sigraw=None, perts=None, want_res=False, fixed_lim=None, wrel=None, sigx=None, wfit=None):
    """Sequential linked fit.
    L (float array), C (len(L) x 9 array; NaN allowed where unused, e.g. C8 beyond 92).
    hi_low: if given, orders <= 7 are fitted on [lo, hi_low] and order 8 (or maxorder) on [lo, hi]; else all on [lo, hi].
    perts: dict name -> len(L) x 9 array of data perturbations. Returns d lim_n for every n (exact first order, including
           the feed of freed omegas into higher-order e_j; exact for fixed-omega fits since the chain is linear).
    sigraw: {k: sigma} white noise per raw coefficient -> 'stat' (gradient propagation, ignoring the omega feed).
    fixed_lim: {n: value} imposes an intercept (calibration only).
    refit72 additions (diagnostics only; the least squares stay unweighted, so intercepts are unchanged):
    wrel: {n: array over L} relative per-point noise of Y_n (1 at quiet points) -> 'erms' = sqrt(mean((res/wrel)^2)), the
          residual rms the fit would have if every point were at the quiet noise level, and 'emax' = max |res/wrel|.
    sigx: {k: array over L} extra white noise of the data C_k(L) (e.g. the S10 cluster noise at L = 46..72) ->
          'stat_x' = its propagated intercept error (gradient, same as 'stat', with the low/top windows of one L merged).
    wfit: {n: array over L} weights for a WEIGHTED least-squares variant (rows / wfit); None = the run1 unweighted fit."""
    omega = list(omega)
    fixed_lim = fixed_lim or {}
    lim = {2: C2A, 3: C3A}
    limf = {2: C2F, 3: C3F}
    grad = {}
    out = dict(lo=lo, hi=hi, spec=spec, shift=shift, orders={})
    pnames = list(perts) if perts else []
    dlim = {n: np.zeros(len(pnames)) for n in range(2, maxorder + 1)}
    domega = {}                         # k -> array over perts (only for freed omegas)
    for n in range(4, maxorder + 1):
        uselow = hi_low is not None and n <= 7
        msk = (L >= lo) & (L <= (hi_low if uselow else hi))
        a = L[msk]; d = C[msk]
        npt = len(a)
        if np.any(~np.isfinite(d[:, 2:n + 1])):
            raise ValueError('missing data in window')
        z = [arb(float(x)) + arb(shift) for x in a]
        ell = [x.log() for x in z]
        Ca = {k: [arb(float(v)) for v in d[:, k]] for k in range(2, n + 1)}
        T2 = [Ca[2][i] - C2A for i in range(npt)]
        free = (n == 8 and fixed_omega6 is None) or (n < 8 and n in free_orders)
        om = list(omega)
        if free:
            om[n - 2] = 0.
        if n == 8 and fixed_omega6 is not None:
            om[6] = fixed_omega6
        e = eseries_a(ell, om, n - 2)
        Y = [Ca[n][i] + sum((e[j][i] * (Ca[n - j][i] - lim[n - j]) for j in range(1, n - 1)), arb(0)) for i in range(npt)]
        terms = terms_for(spec, n)
        cols = [[arb(1)] * npt, T2] + [[z[i] ** arb(-p) * ell[i] ** q for i in range(npt)] for p, q in terms]
        if free:
            cols.append([ell[i] * T2[i] for i in range(npt)])
        if npt <= len(cols):
            raise ValueError('insufficient points')
        if wfit is not None and n in wfit:
            # refit72 weighted least squares: rows scaled by 1/w (w = relative per-point noise of Y_n); P is mapped back so
            # that it acts on the unweighted Y (perturbation and noise propagation below stay valid); residuals unweighted
            wv = np.asarray(wfit[n][msk], float)
            iw = [arb(1.0 / float(x)) for x in wv]
            lsq_cols = [[c[i] * iw[i] for i in range(npt)] for c in cols]
            lsq_Y = [Y[i] * iw[i] for i in range(npt)]
        else:
            wv = None; lsq_cols = cols; lsq_Y = Y; iw = None
        if n in fixed_lim:
            Yf = [Y[i] - arb(fixed_lim[n]) for i in range(npt)]
            if iw is not None:
                Yf = [Yf[i] * iw[i] for i in range(npt)]
            coef, P, cond = lsq_a(lsq_cols[1:], Yf)
            coef = [arb(fixed_lim[n])] + coef
            P = np.vstack([np.zeros(npt), P])
        else:
            coef, P, cond = lsq_a(lsq_cols, lsq_Y)
        if wv is not None:
            P = P / wv[None, :]
        res = [sum((coef[j] * cols[j][i] for j in range(len(cols))), arb(0)) - Y[i] for i in range(npt)]
        resf = np.array([af(r) for r in res])
        lim[n] = arb(coef[0].mid())
        limf[n] = af(lim[n])
        if free:
            omega[n - 2] = -af(coef[-1])
        elif n == 8 and fixed_omega6 is not None:
            omega[6] = fixed_omega6
        ef = np.array([[af(e[j][i]) for i in range(npt)] for j in range(n - 1)])     # e_0..e_{n-2}
        ellf = np.array([af(x) for x in ell])
        # ---- perturbation propagation (exact first order)
        if pnames:
            dC = np.array([perts[p][msk] for p in pnames])   # npert x npt x 9
            dY = dC[:, :, n].copy()
            for j in range(1, n - 1):
                dY += ef[j][None, :] * (dC[:, :, n - j] - dlim[n - j][:, None])
                # feed of freed omegas: d e_j / d omega_k = ell * e_{j-k}
                dej = np.zeros_like(dY)
                for k, dw in domega.items():
                    if k <= j and k != (n - 2 if free else -1):
                        dej += (ellf * ef[j - k])[None, :] * dw[:, None]
                dY += dej * (d[:, n - j] - limf[n - j])[None, :]
            db = dY @ P.T           # npert x ncol
            dlim[n] = db[:, 0]
            if free and n < 8:
                domega[n - 2] = -db[:, -1]
        # ---- noise propagation (gradient, ignoring the omega feed)
        stat = None
        stat_x = None
        if sigraw is not None:
            g = {}
            row = P[0]
            Lkeys = [float(x) for x in a]
            tag = 'low' if uselow else 'top'

            def addto(k, Lk, v):
                g.setdefault(k, {}); g[k][(tag, Lk)] = g[k].get((tag, Lk), 0.) + v
            for i, Lk in enumerate(Lkeys):
                addto(n, Lk, row[i])
                for j in range(1, n - 1):
                    addto(n - j, Lk, row[i] * ef[j][i])
            for j in range(1, n - 1):
                if n - j >= 4:
                    s = float(np.dot(row, ef[j]))
                    for k, dd in grad[n - j].items():
                        for Lk, v in dd.items():
                            g.setdefault(k, {}); g[k][Lk] = g[k].get(Lk, 0.) - s * v
            grad[n] = g
            stat = float(np.sqrt(sum(sigraw[k] ** 2 * sum(v ** 2 for v in dd.values()) for k, dd in g.items())))
            if sigx is not None:
                Lidx = {float(x): i for i, x in enumerate(L)}
                sx2 = 0.
                for k, dd in g.items():
                    if k not in sigx:
                        continue
                    gL = {}
                    for (tg, Lk), v in dd.items():
                        gL[Lk] = gL.get(Lk, 0.) + v
                    sx2 += sum((sigx[k][Lidx[Lk]] * v) ** 2 for Lk, v in gL.items())
                stat_x = float(np.sqrt(sx2))
        if wrel is not None and n in wrel:
            rw = resf / wrel[n][msk]
            erms, emax = float(np.sqrt(np.mean(rw ** 2))), float(np.max(np.abs(rw)))
        else:
            erms, emax = float(np.sqrt(np.mean(resf ** 2))), float(np.max(np.abs(resf)))
        od = dict(lim=limf[n], maxres=float(np.max(np.abs(resf))), rms=float(np.sqrt(np.mean(resf ** 2))), cond=cond,
                  erms=erms, emax=emax, stat_x=stat_x,
                  gain=float(np.sum(np.abs(P[0]))), stat=stat, npts=npt, ncol=len(cols),
                  omega_fit=(omega[n - 2] if free else None), coef=[af(c) for c in coef], terms=terms)
        if want_res:
            od['L'] = a.tolist(); od['res'] = resf.tolist()
        out['orders'][n] = od
    out['lim'] = {n: limf[n] for n in range(4, maxorder + 1)}
    out['omega'] = omega
    if pnames:
        out['dlim'] = {n: dict(zip(pnames, dlim[n].tolist())) for n in range(4, maxorder + 1)}
    return out
