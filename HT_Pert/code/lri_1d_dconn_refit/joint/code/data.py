#!/usr/bin/env python3
"""Raw and fully Dconn-corrected HT tables for the joint linked fits (delta-v1 output of the previous stage).

Unified tables: L = every even cutoff 2..118; C[:, 0..8]; C8 is NaN beyond 92 (no raw C8 there). Raw C0..C7 are
thermal_d7 and raw C8 is lri_c8, exactly as in delta_v1_corrected.json ('raw' field). 'raw' and the corrected tables
are kept separate, and every order of a corrected table carries the same complete Dconn prescription (dC0..dC3 = 0;
exact dC4, dC5 at every L; exact S10 dC6..dC8 at L <= hi_exact (44); delta-v1 kept-fit curves beyond).

Corrected prescriptions (differ only in dC6..dC8 at modelled L, or, for dconn_model, also at L <= 44):
  dconn       PRIMARY. Exact dC at L <= 44; beyond, the MEAN of the floor-level delta-v1 kept fits (maxres <= QF=3 x the
              best maxres in the same training window; n = 37, 9, 13 for k = 6, 7, 8). Smooth, and it joins the exact
              values at the data noise (step at 44/46: -4e-11, -2e-9, +9e-9 for k = 6, 7, 8).
  dconn_med   As published: exact <= 44, per-L MEDIAN of all kept fits beyond. Not smooth (the median switches between
              member curves): roughness 2.3e-9 (dC6) and 2.9e-7 (dC8), 50-70x the C6 data noise.
  dconn_mean  Exact <= 44, MEAN of all kept fits beyond. Smooth, but steps at 44/46 of -6.8e-8 (dC7) and +5.6e-7 (dC8),
              ~20x and ~5x the C7/C8 noise.
  dconn_model MEAN of all kept fits at EVERY L (also L <= 44, replacing the exact S10 dC6..dC8): smooth, no step,
              deviates from the exact values at L <= 44 by the mean misfit (<= ~1e-10, 7e-8, 6e-7).
Perturbations relative to the primary (first order; the fits are linear in the data for fixed omega):
  unc{k}, typ{k}   +dC_unc_k, +dC_unc_typ_k at the modelled L (published envelope edge / typical size)
  spl{k}_i         kept fit i spliced in at the modelled L (exact kept at L <= 44): (curve_i - primary) at L > 44
  evw{k}_i         kept fit i used at every L <= 118: (curve_i - primary) at all L (no step, ignores the exact values)
  P:dconn_med, P:dconn_mean, P:dconn_model   the alternative prescriptions as perturbations of the primary
Inputs: delta_v1_corrected.json (raw values, exact flags, envelopes) and variants_full.json (regen_variants.py: the
kept fits on every L, reproduced bit-for-bit at L >= 46 from the published delta_v1_variants.json). For a rerun with
new exact S10 points: build_delta.py --extra-dconn CSV --tag T, regen_variants.py --extra-dconn CSV --published
<T>_variants.json --out <dir>/variants_full_T.json, then set DCONN_CORRECTED / DCONN_VARIANTS_FULL.
"""
import json, os, hashlib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DELTA_OUT = '<TMP>/scratchpad/dconn_refit72/delta/out'
CORR = os.environ.get('DCONN_CORRECTED', DELTA_OUT + '/delta_v1_hi72_corrected.json')
VFULL = os.environ.get('DCONN_VARIANTS_FULL', DELTA_OUT + '/variants_full_hi72.json')
QF = float(os.environ.get('DCONN_QF', '3'))
# refit72: first L of the S10 cluster rows (46..72, exact but ~2e-13 relative noise); 'dconn_s46' replaces them by the
# floor-level mean curve (trained through them), i.e. exact dC to 44 and the smooth curve from S46_FROM on.
S46_FROM = int(os.environ.get('DCONN_S46_FROM', '46'))
PRESCRIPTIONS = ('dconn', 'dconn_s46', 'dconn_med', 'dconn_mean', 'dconn_model')
SIGQ = {4: 7e-13, 5: 9e-12, 6: 8e-11, 7: 8e-10, 8: 1.5e-8}       # quiet Y_n floor (tab.SIG92, from the run1 best fits)


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def load(corr=CORR, vfull=VFULL, with_perts=True, qf=QF):
    d = json.load(open(corr))
    seq = d['sequences']
    Ls = sorted({r['L'] for r in seq['C0']})
    L = np.array(Ls, float)
    idx = {l: i for i, l in enumerate(Ls)}
    raw = np.full((len(L), 9), np.nan); med = np.full((len(L), 9), np.nan)
    unc = np.zeros((len(L), 9)); typ = np.zeros((len(L), 9)); exact = np.ones((len(L), 9), bool)
    for k in range(9):
        for r in seq[f'C{k}']:
            i = idx[r['L']]
            raw[i, k] = r['raw']; med[i, k] = r['corrected']
            unc[i, k] = r['dC_unc']; typ[i, k] = r['dC_unc_typ']; exact[i, k] = r['exact']
            assert abs(r['raw'] + r['dC'] - r['corrected']) <= 1e-12 * max(1, abs(r['corrected'])), (k, r)
    V = json.load(open(vfull))
    out = dict(L=L, raw=raw, dconn_med=med, unc=unc, typ=typ, exact=exact, tag=d.get('tag'), qf=qf,
               extra_dconn_csv=d.get('extra_dconn_csv'),
               sources=dict(corrected=corr, corrected_sha256=sha(corr), variants_full=vfull, variants_full_sha256=sha(vfull)))
    prim = med.copy(); mean = med.copy(); model = med.copy()
    s46cols = {}
    curves = {}
    info = {}
    for k in (6, 7, 8):
        b = V[f'dC{k}']
        Lv = b['L']; P = np.array(b['pred']); mr = np.array(b['maxres'])
        lo = np.array([int(s.split('lo=')[1].split('|')[0]) for s in b['labels']])
        best = {l: mr[lo == l].min() for l in set(lo)}
        floor = np.array([mr[i] <= qf * best[lo[i]] for i in range(len(mr))])
        # map curves onto the table
        C = np.full((P.shape[0], len(L)), np.nan)
        for j, l in enumerate(Lv):
            if l in idx:
                C[:, idx[l]] = P[:, j]
        mod = ~exact[:, k] & np.isfinite(med[:, k])          # modelled points of this order
        have = np.isfinite(raw[:, k])
        assert np.all(np.isfinite(C[:, mod])), 'variants do not cover the modelled points'
        exact_dc = med[:, k] - raw[:, k]                       # exact dC where exact
        # sanity: published median == median of curves at the modelled points
        assert np.allclose(np.median(C[:, mod], axis=0), exact_dc[mod], rtol=0, atol=4e-16 * np.nanmax(np.abs(raw[:, k]))), k
        prim[mod, k] = raw[mod, k] + C[floor][:, mod].mean(axis=0)
        cl = exact[:, k] & (L >= S46_FROM) & np.isfinite(raw[:, k])     # exact S10 cluster rows (refit72)
        s46k = prim[:, k].copy(); s46k[cl] = raw[cl, k] + C[floor][:, cl].mean(axis=0)
        s46cols[k] = s46k
        mean[mod, k] = raw[mod, k] + C[:, mod].mean(axis=0)
        model[have, k] = raw[have, k] + C[:, have].mean(axis=0)
        curves[k] = (C, floor, mod, have)
        info[k] = dict(n_kept=int(P.shape[0]), n_floor=int(floor.sum()), hi_exact=b['hi_exact'],
                       step_primary=float(C[floor][:, idx[b['hi_exact']]].mean() - exact_dc[idx[b['hi_exact']]]),
                       step_mean=float(C[:, idx[b['hi_exact']]].mean() - exact_dc[idx[b['hi_exact']]]))
    s46 = prim.copy()
    for k in (6, 7, 8):
        s46[:, k] = s46cols[k]
    out.update(dconn=prim, dconn_s46=s46, dconn_mean=mean, dconn_model=model, info=info)
    # refit72 noise model of the primary: the exact S10 cluster rows (L >= S46_FROM, exact) carry white noise; its size
    # per order is the rms of (exact - floor-mean curve) there. sigx: data noise of C_k(L); wrel: relative noise of the
    # fit target Y_n(L) = C_n + sum_j e_j C_{n-j} (ext omegas, shift 0) against the quiet floor SIGQ (tab.SIG92).
    cl = np.zeros(len(L), bool)
    for k in (6, 7, 8):
        cl |= exact[:, k] & (L >= S46_FROM) & np.isfinite(raw[:, k])
    dC = np.nan_to_num(prim - s46)                     # the noise realization (zero off the cluster rows and for k <= 5)
    sigx = {k: np.where(cl, float(np.sqrt(np.mean(dC[cl, k] ** 2))) if cl.any() else 0., 0.) for k in (6, 7, 8)}
    om = [0., 3.5, -29.552388360629354, 556.2011107308521, -13455.32792429696, 376987.01090272394, 0., 0., 0.]
    ell = np.log(L)
    e = [np.ones_like(ell)]
    for n in range(1, 7):
        e.append(ell / n * sum(j * om[j] * e[n - j] for j in range(1, n + 1)))
    wrel, s10Y = {}, {}
    for n in range(4, 9):
        dY = dC[:, n] + sum(e[j] * dC[:, n - j] for j in range(1, n - 1))
        s10Y[n] = float(np.sqrt(np.mean(dY[cl] ** 2))) if cl.any() else 0.
        wrel[n] = np.where(cl, np.sqrt(1. + (s10Y[n] / SIGQ[n]) ** 2), 1.)
    out.update(sigx=sigx, wrel=wrel, noise_model=dict(cluster_L=[int(x) for x in L[cl]], sigx={k: float(v.max()) for k, v in sigx.items()},
                                                    s10Y=s10Y, SIGQ=SIGQ, wrel={n: float(w.max()) for n, w in wrel.items()}))
    if with_perts:
        perts = {}
        for k in (6, 7, 8):
            a = np.zeros((len(L), 9)); a[:, k] = unc[:, k]; perts[f'unc{k}'] = a
            b_ = np.zeros((len(L), 9)); b_[:, k] = typ[:, k]; perts[f'typ{k}'] = b_
            C, floor, mod, have = curves[k]
            for i in range(C.shape[0]):
                a = np.zeros((len(L), 9)); a[mod, k] = raw[mod, k] + C[i, mod] - prim[mod, k]
                perts[f'spl{k}_{i}'] = a
                b_ = np.zeros((len(L), 9)); b_[have, k] = raw[have, k] + C[i, have] - prim[have, k]
                perts[f'evw{k}_{i}'] = b_
        # refit72: seam-anchored kept curves 'anc{k}_i' = spl_i minus its offset at the last exact L (curve_i(hi) - floor-mean(hi)):
        # the continuation-shape difference without the seam step (the hi=72 kept curves misfit the noisy exact rows by up to
        # ~1e-5 (dC7) / 1e-4 (dC8) at L=72, so spl_i carries a step at 72/74 to which order-7/8 fits are very sensitive);
        # 'stp{k}' = unit step (+1 at every modelled L of order k)
        for k in (6, 7, 8):
            C, floor, mod, have = curves[k]
            i0 = idx[info[k]['hi_exact']]
            fm = C[floor].mean(axis=0)
            for i in range(C.shape[0]):
                a = np.zeros((len(L), 9)); a[mod, k] = (C[i, mod] - C[i, i0]) - (fm[mod] - fm[i0])
                perts[f'anc{k}_{i}'] = a
            a = np.zeros((len(L), 9)); a[mod, k] = 1.; perts[f'stp{k}'] = a
        for p in ('dconn_med', 'dconn_mean', 'dconn_model', 'dconn_s46'):
            a = np.nan_to_num(out[p] - prim); a[:, :6] = 0.; perts['P:' + p] = a
        out['perts'] = perts
        out['floor_idx'] = {k: [i for i in range(curves[k][0].shape[0]) if curves[k][1][i]] for k in (6, 7, 8)}
    return out


if __name__ == '__main__':
    from math import comb

    def sig(y):
        s = {kk: float(np.sqrt(np.mean(np.diff(y, kk) ** 2)) / np.sqrt(comb(2 * kk, kk))) for kk in range(3, min(len(y) - 3, 22))}
        return min(s.values())
    D = load()
    L = D['L']
    print('tag', D['tag'], 'QF', D['qf'], 'nL', len(L), 'info', json.dumps(D['info']))
    for p in PRESCRIPTIONS:
        for k in (6, 7, 8):
            m = np.isfinite(D[p][:, k])
            dc = D[p][m, k] - D['raw'][m, k]
            w = (L[m] >= 24) & (L[m] <= 70)
            print(f'{p:12s} dC{k} at 44/46/92/118: ' + ' '.join(f'{float(dc[L[m] == x][0]):+.9f}' if (L[m] == x).any() else '-' for x in (44, 46, 92, 118))
                  + f'  roughness(24..70) {sig(dc[w]):.1e}')
    print('n perts', len(D['perts']))
    print('noise model', json.dumps(D['noise_model']))
