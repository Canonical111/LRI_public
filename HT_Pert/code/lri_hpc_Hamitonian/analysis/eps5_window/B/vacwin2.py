"""Memory-lean version of vacwin.py (same formulas): vertex on |0> computed in the P<=4 space and embedded,
X columns built directly, compact integer arrays. Usage: vacwin2.py L [L ...] -> vacwin_L{L}.json"""
import sys, json, time, gc
import numpy as np
from htb5 import Space, bubble_S_table
from vacwin import series_div

K = 5


def build(L):
    sp = Space(4 * L, 8, None, K, keep_modes=False)
    sm = Space(4 * L, 4, None, K, keep_modes=False)
    r_s = sm.keys // (sm.Pmax + 1); P_s = sm.keys % (sm.Pmax + 1)
    emb = np.searchsorted(sp.keys, r_s * (sp.Pmax + 1) + P_s)
    assert np.all(sp.keys[emb] == r_s * (sp.Pmax + 1) + P_s)
    del sp.keys, sp.Q
    sp.P = sp.P.astype(np.int8); sp.N = sp.N.astype(np.int32); sp.E4 = sp.E4.astype(np.int32)
    gc.collect()
    return sp, sm, emb


def energies(sp, sm, emb, c4, r, g, Sf):
    d = sp.dim
    mask = (sp.N % 2 == 0) & (sp.E4 <= c4)
    E4 = sp.E4
    Rinv = np.zeros(d); ok = mask & (E4 > 0); Rinv[ok] = -4.0 / E4[ok]
    # vertex on |0> in the small space, embedded
    masks = (sm.N % 2 == 0) & (sm.E4 <= c4)
    e0 = np.zeros(sm.dim); e0[0] = 1.
    M0s, V0s = sm.vertices(e0, 3, masks)
    def comb(Mj, Vj, k, maxl, n):
        out = np.zeros(n)
        for i in range(1, k + 1):
            l = k - i
            if l > maxl: continue
            if r[i] != 0.: out += r[i] * Mj[:, l]
            if g[i] != 0.: out += g[i] * Vj[:, l]
        return out
    W0 = {}
    for k in range(1, 5):
        w = np.zeros(d); w[emb] = comb(M0s, V0s, k, 3, sm.dim); W0[k] = w
    v00 = np.zeros(d); v00[emb] = V0s[:, 0]
    del M0s, V0s
    psi1 = Rinv * W0[1]
    M1, V1 = sp.vertices(psi1, 2, mask)
    W1 = {k: comb(M1, V1, k, 2, d) for k in range(1, 4)}
    del M1, V1; gc.collect()
    F1 = -sp.P / 4.0
    W1[1] += F1 * psi1
    psi2 = Rinv * (W1[1] + W0[2])
    M2, V2 = sp.vertices(psi2, 0, mask)
    W2 = comb(M2, V2, 1, 0, d) + F1 * psi2
    del M2, V2, F1; gc.collect()
    # X_{L''} on intermediates: [g^2 D]_{2,3} + g1^3 W relative to c4/4 (only cols 2,3 needed)
    top = c4 // 4; up = np.maximum(0, (c4 - E4) // 4)
    D0 = -(Sf[top, 0] - Sf[up, 0]) / 6.0; D1 = -(Sf[top, 1] - Sf[up, 1]) / 6.0
    cnt = lambda x: (x + 1) // 2
    Wn = (cnt(top) - cnt(up)).astype(float)
    X2 = g[1] ** 2 * D0
    X3 = 2 * g[1] * g[2] * D0 + g[1] ** 2 * D1 + g[1] ** 3 * Wn
    X2[~mask] = 0.; X3[~mask] = 0.
    del D0, D1, Wn, up
    psi = [None, psi1, psi2]
    Nn0 = np.zeros(K + 1); Dd = np.zeros(K + 1); Nx = np.zeros(K + 1)
    E0 = E4 / 4.0
    for a in (1, 2):
        for b in (1, 2):
            Dd[a + b] += psi[a] @ psi[b]
            Nn0[a + b] += psi[a] @ (E0 * psi[b])
    for b in (1, 2):
        for k in range(1, K + 1 - b):
            Nn0[b + k] += 2 * (psi[b] @ W0[k])
    for k in range(1, 4):
        Nn0[2 + k] += psi1 @ W1[k]
    for k in range(1, 3):
        Nn0[3 + k] += 2 * (psi2 @ W1[k])
    Nn0[5] += psi2 @ W2
    Nx[4] += psi1 @ (X2 * psi1)
    Nx[5] += psi1 @ (X3 * psi1) + 2 * (psi1 @ (X2 * psi2))
    out = {'raw': series_div(Nn0, Dd, K), 'conn': series_div(Nn0 + Nx, Dd, K), 'S2g': float(psi1 @ v00)}
    return out


def run(L, r, g, js=None):
    t0 = time.time()
    sp, sm, emb = build(L)
    tb = time.time() - t0
    S = bubble_S_table(L + 2, K)
    Sf = np.array([[float(x) for x in row] for row in S])
    js = js or [2 * L, 2 * L - 1, 2 * L - 2, 2 * L - 3, 2 * L - 4]
    res = {'L': L, 'dim8': sp.dim, 'nedges': int(sp.nedges), 'r': list(r), 'g': list(g), 'E': {}}
    for j in js:
        e = energies(sp, sm, emb, 2 * j, r, g, Sf)
        res['E'][str(j)] = {'raw': e['raw'].tolist(), 'conn': e['conn'].tolist(), 'S2g': e['S2g']}
        gc.collect()
    res['seconds'] = time.time() - t0; res['build'] = tb
    return res


if __name__ == '__main__':
    from couplings import raw_couplings
    args = sys.argv[1:]
    suffix = ''
    if args[0] == '--suffix':
        suffix = args[1]; args = args[2:]
    for L in [int(a) for a in args]:
        r, g = raw_couplings(L)
        g = list(g); g[4] = 0.; g[5] = 0.; r = list(r); r[4] = 0.; r[5] = 0.
        res = run(L, r, g)
        E = res['E']; j = 2 * L
        A = np.array(E[str(j)]['conn']) - np.array(E[str(j - 1)]['conn'])
        B = np.array(E[str(j)]['conn']) - np.array(E[str(j - 2)]['conn'])
        print(f"L={L} dim8={res['dim8']} t={res['seconds']:.1f}s (build {res['build']:.1f})  A4={A[4]:.15f} B4={B[4]:.15f} A5={A[5]:.13f} B5={B[5]:.13f}", flush=True)
        json.dump(res, open(f'vacwin{suffix}_L{L}.json', 'w'), indent=1)
        gc.collect()
