"""Vacuum energies E_vac(L'') through eps^5 at half-integer cutoffs L''=j/2 near the top of an
even cutoff L, by the 2n+1 (Rayleigh-quotient) rule: Psi~ = psi0 + eps psi1 + eps^2 psi2 gives E
through eps^5 (independent algorithm from the RS recursion in htb5.vacuum_energy).
raw : X = 0 ; conn: X_{L''} = [g^2 D]_{2,3} + g1^3 W relative to L'' on intermediates (Dconn vacuum).
g4 enters E^(5) only as 2 g4 <psi1|V0|0> (reported separately as S2g = <psi1|V0|0>; E5 below uses g4=0).
Usage: vacwin.py L [L ...]  -> vacwin_L{L}.json (cutoffs j = 2L, 2L-1, 2L-2, 2L-3, 2L-4)."""
import sys, json, time, gc
import numpy as np
from htb5 import Space, bubble_S_table, g2D3W_diag

K = 5


def series_div(Nn, Dd, K):
    E = np.zeros(K + 1)
    for n in range(K + 1):
        E[n] = Nn[n] - sum(E[k] * Dd[n - k] for k in range(n))
    return E


def energies(sp, c4, r, g, Sf, j_jet=K):
    """returns dict raw/conn: E[0..5] (g4 := 0; r4,r5,g5 irrelevant), S2g=<psi1|V0|0>. Memory-lean."""
    mask = (sp.N % 2 == 0) & (sp.E4 <= c4)
    assert sp.P[0] == 0
    E0 = sp.E4 / 4.0
    Rinv = np.where(mask & (sp.E4 > 0), -1.0 / np.where(sp.E4 > 0, E0, 1.0), 0.0)
    F1 = -sp.P / 4.0
    e0 = np.zeros(sp.dim); e0[0] = 1.
    M0, V0 = sp.vertices(e0, 3, mask)            # jets 0..3 on psi0
    def comb(Mj, Vj, k, maxl):
        out = np.zeros(sp.dim)
        for i in range(1, k + 1):
            l = k - i
            if l > maxl: continue
            if r[i] != 0.: out += r[i] * Mj[:, l]
            if g[i] != 0.: out += g[i] * Vj[:, l]
        return out
    W0 = {k: comb(M0, V0, k, 3) for k in range(1, 5)}       # V_k|0>, k=1..4 (no F1, no X on |0>)
    v00 = V0[:, 0].copy()
    del M0, V0
    psi1 = Rinv * W0[1]
    M1, V1 = sp.vertices(psi1, 2, mask)            # jets 0..2 on psi1
    W1 = {k: comb(M1, V1, k, 2) for k in range(1, 4)}       # (V_k - F1 - X) psi1, k=1..3
    del M1, V1
    W1[1] += F1 * psi1
    psi2 = Rinv * (W1[1] + W0[2])
    M2, V2 = sp.vertices(psi2, 0, mask)
    W2 = comb(M2, V2, 1, 0) + F1 * psi2                    # V_1 psi2
    del M2, V2
    X = g2D3W_diag(sp.E4, g, c4, Sf, K)[:, 2:4].copy()
    X[~mask] = 0.
    psi = [None, psi1, psi2]
    Nn0 = np.zeros(K + 1); Dd = np.zeros(K + 1); Nx = np.zeros(K + 1)
    for a in (1, 2):
        for b in (1, 2):
            Dd[a + b] += psi[a] @ psi[b]
            Nn0[a + b] += psi[a] @ (E0 * psi[b])
    # pairs with a vertex: (0,b) and (b,0): <psi_b|V_k|0>, k <= 5-b
    for b in (1, 2):
        for k in range(1, K + 1 - b):
            Nn0[b + k] += 2 * (psi[b] @ W0[k])
    # (1,1): k<=3 ; (1,2),(2,1): k<=2 ; (2,2): k=1
    for k in range(1, 4):
        Nn0[2 + k] += psi1 @ W1[k]
    for k in range(1, 3):
        Nn0[3 + k] += 2 * (psi2 @ W1[k])
    Nn0[5] += psi2 @ W2
    # X terms (k>=2): (1,1) k=2,3 ; (1,2),(2,1) k=2
    Nx[4] += psi1 @ (X[:, 0] * psi1)
    Nx[5] += psi1 @ (X[:, 1] * psi1) + 2 * (psi1 @ (X[:, 0] * psi2))
    out = {'raw': series_div(Nn0, Dd, K), 'conn': series_div(Nn0 + Nx, Dd, K)}
    out['S2g'] = float(psi1 @ v00)
    return out


def run(L, js=None, r=None, g=None):
    t0 = time.time()
    sp = Space(4 * L, 8, None, K, keep_modes=False)
    tb = time.time() - t0
    S = bubble_S_table(L + 2, K)
    Sf = np.array([[float(x) for x in row] for row in S])
    js = js or [2 * L, 2 * L - 1, 2 * L - 2, 2 * L - 3, 2 * L - 4]
    res = {'L': L, 'dim8': sp.dim, 'nedges': int(sp.nedges), 'r': list(r), 'g': list(g), 'E': {}}
    for j in js:
        e = energies(sp, 2 * j, r, g, Sf)
        res['E'][str(j)] = {'raw': e['raw'].tolist(), 'conn': e['conn'].tolist(), 'S2g': e['S2g']}
    res['seconds'] = time.time() - t0; res['build'] = tb
    return res


if __name__ == '__main__':
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from couplings import raw_couplings
    for L in [int(a) for a in sys.argv[1:]]:
        r, g = raw_couplings(L)
        g = list(g); g[4] = 0.; g[5] = 0.; r = list(r); r[4] = 0.; r[5] = 0.
        res = run(L, r=r, g=g)
        E = res['E']; j = 2 * L
        A = np.array(E[str(j)]['conn']) - np.array(E[str(j - 1)]['conn'])
        B = np.array(E[str(j)]['conn']) - np.array(E[str(j - 2)]['conn'])
        print(f"L={L} dim8={res['dim8']} t={res['seconds']:.1f}s (build {res['build']:.1f})  A4={A[4]:.15f} B4={B[4]:.15f} A5={A[5]:.13f} B5={B[5]:.13f}", flush=True)
        json.dump(res, open(f'vacwin_L{L}.json', 'w'), indent=1)
        gc.collect()
