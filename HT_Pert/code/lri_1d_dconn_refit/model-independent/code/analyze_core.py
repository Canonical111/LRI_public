#!/usr/bin/env python3
"""Aggregate the model-independent lens (float64 post-processing of the 50-digit grid; runs in seconds).

Selection (identical to the earlier raw-data lens): adequate at order n if maxres <= FAC * floor(n) and the
noise-propagated intercept error gain * floor/2 <= NOISE * |c| (own estimate as scale; no reference used);
floor(n) = 5th percentile of maxres over the family at that hi. A configuration is 'calibrated' for C8 if it is
adequate at n = 8 and |b_n| < BMAX at every n = 4..7, b_n = (c_n - ref_n)/|ref_n| (labelled calibration step).
Calibrated C8 = c8 * (1 - mean_{n=4..7} b_n). For C4..C7 a held-out version of the same rule uses only lower orders
(n = 3..n-1; C4 from b3 alone).
Delta-model propagation: every kept delta-model fit (dC6: 86, dC7: 57, dC8: 62 sequences) and the +-envelope edges are
pushed through the stored 50-digit intercept weights (exactly linear for fixed design, omegas and limits), with the
selection held fixed; calibration biases are recomputed with the shifted b6, b7.
usage: imported by analyze.py / members_analyze.py (RUNDIR = sys.argv[1])
"""
import sys, os, json, itertools, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

RUN = sys.argv[1]
FAC = float(os.environ.get('MI_FAC', 10)); NOISE = float(os.environ.get('MI_NOISE', 1e-4))
BMAX = float(os.environ.get('MI_BMAX', 1e-3))
LIGHT = bool(os.environ.get('MI_LIGHT'))          # families table only (for the member reruns)
LOS_KEEP = [int(x) for x in os.environ['MI_LOS'].split(',')] if os.environ.get('MI_LOS') else None
OUTNAME = os.environ.get('MI_OUT', 'analysis')
GUESS = {4: 0.0803, 5: 0.717, 6: 2.3, 7: 2.8, 8: 84.0}
EARLIER = dict(  # earlier raw-data model-independent lens (workflow wf_d568c208-924), for comparison
    C8_HT_median=8063670, C8_HT_range=[8062254, 8066318], C8_HT_corr=8065958, C8_phys=8066040, N=19,
    bias_x1e3={4: -0.12, 5: -0.25, 6: -0.28, 7: -0.31},
    lower_median={4: 45.33935, 5: -732.0390, 6: 14325.33, 7: -322652},
    neville=[8058572, 8058993], bst=[8058368, 8058716], vac=8066177)

G = json.load(open(os.path.join(RUN, 'grid.json')))
D = load_corrected()
V = load_variants()
OUT = {}
# refit72 addition: the post-processing must use the same data file and smooth central as the grid run (checked).
if not os.environ.get('MI_SKIP_CENTRAL_CHECK'):
    assert G['meta'].get('tag') == D['tag'], 'analysis data tag %s != grid data tag %s' % (D['tag'], G['meta'].get('tag'))
    _gm = G['meta'].get('central_members') or {}
    _dm = D.get('central_members') or {}
    assert sorted(int(k) for k in _gm) == sorted(_dm), 'central members differ: grid %s, analysis %s' % (_gm, _dm)
    for _k, _v in _gm.items():
        assert _dm[int(_k)]['member'] == _v['member'], 'central member differs at k=%s: grid %s, analysis %s' % (_k, _v, _dm[int(_k)])

# ----------------------------------------------------------------------------------------------- index the grid
R = collections.defaultdict(lambda: collections.defaultdict(dict))
W = {}
for res in G['results']:
    c = res['cfg']; key3 = (c['tails'], c['lead'], c['lo']); hi = c['hi']
    if LOS_KEEP and c['lo'] not in LOS_KEEP:
        continue
    W[key3 + (hi,)] = res['weights']
    for r in res['rows']:
        R[(r['kind'], r['mode'], r['level'], r['om'], hi)][key3][r['n']] = r
