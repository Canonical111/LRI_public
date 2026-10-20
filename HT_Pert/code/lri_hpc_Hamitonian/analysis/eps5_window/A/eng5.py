"""eps^5 extension of implementation A's eps-jet RS/Bloch engine (ht4.py) on the package kernels.

New pieces
 * rs_multi: lockstep RS/Bloch for several model spaces (each with its own sector/cutoff mask) with
   optional order-by-order retuning of r_k, g_k on the zero-mode references p=0,1,3 (any cutoff phase).
   Optional diagonal operator jets on every state + extra jets on the model rows.  Keeps psi_1, psi_2
   and the eps^1 Rayleigh-quotient coefficients of M and V (for the linear-response assembly).
 * low_table: raw vacuum energies E_vac^(k)(x), k<=3, at every half-integer cutoff x (tiny basis).
 * dconn23: Dconn^(2), Dconn^(3) on every state from the low table (windows relative to any Lam).
 * vac_jets: vacuum energy through eps^5 at cutoff x, raw or self-consistent (with Dconn^[x] through eps^3
   acting on the vacuum's own intermediate states).
Everything float64 on lri_hpc.operators.Space; N-parity projection after each complete vertex is done
by the sector mask (applied to the summed vertex output, as in ht4.py).
"""
import sys, os, math, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'pkg'))
import numpy as np
from lri_hpc.operators import Space
from lri_hpc.solver import calibrate, vacuum_table
from ht4 import vertices_nomask, find, series_eig2

G1 = 1. / 3.


def q4(x):
    return int(math.floor(4 * x + 1e-9))


def fh(x):
    """floor to the half-integer grid"""
    return math.floor(2 * x + 1e-9) / 2


def E4(sp):
    return 4 * sp.N.astype(np.int64) + sp.P.astype(np.int64)


def mask_for(sp, Npar, Ppar, Lam):
    return (sp.N % 2 == Npar) & (sp.P % 2 == Ppar) & (E4(sp) <= q4(Lam))


def rs_multi(sp, items, K, r, g, diag=None, tune=None, keep=False, verbose=False):
    """items: list of dicts {'seeds': [idx...], 'mask': bool array, 'row': (K+1) jets or None}
    (row jets are added on every seed row, i.e. as a diagonal operator restricted to the model space).
    r, g: coupling jets (length >= K+1); entries for tuned orders are overwritten in place.
    tune: None or dict {'items': (i0, i1, i3) indices of the p=0,1,3 references, 'orders': set of k}.
    diag: (dim, K+1) jets of a diagonal operator on all states (may be None).
    Returns list of result dicts: heff (K+1,n,n), first (n,n,2) [M0, V0], spect, spc (K+1, nspect, n),
    and if keep: psi1, psi2 (scalar items) and mv1 = eps^1 Rayleigh coefficients (M, V)."""
    nI = len(items)
    st = []
    for it in items:
        seeds = it['seeds']; n = len(seeds)
        E0 = float(sp.Efree[seeds[0]])
        assert all(float(sp.Efree[s]) == E0 for s in seeds)
        par = int(sp.P[seeds[0]] % 2)
        mask = it['mask']
        den = E0 - sp.Efree
        ok = mask & (den != 0)
        spect = np.flatnonzero(mask & (den == 0))
        spect = np.array([j for j in spect if j not in seeds], dtype=np.int64)
        psi = [np.zeros((sp.dim, K + 1)) for _ in range(n)]
        for a, s in enumerate(seeds):
            psi[a][s, 0] = 1.
        heff = np.zeros((K + 1, n, n)); heff[0] = E0 * np.eye(n)
        st.append(dict(seeds=seeds, n=n, par=par, mask=mask, ok=ok, den=den, spect=spect, psi=psi, heff=heff,
                       first=np.zeros((n, n, 2)), spc=np.zeros((K + 1, max(1, len(spect)), n)),
                       m0=[None] * n, v0=[None] * n, row=it.get('row')))
    for k in range(1, K + 1):
        tuned = tune is not None and k in tune['orders']
        Ts = []
        for S in st:
            T = []
            for a in range(S['n']):
                psi = S['psi'][a]
                m, v = vertices_nomask(sp, np.ascontiguousarray(psi[:, :k]), k - 1, S['par'])
                if k == 1:
                    for b in range(S['n']):
                        S['first'][b, a] = (m[S['seeds'][b], 0], v[S['seeds'][b], 0])
                    S['m0'][a] = m[:, 0].copy(); S['v0'][a] = v[:, 0].copy()
                t = sp.F1 * psi[:, k - 1]
                for j in range(1, k + 1):
                    if j == k and tuned:
                        continue
                    if r[j] != 0.: t += r[j] * m[:, k - j]
                    if g[j] != 0.: t += g[j] * v[:, k - j]
                del m, v
                if diag is not None:
                    for j in range(1, k + 1):
                        if np.any(diag[:, j]):
                            t += diag[:, j] * psi[:, k - j]
                if S['row'] is not None:
                    t[S['seeds'][a]] += S['row'][k]
                t[~S['mask']] = 0.
                T.append(t)
            Ts.append(T)
        if tuned:
            i0, i1, i3 = tune['items']
            raw = {p: Ts[i][0][st[i]['seeds'][0]] for p, i in zip((0, 1, 3), (i0, i1, i3))}
            fM = {p: st[i]['first'][0, 0, 0] for p, i in zip((0, 1, 3), (i0, i1, i3))}
            fV = {p: st[i]['first'][0, 0, 1] for p, i in zip((0, 1, 3), (i0, i1, i3))}
            t1 = .25 if k == 0 else (-.25 if k == 1 else 0.)
            t3 = (.25 if k == 1 else 0.)
            Amat = np.array([[fM[1] - fM[0], fV[1] - fV[0]], [fM[3] - fM[0], fV[3] - fV[0]]])
            bvec = np.array([t1 - (raw[1] - raw[0]), t3 - (raw[3] - raw[0])])
            r[k], g[k] = np.linalg.solve(Amat, bvec)
            for S, T in zip(st, Ts):
                for a in range(S['n']):
                    T[a] += (r[k] * S['m0'][a] + g[k] * S['v0'][a]) * S['mask']
        for S, T in zip(st, Ts):
            n = S['n']
            for a in range(n):
                for b in range(n):
                    S['heff'][k, b, a] = T[a][S['seeds'][b]]
                if len(S['spect']):
                    S['spc'][k, :, a] = T[a][S['spect']]
            for a in range(n):
                t = T[a]
                for j in range(1, k + 1):
                    for b in range(n):
                        if S['heff'][j, b, a] != 0.:
                            t -= S['heff'][j, b, a] * S['psi'][b][:, k - j]
                S['psi'][a][:, k] = np.where(S['ok'], t / np.where(S['ok'], S['den'], 1.), 0.)
        del Ts
        if verbose:
            print(f'   order {k} done', flush=True)
    out = []
    for S in st:
        res = dict(heff=S['heff'], first=S['first'], spect=S['spect'], spc=S['spc'], seeds=S['seeds'])
        if keep and S['n'] == 1:
            psi = S['psi'][0]
            res['psi1'] = psi[:, 1].copy(); res['psi2'] = psi[:, 2].copy()
            # eps^1 Rayleigh coefficients <psi|X(eps)|psi>/<psi|psi> for X = M, V
            m, v = vertices_nomask(sp, np.ascontiguousarray(psi[:, :2]), 1, S['par'])
            s = S['seeds'][0]
            res['mv1'] = (m[s, 1] + psi[:, 1] @ m[:, 0], v[s, 1] + psi[:, 1] @ v[:, 0])
            # note: m[s,1] = (M0 psi1)_s + (M1 psi0)_s ; psi1.m[:,0] = <psi1|M0|s>  => M1_ss + 2<s|M0|psi1>
        out.append(res)
    del st
    return out


