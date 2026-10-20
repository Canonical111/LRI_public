"""Model-independent lens on the fully window-corrected (Dconn) HT thermal coefficients.

Shared definitions: data loading (corrected and raw kept separate), reference values (comparison/calibration only),
gap-omega sets, high-precision e-subtraction and least-squares machinery.

Data:   DCONN_CORRECTED (default: ../../delta/out/delta_v1_corrected.json) -> per order k, per even L:
        raw, dC, corrected = raw + dC (here recomputed in mp as mpf(raw) + mpf(dC)), exact flag.
        DCONN_VARIANTS  (default: ../../delta/out/delta_v1_variants.json) -> every kept delta-model fit's dC_k(L)
        prediction for k = 6, 7, 8 at the modelled L (used only for error propagation).
Both paths can be overridden by environment variables so the whole lens reruns on a rebuilt delta model
(e.g. after the S10 cluster points L = 46..72 replace modelled shifts: build_delta.py --extra-dconn CSV --tag new).
"""
import os, json, math
import numpy as np
import mpmath as mp

HERE = os.path.dirname(os.path.abspath(__file__))
DELTA_OUT = os.path.normpath(os.path.join(HERE, '..', '..', 'delta', 'out'))
CORR_PATH = os.environ.get('DCONN_CORRECTED', os.path.join(DELTA_OUT, 'delta_v1_corrected.json'))
VAR_PATH = os.environ.get('DCONN_VARIANTS', os.path.join(DELTA_OUT, 'delta_v1_variants.json'))

DPS = int(os.environ.get('MI_DPS', '50'))
mp.mp.dps = DPS

# ----------------------------------------------------------------------------- references (never fit targets)
A_mp = mp.pi + 4 * mp.log(2)
C2_mp = A_mp / 9
C3_mp = (mp.pi ** 2 + 6 * mp.pi * mp.log(2) + 12 * mp.log(2) ** 2 - 6 * mp.gamma(mp.mpf(1) / 4) ** 4 / mp.pi) / 81
REF = {2: float(C2_mp), 3: float(C3_mp), 4: 45.42488010356, 5: -731.13947662454, 6: 14331.68703277,
       7: -322550.0, 8: 8066723.0}
REF_ERR = {2: 0.0, 3: 0.0, 4: 1e-11, 5: 1e-11, 6: 4.9e-7, 7: 41.0, 8: 8015.0}
REF7_POSTHOC = (-322524.0, 38.0)   # post hoc truncation-aware C7 (comparison only)
REF8_QUOTED = 33000.0               # quoted allowance of the diagrammatic C8

# ----------------------------------------------------------------------------- gap omega sets
# raw-HT gap exponents ('extended' set of the HT note, Table gap): omega2 = -5A + 1/54 contains the raw window shift.
OM_RAW = {1: mp.mpf('3.5'), 2: -5 * A_mp + mp.mpf(1) / 54, 3: mp.mpf('556.2011107308521'),
          4: mp.mpf('-13455.32792429696'), 5: mp.mpf('376987.01090272394')}
# window-free exponents for Dconn-corrected data: omega2 = -5A (continuum), omega3 shifted by the Dconn window shift
# delta omega3 = -(2A+3)/81 + 1/27 = -0.14603 (g2D part -(2A+3)/81 plus the g^3 W bubble +1/27); omega4, omega5: raw
# values (their window shifts are unknown; a +-1, +-10 sensitivity is reported).
DOM3_DCONN = -(2 * A_mp + 3) / 81 + mp.mpf(1) / 27
OM_WF = {1: mp.mpf('3.5'), 2: -5 * A_mp, 3: OM_RAW[3] + DOM3_DCONN, 4: OM_RAW[4], 5: OM_RAW[5]}
OMSETS = {'wf': OM_WF, 'raw': OM_RAW}


# ----------------------------------------------------------------------------- data
def load_corrected(path=None):
    """Returns dict with Ls (per order), raw[k][L], dC[k][L], exact[k][L], corr[k][L] (mpf), unc[k][L]."""
    path = path or CORR_PATH
    d = json.load(open(path))
    S = d['sequences']
    out = dict(raw={}, dC={}, corr={}, exact={}, unc={}, unc_typ={}, path=path, tag=d.get('tag'))
    for k in range(9):
        rows = S['C%d' % k]
        out['raw'][k] = {r['L']: r['raw'] for r in rows}
        out['dC'][k] = {r['L']: r['dC'] for r in rows}
        out['exact'][k] = {r['L']: bool(r['exact']) for r in rows}
        out['unc'][k] = {r['L']: r['dC_unc'] for r in rows}
        out['unc_typ'][k] = {r['L']: r['dC_unc_typ'] for r in rows}
    out['central_rule'] = 'pointwise-median (delta_v1 as published)'
    rule = os.environ.get('DCONN_CENTRAL', 'medoid')
    if rule != 'median':
        smooth_central(out, rule)
    return out