# the effective-omega chain starts at n=5; orders 3, 4 are identical to the wf family (no omega3+ enters there)
for fam in list(R):
    if fam[3].endswith('_eff'):
        base = (fam[0], fam[1], fam[2], fam[3][:-4], fam[4])
        for key in R[fam]:
            for n in (3, 4):
                if n in R[base].get(key, {}):
                    R[fam][key][n] = R[base][key][n]
VARRES = {}
for res in G['results']:
    c = res['cfg']
    for v in res['varres']:
        VARRES[(c['tails'], c['lead'], c['lo'], c['hi'], v['k'], v['var'], v['level'], v['n'])] = v


def target(kind, mode, n):
    return REF[n] - (GUESS[n] if (mode == 'H' and n >= 4) else 0.0)


def floors(fam):
    F = R[fam]; fl = {}
    for n in range(2, 9):
        v = [F[k][n]['maxres'] for k in F if n in F[k]]
        if v:
            fl[n] = float(np.percentile(v, 5))
    return fl


def adequate(row, fl):
    f = fl[row['n']]
    return row['maxres'] <= FAC * f and row['gain'] * 0.5 * f <= NOISE * abs(row['c'])


def bias(fam, key, n, cvals=None):
    kind, mode = fam[0], fam[1]
    if cvals is not None:
        c = cvals.get((key, n))
    else:
        c = R[fam][key][n]['c'] if n in R[fam][key] else None
    if c is None:
        return float('nan')
    t = target(kind, mode, n)
    return (c - t) / abs(t)


def c8_family(fam, cvals=None, sel=None, rule='mean47'):
    """C8 statistics of a family. cvals: optional dict (key,n)->shifted intercept (selection kept fixed)."""
    F = R[fam]; fl = floors(fam)
    if sel is None:
        adq = [k for k in F if 8 in F[k] and adequate(F[k][8], fl)]
        cal = [k for k in adq if all(j in F[k] and abs(bias(fam, k, j)) < BMAX for j in range(4, 8))]
        sel = dict(adq=adq, cal=cal)
    get = (lambda k, n: cvals[(k, n)]) if cvals is not None else (lambda k, n: F[k][n]['c'])
    adq, cal = sel['adq'], sel['cal']
    out = dict(N_adequate=len(adq), N_cal=len(cal))
    if adq:
        out['all_adequate_median'] = float(np.median([get(k, 8) for k in adq]))
    if cal:
        c8 = np.array([get(k, 8) for k in cal])
        B = np.array([[bias(fam, k, j, cvals) for j in range(3, 8)] for k in cal])   # columns n=3..7
        corr = {}
        corr['mean47'] = c8 * (1 - B[:, 1:].mean(axis=1))
        corr['mean37'] = c8 * (1 - np.nanmean(B, axis=1))
        corr['b7'] = c8 * (1 - B[:, 4])
        corr['mean67'] = c8 * (1 - B[:, 3:].mean(axis=1))
        ns = np.arange(4, 8)
        lin = []
        for row in B[:, 1:]:
            a, b0 = np.polyfit(ns, row, 1); lin.append(a * 8 + b0)
        corr['lintrend47'] = c8 * (1 - np.array(lin))
        out.update(uncal_median=float(np.median(c8)), uncal_range=[float(c8.min()), float(c8.max())],
                   uncal_p10_p90=[float(np.percentile(c8, 10)), float(np.percentile(c8, 90))],
                   cal_median=float(np.median(corr['mean47'])),
                   cal_range=[float(corr['mean47'].min()), float(corr['mean47'].max())],
                   cal_alt={r: float(np.median(v)) for r, v in corr.items()},
                   bias_median_x1e3={n: float(np.nanmedian(B[:, n - 3]) * 1e3) for n in range(3, 8)},
                   bias_absmax_x1e3={n: float(np.nanmax(abs(B[:, n - 3])) * 1e3) if np.isfinite(B[:, n - 3]).any() else None for n in range(3, 8)})
    return out, sel


