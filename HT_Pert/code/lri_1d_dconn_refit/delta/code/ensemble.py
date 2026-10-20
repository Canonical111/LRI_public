"""Ensemble rule for extrapolating a window-shift sequence F(L) beyond the largest exact cutoff.

Rule 'delta-v1' (fixed before the final dC6..dC8 numbers were produced; parameters below):
  * models: non-decaying log polynomial N1 (c+ l), N2 (+ l^2), N3 (+ l^3), l = log L, times every tail set in
    fitlib.TAILS (half-integer and integer powers with logs); shifts s in SHIFTS (l = log(L+s), powers of L+s);
  * windows lo..hi with lo in LOS, hi = largest contiguous exact cutoff; every even L in the window;
  * keep fits with NPMIN <= npar <= n - DOFMIN and max residual <= Q * (best max residual in that window);
  * central value = median of kept predictions; spread = (max - min)/2 of kept predictions at each L;
  * quoted uncertainty = KAPPA * spread + NOISE (KAPPA calibrated on validation sequences, see validate_rule.py).
"""
import numpy as np
from fitlib import fit, all_models

RULE = dict(LOS=(10, 12, 14, 16), SHIFTS=(0,), NPMIN=6, DOFMIN=4, Q=100.0, NONDEC=('N1', 'N2', 'N3'))


def ensemble(seq, hi, Lpred, rule=RULE, step=2, models=None, keep_all=False):
    """seq: dict L -> value (exact). Train on even L in [lo, hi] (stride `step`). Returns dict."""
    models = models or all_models(nondec=rule.get('NONDEC', ('N1', 'N2', 'N3')))
    fits = []
    for lo in rule['LOS']:
        Ltr = [L for L in sorted(seq) if lo <= L <= hi and (L - lo) % step == 0]
        cand = []
        for s in rule['SHIFTS']:
            for mname, terms in models:
                if len(terms) < rule['NPMIN'] or len(terms) > len(Ltr) - rule['DOFMIN']:
                    continue
                f = fit(Ltr, [seq[L] for L in Ltr], terms, shift=s)
                cand.append(dict(model=mname, lo=lo, shift=s, npar=len(terms), n=len(Ltr), maxres=f['maxres'],
                                 cond=f['cond'], pred=np.array([f['predict'](L) for L in Lpred])))
        if not cand:
            continue
        best = min(c['maxres'] for c in cand)
        for c in cand:
            c['kept'] = c['maxres'] <= rule['Q'] * best
        fits.extend(cand)
    kept = [c for c in fits if c['kept']]
    if not kept:
        return None
    P = np.array([c['pred'] for c in kept])
    out = dict(Lpred=list(Lpred), n_kept=len(kept), n_all=len(fits),
               median=np.median(P, axis=0), lo=P.min(axis=0), hi=P.max(axis=0),
               spread=(P.max(axis=0) - P.min(axis=0)) / 2, std=P.std(axis=0),
               kept=[(c['model'], c['lo'], c['shift'], c['npar'], c['maxres']) for c in kept],
               preds=P)
    if keep_all:
        out['fits'] = fits
    return out
