"""Generic eps-jet Rayleigh-Schroedinger / Bloch machinery on the package kernels.

Extends analysis/eh_review/theory/desc3.py (scalar RS through eps^3) to
 * block (Bloch) RS with a degenerate model space (matrix H_eff jets);
 * an arbitrary allowed-state mask (sector parity AND/OR a reduced cutoff L'<=L,
   L' may be a quarter integer) -> vacuum energy series E_vac(L');
 * an arbitrary diagonal operator jet added to H (g^2 D, or Dfull);
 * eps^4 (psi through eps^3).
Everything is float64 on lri_hpc.operators.Space (ranked basis + ladder kernels).
H = H0 + eps F1 + r(eps) M + g(eps) V (+ diag), N-parity projection after each
complete vertex (applied to the summed vertex output, which is equivalent).
"""
import sys, os, math, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'pkg'))
import numpy as np
from lri_hpc.operators import Space
from lri_hpc.solver import calibrate, vacuum_table


def vertices_nomask(sp, psi, degree, parity):
    """Package Horner factorization of M and V (9 ladder sweeps), WITHOUT the
    N-even mask (caller applies its own sector mask). parity = P-parity of psi."""
    opposite = 1 - parity
    b1 = sp.linear(psi, degree, parity=parity)
    c1 = sp.linear(psi, degree, True, parity=parity)
    m = sp.linear(c1 + 2 * b1, degree, True, parity=opposite)
    v = c1 / 12 + b1 / 3
    del c1
    b2 = sp.linear(b1, degree, parity=opposite); del b1
    m += b2
    v = sp.linear(v, degree, True, parity=opposite); v += b2 / 2
    b3 = sp.linear(b2, degree, parity=parity); del b2
    v = sp.linear(v, degree, True, parity=parity); v += b3 / 3
    b4 = sp.linear(b3, degree, parity=opposite); del b3
    v = sp.linear(v, degree, True, parity=opposite); v += b4 / 12
    return m, v


def find(sp, P, N):
    i = np.flatnonzero((sp.P == P) & (sp.N == N))
    return [int(x) for x in i]


def sector_mask(sp, s, Lp=None):
    """Same N parity and P parity as state s; optional reduced cutoff Efree<=Lp."""
    m = (sp.N % 2 == sp.N[s] % 2) & (sp.P % 2 == sp.P[s] % 2)
    if Lp is not None:
        m &= (4 * sp.N + sp.P) <= int(math.floor(4 * Lp + 1e-9))
    return m


def block_rs(sp, seeds, K, r, g, mask, diag=None, diag_at=None):
    """Bloch RS with intermediate normalization.
    seeds: model-space states (all with the same free energy E0).
    Q-space = mask & (Efree != E0): any other exactly degenerate state in the
    sector ('spectator') is EXCLUDED and its coupling is reported.
    diag: (dim, K+1) jets of a diagonal operator added to H (or None).
    diag_at: optional dict {seed_index_in_seeds: jets} of extra diagonal jets
             applied ONLY on the model state itself (shortcut for Dfull).
    r, g: coupling jets (len >= K+1); r[0]=g[0]=0.
    Returns heff[k][b,a] (k=0..K), firstorder diag (M0, V0) per seed, spectator couplings."""
    n = len(seeds)
    E0 = float(sp.Efree[seeds[0]])
    assert all(float(sp.Efree[s]) == E0 for s in seeds)
    par = int(sp.P[seeds[0]] % 2)
    assert all(int(sp.P[s] % 2) == par for s in seeds)
    den = E0 - sp.Efree
    ok = mask & (den != 0)
    spect = np.flatnonzero(mask & (den == 0))
    spect = np.array([j for j in spect if j not in seeds], dtype=np.int64)
    psi = [np.zeros((sp.dim, K + 1)) for _ in range(n)]
    for a, s in enumerate(seeds):
        psi[a][s, 0] = 1.
    heff = np.zeros((K + 1, n, n))
    heff[0] = E0 * np.eye(n)
    first = np.zeros((n, n, 2))
    spc = np.zeros((K + 1, max(1, len(spect)), n))
    for k in range(1, K + 1):
        T = []
        for a in range(n):
            m, v = vertices_nomask(sp, np.ascontiguousarray(psi[a][:, :k]), k - 1, par)
            if k == 1:
                for b in range(n):
                    first[b, a] = (m[seeds[b], 0], v[seeds[b], 0])
            t = sp.F1 * psi[a][:, k - 1]
            for j in range(1, k + 1):
                if r[j] != 0.: t += r[j] * m[:, k - j]
                if g[j] != 0.: t += g[j] * v[:, k - j]
            del m, v
            if diag is not None:
                for j in range(0, k + 1):
                    t += diag[:, j] * psi[a][:, k - j]
            if diag_at is not None and a in diag_at:
                t[seeds[a]] += diag_at[a][k]
            t[~mask] = 0.
            T.append(t)
        for a in range(n):
            for b in range(n):
                heff[k, b, a] = T[a][seeds[b]]
            if len(spect):
                spc[k, :, a] = T[a][spect]
        for a in range(n):
            t = T[a]
            for j in range(1, k + 1):
                for b in range(n):
                    if heff[j, b, a] != 0.:
                        t -= heff[j, b, a] * psi[b][:, k - j]
            psi[a][:, k] = np.where(ok, t / np.where(ok, den, 1.), 0.)
        del T
    return heff, first, spect, spc


