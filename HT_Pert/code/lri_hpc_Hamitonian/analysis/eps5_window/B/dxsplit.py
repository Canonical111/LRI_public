"""Split of the Dconn vacuum-window X-change terms (bubble-bubble class restored on vacuum intermediates):
 eps^4: <psi1|dX2|psi1>;  eps^5: <psi1|dX3|psi1> + 2<psi1|dX2|psi2^(4)>, and the part of dX3 due to g1^3 W
 (the third-order bubble that the self-consistent eps^5 recursion must include on vacuum intermediates)."""
import sys, json, numpy as np
from htb5 import Space, bubble_S_table, g2D_diag, window_W
from couplings import raw_couplings
K = 5
for L in [int(a) for a in sys.argv[1:]]:
    r, g = raw_couplings(L); g1, g2, r2 = g[1], g[2], r[2]
    sp = Space(4 * L, 4, None, K, keep_modes=False)
    mask = (sp.N % 2 == 0); E0 = sp.E4 / 4.
    Rinv = np.where(mask & (sp.E4 > 0), -1.0 / np.where(sp.E4 > 0, E0, 1.), 0.)
    e0 = np.zeros(sp.dim); e0[0] = 1.
    M0, V0 = sp.vertices(e0, 1, mask); psi1 = Rinv * g1 * V0[:, 0]
    M1, V1 = sp.vertices(psi1, 0, mask)
    psi2 = Rinv * (-sp.P / 4. * psi1 + g1 * V1[:, 0] + r2 * M0[:, 0] + g2 * V0[:, 0] + g1 * V0[:, 1]); psi2[sp.P != 4] = 0.
    S = bubble_S_table(L + 2, K); Sf = np.array([[float(x) for x in row] for row in S])
    gg = np.array([0, g1, g2, 0, 0, 0.])
    out = {'L': L}
    for name, c4 in (('A', 4 * L - 2), ('B', 4 * L - 4)):
        d = g2D_diag(sp.E4, gg, 4 * L, Sf, K) - g2D_diag(sp.E4, gg, c4, Sf, K)
        dW = (window_W(sp.E4, 4 * L) - window_W(sp.E4, c4)).astype(float)
        out[name] = dict(dX4=float(psi1 @ (d[:, 2] * psi1)), dX5_g2D=float(psi1 @ (d[:, 3] * psi1) + 2 * psi1 @ (d[:, 2] * psi2)),
                         dX5_g3W=float(g1 ** 3 * (psi1 @ (dW * psi1))))
    print(json.dumps(out), flush=True)
