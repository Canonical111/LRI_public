"""Folded connected-x-bubble term at eps^4 for single-particle states (phi = a0, dphi = a1).
A pair (j, b) of a connected first-order excitation j (C^3 B, P=3) and a vacuum bubble b
(P=4, odd shell E_b) is missing from the truncated space when E_j + E_b > Lam while the RS
renormalisation term keeps it (b <= Lam - E_i).  The g^2D operator response restores the
1/(Delta^2 E_b) half; the 1/(Delta E_b^2) half is NOT in Dconn:
   F_i = - sum_j |psi1_j|^2 Delta_j * (g1^2/6) * [H(Lam - E_i) - H(Lam - E_j)],
   H(x) = sum_{odd E <= x} 1/E  (eps=0 shell weight sum_b |g1 V_b0|^2/E_b = g1^2/6).
Effect on the dphi identity after the r4 retune (M0(a1)-M0(a0) = -1):  dv4 = F_dphi - F_phi/2."""
import sys, os, json, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ht4 import *

g1 = 1 / 3
def H(x):
    top = int(math.floor(x + 1e-9))
    return math.fsum(1 / E for E in range(1, top + 1, 2))

def folded(Lam):
    Lint = 2 * int(math.ceil(Lam / 2 - 1e-12))
    sp = Space(Lint, 6, 5, 0)
    E4 = 4 * sp.N.astype(np.int64) + sp.P.astype(np.int64)
    allowed = E4 <= int(round(4 * Lam))
    out = {}
    for name, (P0, N0) in {'phi': (1, 0), 'dphi': (1, 1)}.items():
        s = find(sp, P0, N0)[0]
        x = np.zeros((sp.dim, 1)); x[s, 0] = 1.
        m, v = vertices_nomask(sp, x, 0, 1)
        Ei = float(sp.Efree[s])
        conn = allowed & (sp.P == P0 + 2) & (sp.N % 2 == N0 % 2)
        Ej = sp.Efree[conn]; vj = g1 * v[conn, 0]
        D = Ej - Ei
        psi2 = (vj / D) ** 2
        Hi = H(Lam - Ei)
        Hj = np.array([H(Lam - e) for e in Ej]) if len(Ej) < 2000 else None
        if Hj is None:
            # vectorised H on the quarter grid
            grid = {}
            for e in np.unique(Ej):
                grid[float(e)] = H(Lam - e)
            Hj = np.array([grid[float(e)] for e in Ej])
        F = -np.sum(psi2 * D * (g1 ** 2 / 6) * (Hi - Hj))
        out[name] = float(F)
    out['dv4'] = out['dphi'] - out['phi'] / 2
    return out

if __name__ == '__main__':
    ph = float(sys.argv[1]); Ls = range(int(sys.argv[2]), int(sys.argv[3]) + 1, 2)
    res = {}
    for L in Ls:
        o = folded(L + ph); res[L + ph] = o
        print(f'Lam={L+ph:7.2f} F_phi={o["phi"]:+.8f} F_dphi={o["dphi"]:+.8f} dv4={o["dv4"]:+.8f}', flush=True)
    json.dump(res, open(os.path.join(HERE, f'folded_ph{ph}.json'), 'w'))