def lower_family(fam, n, cvals=None, sel=None):
    """C_n (n=3..7) statistics: adequate configurations; held-out calibration from lower orders."""
    F = R[fam]; fl = floors(fam)
    get = (lambda k, m: cvals[(k, m)]) if cvals is not None else (lambda k, m: F[k][m]['c'])
    if sel is None:
        adq = [k for k in F if n in F[k] and adequate(F[k][n], fl)]
        low = list(range(3, n)) if n >= 4 else []
        low4 = [j for j in low if j >= 4] or low
        cal = [k for k in adq if low4 and all(j in F[k] and abs(bias(fam, k, j)) < BMAX for j in low4)]
        sel = dict(adq=adq, cal=cal, low4=low4)
    adq, cal, low4 = sel['adq'], sel['cal'], sel['low4']
    out = dict(N_adequate=len(adq), N_cal=len(cal))
    if adq:
        c = np.array([get(k, n) for k in adq])
        out.update(median=float(np.median(c)), range=[float(c.min()), float(c.max())],
                   p10_p90=[float(np.percentile(c, 10)), float(np.percentile(c, 90))],
                   rel_median_x1e3=float((np.median(c) - target(fam[0], fam[1], n)) / abs(target(fam[0], fam[1], n)) * 1e3))
    if cal:
        c = np.array([get(k, n) for k in cal])
        bl = np.array([np.mean([bias(fam, k, j, cvals) for j in low4]) for k in cal])
        cc = c - bl * np.abs(c)          # b = (c - ref)/|ref|  ->  ref ~ c - b |c|  (sign-safe for negative C_n)
        out.update(heldout_lower=low4, cal_uncal_median=float(np.median(c)), cal_median=float(np.median(cc)),
                   cal_range=[float(cc.min()), float(cc.max())],
                   cal_rel_x1e3=float((np.median(cc) - target(fam[0], fam[1], n)) / abs(target(fam[0], fam[1], n)) * 1e3))
    return out, sel


# ----------------------------------------------------------------------------------------------- families
FAMS = {
    'LSQ-full E wf (primary)': ('dconn', 'E', 'full', 'wf'),
    'LSQ-full E raw-omega': ('dconn', 'E', 'full', 'raw'),
    'LSQ-full3 E wf (+l^2 T2)': ('dconn', 'E', 'full3', 'wf'),
    'LSQ-full3 E raw-omega': ('dconn', 'E', 'full3', 'raw'),
    'LSQ-lev2 E wf (omega1,2 only)': ('dconn', 'E', 'lev2', 'wf'),
    'LSQ-free E (omega-free)': ('dconn', 'E', 'free', 'wf'),
    'LSQ-full E wf_eff (fitted omega3-5)': ('dconn', 'E', 'full', 'wf_eff'),
    'LSQ-full S wf (self-consistent)': ('dconn', 'S', 'full', 'wf'),
    'LSQ-full3 S wf (self-consistent)': ('dconn', 'S', 'full3', 'wf'),
    'RAW LSQ-full H (earlier lens reproduction)': ('raw', 'H', 'full', 'raw'),
    'RAW LSQ-full E (naive exact limits)': ('raw', 'E', 'full', 'raw'),
    'RAW LSQ-full3 E': ('raw', 'E', 'full3', 'raw'),
    'RAW LSQ-full S': ('raw', 'S', 'full', 'raw'),
}
FLOORS = {}
TAB = {}
for name, f4 in FAMS.items():
    for hi in (44, 60, 72, 92, 118):
        fam = f4 + (hi,)
        if fam not in R:
            continue
        FLOORS['%s|hi%d' % (name, hi)] = floors(fam)
        ent = {}
        if hi <= 92:
            ent['C8'], _ = c8_family(fam)
        for n in range(3, 8):
            ent['C%d' % n], _ = lower_family(fam, n)
        TAB['%s|hi%d' % (name, hi)] = ent
OUT['families'] = TAB
OUT['floors'] = FLOORS
OUT['meta'] = G['meta']
