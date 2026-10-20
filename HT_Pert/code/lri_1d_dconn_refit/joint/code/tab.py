"""Helpers for the scan table (dict of numpy arrays from tabulate.py)."""
import pickle
import numpy as np
import fitcore as F
REF = F.REF
C7_ALT = F.C7_ALT
# Per-point noise of the order-n targets Y_n, from the best fits of the scan (rms * sqrt(npts/dof) of the
# lowest-residual fit with dof >= 6 at lo 24..60): windows ending at <= 92 and windows ending at 104..118.
# (Model-free finite differences give 1.2e-12, 1.4e-11, 3e-11/6e-11, 3e-9, 1.1e-7: upper bounds, inflated at
# orders 7, 8 by the smooth part at the usable difference orders.)
SIG92 = {4: 7e-13, 5: 9e-12, 6: 8e-11, 7: 8e-10, 8: 1.5e-8}
SIG118 = {4: 1e-12, 5: 1e-11, 6: 1e-10, 7: 1.1e-9}
FLOOR = 1.5          # floor-level: sigma_hat_n = rms_n sqrt(npts/dof) <= FLOOR * SIG_n, and dof_n >= DOFMIN
DOFMIN = 4
PRE = ('A', 'B', 'C', 'Dj', 'D', 'E', 'F')     # pre-registered bases (analyze_joint naming D -> Dj) plus C8-code D


# refit72: the corrected primary ('dconn') has exact but noisy S10 cluster rows at L = 46..72 (white, ~1e-13 relative:
# Y6 5x, Y7 20x, Y8 17x the quiet floor). Its floor criteria use the whitened residual rms 'erms' (residual / relative
# per-point noise, data.py noise model), which equals the plain rms for every other dataset (raw, dconn_s46, dconn_old),
# so the quiet floors SIG92/SIG118 and FLOOR keep their run1 meaning. RMSKEY='rms' gives the plain (unweighted) criteria.
import os
RMSKEY = os.environ.get('JOINT_RMSKEY', 'erms')


def load(rd, rmskey=None):
    rmskey = rmskey or RMSKEY
    T = pickle.load(open(f'{rd}/scan.pkl', 'rb'))
    N = len(T['kind'])
    reach118 = (T['kind'] == 'o7') & (T['hi'] >= 104) | (T['kind'] == 'o8') & (T['low'] == 'th118')
    for n in range(4, 9):
        if f'erms{n}' not in T:
            T[f'erms{n}'] = T[f'rms{n}']
        T[f'rmsc{n}'] = T[f'{rmskey}{n}']            # the rms used by every criterion below
        T[f'miss{n}'] = T[f'C{n}'] - REF[n]
        T[f'rel{n}'] = T[f'C{n}'] / REF[n] - 1
        T[f'dof{n}'] = T[f'npts{n}'] - T[f'ncol{n}']
        with np.errstate(invalid='ignore', divide='ignore'):
            sh = T[f'rmsc{n}'] * np.sqrt(T[f'npts{n}'] / T[f'dof{n}'])
            shp = T[f'rms{n}'] * np.sqrt(T[f'npts{n}'] / T[f'dof{n}'])
        sig = np.full(N, SIG92[n])
        if n <= 7:
            sig = np.where(reach118, SIG118[n], SIG92[n])
        T[f'fl{n}'] = sh / sig
        T[f'flp{n}'] = shp / sig
        T[f'ok{n}'] = (T[f'fl{n}'] <= FLOOR) & (T[f'dof{n}'] >= DOFMIN)
    T['ok45'] = T['ok4'] & T['ok5']
    T['ok4567'] = T['ok4'] & T['ok5'] & T['ok6'] & T['ok7']
    T['ok67'] = T['ok6'] & T['ok7']
    T['ok8all'] = T['ok4567'] & T['ok8']
    T['miss7alt'] = T['C7'] - C7_ALT
    return T


def sel(T, **kw):
    m = np.ones(len(T['kind']), bool)
    for k, v in kw.items():
        if callable(v):
            m &= v(T[k])
        elif isinstance(v, (list, tuple, set)):
            m &= np.isin(T[k], list(v))
        else:
            m &= (T[k] == v)
    return m


def q(x, p):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return float(np.percentile(x, p)) if len(x) else float('nan')


def summ(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if not len(x):
        return dict(n=0)
    return dict(n=int(len(x)), median=float(np.median(x)), p16=q(x, 16), p84=q(x, 84), min=float(x.min()), max=float(x.max()))


def fmt(s, f='%.4g'):
    if not s or s.get('n', 0) == 0:
        return 'n=0'
    return (f'n={s["n"]} med ' + f % s['median'] + ' [16-84 ' + f % s['p16'] + '..' + f % s['p84'] + '] [min-max ' + f % s['min']
            + '..' + f % s['max'] + ']')