def smooth_central(D, rule='medoid'):
    """Replace the modelled dC_k (k = 6, 7, 8) by ONE smooth kept delta-model fit.
    The published central is the pointwise median of the kept fits, which switches member from L to L and is not smooth
    (6th differences up to 13x those of any member for dC8); its kinks (~1e-7..1e-4) inflate the C6..C8 residual floors
    16-55x at hi = 92. 'medoid' picks the member closest to the pointwise median (rms of (pred - median)/unc over the
    modelled L); 'k6:i,k7:j,k8:l' picks explicit members (indices into the variants file) for a nonlinear rerun."""
    V = load_variants()
    pick = {}
    if rule != 'medoid':
        for part in rule.split(','):
            kk, ii = part.split(':'); pick[int(kk[1:])] = int(ii)
    info = {}
    for k in (6, 7, 8):
        Lm = [L for L in V[k]['L'] if L in D['dC'][k] and not D['exact'][k][L]]
        if not Lm:
            continue
        idx = [V[k]['L'].index(L) for L in Lm]
        P = V[k]['pred'][:, idx]
        cen = np.array([D['dC'][k][L] for L in Lm]); unc = np.array([D['unc'][k][L] for L in Lm])
        dist = np.sqrt(np.mean(((P - cen) / unc) ** 2, axis=1))
        i = pick.get(k, int(np.argmin(dist)))
        for a, L in enumerate(Lm):
            D['dC'][k][L] = float(P[i, a])
        info[k] = dict(member=i, label=V[k]['labels'][i], rms_dist_over_unc=float(dist[i]), member_maxres=float(V[k]['maxres'][i]))
    D['central_rule'] = rule
    D['central_members'] = info


def load_variants(path=None):
    path = path or VAR_PATH
    v = json.load(open(path))
    out = {}
    for key, ent in v.items():
        k = int(key[2:])
        out[k] = dict(L=list(ent['L']), labels=ent['labels'], pred=np.array(ent['pred'], float),
                      maxres=np.array(ent['maxres'], float))
    return out


def table(D, kind, Lmax=None):
    """Build per-L rows of C0..C8 as mpf for kind in {'dconn','raw'}. Returns Ls (ints, ascending, all orders 0..7
    present) and dict L -> list of 9 mpf (C8 = None where absent)."""
    Ls = sorted(D['raw'][7])
    rows = {}
    alt = None
    if os.environ.get('RAW_C07') == 'lri_c8':
        # check variant: raw C0..C7 from the lri_c8 code (the C8 code's own lower orders, L <= 92) instead of thermal_d7
        alt = json.load(open(os.environ.get('HT_DATA_JSON', '<PROJECT>/lri_ht_c8_symmetry/results/'
                                            '2026-10_symmetry/extrapolation/data.json')))['raw']
    for L in Ls:
        if Lmax and L > Lmax:
            continue
        r = []
        for k in range(9):
            if L not in D['raw'][k]:
                r.append(None); continue
            v = mp.mpf(D['raw'][k][L])
            if alt is not None and k <= 7 and str(L) in alt:
                v = mp.mpf(alt[str(L)][k])
            if kind == 'dconn':
                v = v + mp.mpf(D['dC'][k][L])
            r.append(v)
        rows[L] = r
    return sorted(rows), rows


# ----------------------------------------------------------------------------- e-subtraction
def eseries(l, w, kmax):
    """e_k(l) = [eps^k] exp(l sum_j w_j eps^j);  w: dict j -> value (missing = 0)."""
    e = [mp.mpf(1)]
    for k in range(1, kmax + 1):
        s = mp.mpf(0)
        for j in range(1, k + 1):
            wj = w.get(j, 0)
            if wj:
                s += j * wj * e[k - j]
        e.append(l * s / k)
    return e