def low_table(Lint, r, g, K=3):
    """raw vacuum E_vac^(k)(x), k<=K(<=3), for x = 0, 1/2, ..., Lint (exact: 3-step paths need P,q<=4)."""
    sp = Space(Lint, 6, 4, K - 1)
    e4 = E4(sp)
    tab = {}
    for i in range(0, 2 * Lint + 1):
        x = i / 2
        mask = (sp.N % 2 == 0) & (sp.P % 2 == 0) & (e4 <= q4(x))
        res = rs_multi(sp, [dict(seeds=[0], mask=mask)], K, r, g)[0]
        tab[x] = res['heff'][:, 0, 0].copy()
    return tab


def dconn23(Efree, Lam, tab, K=5):
    """Dconn^(k) (k=2,3) = E_vac^(k)(Lam) - E_vac^(k)(Lam-E0) on every state (vector Efree), jets (dim,K+1).
    E_vac at a quarter-integer cutoff equals E_vac at its half-integer floor."""
    keys = np.array(sorted(tab)); vals = np.array([tab[x] for x in keys])
    xs = np.floor(2 * (Lam - Efree) + 1e-9) / 2
    xs = np.maximum(xs, 0.)
    idx = np.searchsorted(keys, xs)
    assert np.all(keys[idx] == xs)
    top = tab[fh(Lam)]
    out = np.zeros((len(Efree), K + 1))
    for k in (2, 3):
        out[:, k] = top[k] - vals[idx, k]
    return out


def g2D_window(Efree, Lam, g, K, sums=None, Lint=None):
    """package g(eps)^2 D(eps) jets with windows (Lam-E0, Lam] (Lam may be a quarter integer)."""
    top = int(math.floor(Lam + 1e-9))
    if sums is None:
        sums = vacuum_table(max(top, 2), K)
    up = np.clip(np.floor(Lam - Efree + 1e-9).astype(np.int64), 0, top)
    D = np.stack([-(sums[top, k] - sums[up, k]) / 6 for k in range(K + 1)], 1)
    gg = np.convolve(g[:K + 1], g[:K + 1])[:K + 1]
    out = np.zeros((len(Efree), K + 1))
    for a in range(K + 1):
        for b in range(K + 1 - a):
            if gg[a] != 0.:
                out[:, a + b] += gg[a] * D[:, b]
    return out, D


def Wwin(Efree, Lam):
    """# odd k in (Lam-E0, Lam]"""
    top = int(math.floor(Lam + 1e-9))
    lo = np.floor(Lam - Efree + 1e-9).astype(np.int64)   # k > lo
    def nodd(n):  # number of odd k in [1, n]
        n = np.maximum(n, 0)
        return (n + 1) // 2
    return nodd(top) - nodd(lo)


def vac_jets(sp, x, K, r, g, tab=None):
    """vacuum energy jets through K at cutoff x; tab given -> self-consistent (Dconn^[x] through eps^3 on
    the vacuum's intermediate states, windows relative to x), else raw."""
    mask = (sp.N % 2 == 0) & (sp.P % 2 == 0) & (E4(sp) <= q4(x))
    diag = None
    if tab is not None:
        diag = dconn23(sp.Efree, x, tab, K)
        diag[~mask] = 0.
    res = rs_multi(sp, [dict(seeds=[0], mask=mask)], K, r, g, diag=diag)[0]
    return res['heff'][:, 0, 0].copy()
