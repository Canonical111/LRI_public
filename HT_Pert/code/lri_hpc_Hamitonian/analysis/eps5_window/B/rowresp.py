"""For each even L: capped-space paired differences (exact):
 dC_g2D, dC_g2D3W (operator parts), and the linear response of C4,C5 to reference-row shifts
 X^(4): (p1,p2)->a, p3->b  [rho4A, rho4B for C4 (expect 0, -1/3); rho5A, rho5B for C5]
 X^(5): (p1,p2)->a5, p3->b5 [expect C5 response 0, -1/3].
Complete Dconn: dC5 = dC5_g2D3W + rho5A*A4 + rho5B*B4 - B5/3 ; dC4 = dC4_g2D - B4/3."""
import numpy as np, json, sys, time
from capped5 import Capped, K
from htb5 import g2D3W_diag

def resp(L):
    t0 = time.time()
    cp = Capped(4 * L)
    sp = cp.sp
    out = {'L': L, 'dim': sp.dim, 'r3': cp.res['raw']['r'][:4].tolist(), 'g3': cp.res['raw']['g'][:4].tolist()}
    out['g2D'] = cp.deltas(cp.g2D(False)); out['g2D+g3W'] = cp.deltas(cp.g2D(True))
    for tag, order, rowv in (('rowA4', 4, (1., 0.)), ('rowB4', 4, (0., 1.)), ('rowA5', 5, (1., 0.)), ('rowB5', 5, (0., 1.))):
        def Xb(gv, order=order, rowv=rowv):
            X = np.zeros((sp.dim, K + 1))
            for p, val in (('p1', rowv[0]), ('p2', rowv[0]), ('p3', rowv[1])):
                X[cp.idx[p], order] = val
            return X
        out[tag] = cp.deltas(cp.variant(Xb))
    out['seconds'] = time.time() - t0
    return out

if __name__ == '__main__':
    Ls = [int(a) for a in sys.argv[1:]]
    res = {}
    for L in Ls:
        o = resp(L); res[L] = o
        print(L, o['dim'], 'dC5 g2D %.12f g2D3W %.12f rho5A %.12f rho5B %.12f rho4A %.2e rho4B %.12f | rowA5->C5 %.3e rowB5->C5 %.12f  %.1fs' % (
            o['g2D']['dC'][5], o['g2D+g3W']['dC'][5], o['rowA4']['dC'][5], o['rowB4']['dC'][5], o['rowA4']['dC'][4], o['rowB4']['dC'][4],
            o['rowA5']['dC'][5], o['rowB5']['dC'][5], o['seconds']), flush=True)
    json.dump(res, open('rowresp_%d_%d.json' % (Ls[0], Ls[-1]), 'w'), indent=1)
