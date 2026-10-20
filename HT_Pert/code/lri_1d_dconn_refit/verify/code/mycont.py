"""Verifier's own continuation of dC6..dC8 beyond the last exact L (72), noise-weighted chi^2 family (independent of delta-v1).
Family: non-decaying log polynomial (degree 0..3) + decaying ladder subsets; windows lo in LOS; rows weighted by 1/sigma(L)
with sigma = quiet floor (L <= 44) or S10 noise (46..72). Keep: chi2/dof <= KCHI and dof >= 4.
Outputs member predictions at 74..118 plus training-window residual stats.
"""
import itertools, json, math, sys
import numpy as np
from flint import arb
from mylsq import solve, evalc

LADDERS = {
    # name: list of decaying terms in order of inclusion
    'H': [(0.5, 0), (1, 0), (1.5, 0), (2, 0), (2.5, 0), (3, 0)],
    'HL': [(0.5, 0), (0.5, 1), (1, 0), (1, 1), (1.5, 0), (1.5, 1), (2, 0), (2, 1)],
    'I': [(1, 0), (2, 0), (3, 0), (4, 0)],
    'IL': [(1, 0), (1, 1), (2, 0), (2, 1), (3, 0), (3, 1)],
    'IL2': [(1, 0), (1, 1), (1, 2), (2, 0), (2, 1), (2, 2), (3, 0)],
    'HL2': [(0.5, 0), (0.5, 1), (0.5, 2), (1, 0), (1, 1), (1, 2), (1.5, 0), (2, 0)],
    'Hq': [(0.5, 0), (1, 0), (1, 1), (1.5, 0), (2, 0), (2, 1), (2.5, 0), (3, 0)],
}
NOND = {0: [(0, 0)], 1: [(0, 0), (0, 1)], 2: [(0, 0), (0, 1), (0, 2)], 3: [(0, 0), (0, 1), (0, 2), (0, 3)]}


def forms(nmax):
    out = []
    for nd, base in NOND.items():
        for lad, terms in LADDERS.items():
            for m in range(2, len(terms) + 1):
                t = base + terms[:m]
                if len(t) <= nmax:
                    out.append(('N%d+%s%d' % (nd, lad, m), t))
    return out


def cols_for(Ls, terms, shift=0):
    return [[(arb(L) + shift) ** (-arb(p)) * (arb(L) + shift).log() ** j for L in Ls] for p, j in terms]


def run(seq, sig, hi, Lpred, LOS=(12, 16, 20, 24, 28), KCHI=2.0, DOFMIN=4, NPMIN=4, step=2):
    """seq: dict L->value (exact), sig: dict L->sigma. Returns list of member dicts."""
    mem = []
    for lo in LOS:
        Ltr = [L for L in range(lo, hi + 1, step) if L in seq]
        y = [arb(float(seq[L])) for L in Ltr]
        w = [1.0 / sig[L] for L in Ltr]
        for name, terms in forms(len(Ltr) - DOFMIN):
            if len(terms) < NPMIN:
                continue
            cols = cols_for(Ltr, terms)
            r = solve(cols, y, w)
            z = r['res'] * np.array(w)
            dof = len(Ltr) - len(terms)
            chi = float(np.sum(z ** 2)) / dof
            pred = evalc(r['coef'], cols_for(Lpred, terms))
            mem.append(dict(name=name, lo=lo, np=len(terms), chi=chi, zmax=float(np.max(np.abs(z))),
                            res_last=float(r['res'][-1]), pred=pred))
    for m in mem:
        m['kept'] = m['chi'] <= KCHI
    return mem


def summarize(mem, Lpred, truth=None):
    K = [m for m in mem if m['kept']]
    P = np.array([m['pred'] for m in K])
    out = dict(nkept=len(K), nall=len(mem))
    if len(K) == 0:
        return out
    out['median'] = np.median(P, axis=0).tolist()
    out['p16'] = np.percentile(P, 16, axis=0).tolist(); out['p84'] = np.percentile(P, 84, axis=0).tolist()
    out['min'] = P.min(axis=0).tolist(); out['max'] = P.max(axis=0).tolist()
    out['std'] = P.std(axis=0).tolist()
    if truth is not None:
        t = np.array([truth.get(L, np.nan) for L in Lpred])
        out['err_median'] = (np.median(P, axis=0) - t).tolist()
        hr = (P.max(axis=0) - P.min(axis=0)) / 2
        out['err_over_halfrange'] = ((np.median(P, axis=0) - t) / np.where(hr > 0, hr, np.nan)).tolist()
        out['frac_in_16_84'] = float(np.nanmean((t >= out and np.array(out['p16'])) if False else ((t >= np.array(out['p16'])) & (t <= np.array(out['p84'])))))
        out['inside_minmax'] = bool(np.all((t >= P.min(axis=0)) & (t <= P.max(axis=0))))
    return out