def omegas_for(level, n, omset):
    """Omegas used in the e-subtraction at target order n.
    'full'/'full3': omega_1..omega_{n-3} fixed, omega_{n-2} free (l*T2 column);
    'lev2': only omega_1, omega_2 fixed (free l^k T2 columns stand in for the rest);
    'free': none fixed (l^0..l^{n-2} T2 columns);  'all': omega_1..omega_{n-2} fixed (n<=7 only)."""
    om = OMSETS[omset] if isinstance(omset, str) else omset
    if level in ('full', 'full3'):
        return {j: om[j] for j in range(1, n - 2)}
    if level == 'lev2':
        return {j: om[j] for j in (1, 2) if j <= n - 2}
    if level == 'free':
        return {}
    if level == 'all':
        return {j: om[j] for j in range(1, n - 1)}
    raise ValueError(level)


def nlead(level, n):
    m = n - 2
    if level == 'full':
        return 2
    if level == 'full3':
        return 3
    if level == 'lev2':
        return m // 3 + 1
    if level == 'free':
        return m + 1
    if level == 'all':
        return 1
    raise ValueError(level)


def ssub(Ls, rows, n, w, lims):
    """S_n(L) = C_n(L) + sum_{j=1}^{n-2} e_j(log L) (C_{n-j}(L) - lim_{n-j})  (mp list)."""
    S = []
    for L in Ls:
        r = rows[L]
        e = eseries(mp.log(L), w, n - 2)
        s = r[n]
        for j in range(1, n - 1):
            s += e[j] * (r[n - j] - lims[n - j])
        S.append(s)
    return S


def ssub_delta(Ls, dcols, n, w, dlims=None):
    """Linear response of S_n to shifts dC_k(L) (float arrays per order k, aligned with Ls) and to shifts of the lower
    limits (dlims: dict k -> float). Float64 (the shifts are small, the e_j are O(10^3))."""
    out = np.zeros(len(Ls))
    for a, L in enumerate(Ls):
        e = [float(x) for x in eseries(mp.log(L), w, n - 2)]
        s = dcols[n][a] if n in dcols else 0.0
        for j in range(1, n - 1):
            k = n - j
            dk = (dcols[k][a] if k in dcols else 0.0) - (dlims.get(k, 0.0) if dlims else 0.0)
            s += e[j] * dk
        out[a] = s
    return out


# ----------------------------------------------------------------------------- tails and designs
def tails(pmin, pmax, J):
    t = []
    for q in range(int(round(2 * pmin)), int(round(2 * pmax)) + 1):
        p = q / 2
        for j in range(J + 1):
            t.append((p, j))
    return t


TAILSETS = [('p%s_J%d' % (pmax, J), tails(1, pmax, J)) for pmax in (1.5, 2, 2.5, 3) for J in (0, 1, 2, 3)]


def design(Ls, rows, terms, lead, nl):
    X = []
    for L in Ls:
        Lm = mp.mpf(L); z = mp.log(Lm)
        base = (rows[L][2] - C2_mp) if lead == 'T2' else Lm ** mp.mpf(-0.5)
        X.append([mp.mpf(1)] + [base * z ** k for k in range(nl)] + [Lm ** (-mp.mpf(p)) * z ** j for p, j in terms])
    return mp.matrix(X)


class MPDesign:
    """Column-scaled QR least squares at DPS digits. w = intercept row of the pseudo-inverse (data weights)."""

    def __init__(self, X):
        self.X = X
        nr, nc = X.rows, X.cols
        sc = [mp.sqrt(mp.fsum(X[i, j] ** 2 for i in range(nr))) for j in range(nc)]
        self.sc = sc
        Xs = mp.matrix(nr, nc)
        for i in range(nr):
            for j in range(nc):
                Xs[i, j] = X[i, j] / sc[j]
        Q, R = mp.qr(Xs, mode='skinny')
        Rinv = mp.inverse(R)
        self.P = Rinv * Q.T
        self.w = [self.P[0, i] / sc[0] for i in range(nr)]
        self.gain = float(mp.fsum(abs(v) for v in self.w))
        try:
            sv = mp.svd_r(R, compute_uv=False)
            self.cond = float(max(sv) / min(sv))
        except Exception:
            self.cond = float('nan')

    def solve(self, y):
        yv = mp.matrix(y)
        ps = self.P * yv
        p = [ps[j] / self.sc[j] for j in range(len(self.sc))]
        res = self.X * mp.matrix(p) - yv
        return p, max(abs(res[i]) for i in range(len(y)))


def rel(c, n, ref=None):
    r = REF[n] if ref is None else ref
    return (c - r) / abs(r)