def scalar_rs(sp, s, K, r, g, mask=None, diag=None, diag_at=None):
    if mask is None:
        mask = sector_mask(sp, s)
    h, first, spect, spc = block_rs(sp, [s], K, r, g, mask, diag,
                                    None if diag_at is None else {0: diag_at})
    return h[:, 0, 0].copy(), first[0, 0], spect, spc


def evac(sp, Lp, K, r, g):
    """Vacuum energy jets of the same Hamiltonian truncated at Efree<=Lp."""
    mask = (sp.N % 2 == 0) & (sp.P % 2 == 0) & ((4 * sp.N + sp.P) <= int(math.floor(4 * Lp + 1e-9)))
    h, _, _, _ = block_rs(sp, [0], K, r, g, mask)
    return h[:, 0, 0].copy()


def g2D_jets(sp, g, K):
    """Package isolated correction g(eps)^2 D_j(eps) as (dim, K+1) jets (D from vacuum_table)."""
    L = sp.cutoff
    sums = vacuum_table(L, K)
    up = np.maximum(0, (4 * L - 4 * sp.N.astype(np.int64) - sp.P.astype(np.int64)) // 4)
    D = np.stack([-(sums[L, k] - sums[up, k]) / 6 for k in range(K + 1)], 1)
    gg = np.convolve(g, g)[:K + 1]
    out = np.zeros((sp.dim, K + 1))
    for a in range(K + 1):
        for b in range(K + 1 - a):
            if gg[a] != 0.:
                out[:, a + b] += gg[a] * D[:, b]
    return out


def window_W(L, E0):
    """#{odd k in (L-E0, L]}"""
    return sum(1 for k in range(1, L + 1) if k % 2 == 1 and k > L - E0)


def series_eig2(H):
    """Eigenvalue jets of a 2x2 jet matrix H[k] (k=0..K) whose H[0] is E0*1 and
    whose H[1] has distinct eigenvalues. Returns list of jets for both branches."""
    K = H.shape[0] - 1
    # work with H' = (H - E0)/eps : jets H'[k] = H[k+1]
    Hp = H[1:]
    a = Hp[:, 0, 0]; d = Hp[:, 1, 1]; b = Hp[:, 0, 1]; c = Hp[:, 1, 0]
    n = len(a)
    def mul(x, y):
        return np.convolve(x, y)[:n]
    tr = a + d
    disc = mul(a - d, a - d) + 4 * mul(b, c)
    # sqrt of series
    s = np.zeros(n); s[0] = math.sqrt(disc[0])
    for k in range(1, n):
        s[k] = (disc[k] - sum(s[j] * s[k - j] for j in range(1, k))) / (2 * s[0])
    out = []
    for sign in (-1, 1):
        e = np.zeros(K + 1); e[0] = H[0, 0, 0]
        e[1:] = (tr + sign * s) / 2
        out.append(e)
    return out
