"""Building blocks of the complete Delta C5 at even L (references only).
Usage: c5tab.py L [L ...] [--novac] [--vacmode=rs|q]
 * references p=0..3: psi_1, psi_2 on the exact correction support (P<=7, q<=4) -> first-order response integrals
   <psi1|D2|psi1>, <psi1|D3|psi1>, <psi1|D2|psi2>, norms, M/V first-order and eps^1 Rayleigh coefficients;
 * vacuum energies through eps^5 at x = L, L-1/2, L-1 (raw and self-consistent Ec) on (P,q)<=(8,8):
   'rs': direct RS (psi through eps^4); 'q': Wigner 2n+1 Rayleigh quotient with psi through eps^2
   (raw) + first-order response of the vacuum to its own Dconn^[x] (Ec - Eraw = <psi|D|psi>/<psi|psi>).
Output c5tab_L.json.  Raw r_k,g_k through eps^3 are recomputed (lockstep, exact on P<=7,q<=4); g4 is
taken from the campaign row (it does not enter the reference windows; checked).
"""
import sys, json, time
from eng5 import *
from lri_hpc.operators import quotient_components, divide_series

PRES = ['g2D', 'g2D3W', 'Dconn', 'Dfull']
camp = {}
for f in ['thermal_new.json', 'prior_c7/C7_completed_runs.json', 'C7_extension.json']:
    for row in json.load(open('<PROJECT>/lri_hpc_Hamitonian/analysis/extended/' + f)):
        camp[row['cutoff']] = row


def vac_q(sp, x, r, g, D23=None):
    """raw vacuum jets through eps^5 by the 2n+1 quotient on psi_hat = psi0+eps psi1+eps^2 psi2; and the
    first-order response to a diagonal operator with jets D23 (eps^2, eps^3 columns) if given."""
    mask = (sp.N % 2 == 0) & (sp.P % 2 == 0) & (E4(sp) <= q4(x))
    rr = rs_multi(sp, [dict(seeds=[0], mask=mask)], 2, r, g, keep=True)[0]
    psi = np.zeros((sp.dim, 3)); psi[0, 0] = 1.; psi[:, 1] = rr['psi1']; psi[:, 2] = rr['psi2']
    del rr
    F, M, V = quotient_components(sp, psi, 5, parity=0)
    E = F.copy()
    for k in range(1, 6):
        E[k] += sum(r[j] * M[k - j] + g[j] * V[k - j] for j in range(1, k + 1))
    R = np.zeros(6)
    if D23 is not None:
        d2, d3 = D23
        p1, p2 = psi[:, 1], psi[:, 2]
        R[4] = p1 @ (d2 * p1)
        R[5] = p1 @ (d3 * p1) + 2 * (p1 @ (d2 * p2))
    return E, R


def run(L, dovac=True, vacmode='q'):
    t0 = time.time()
    K = 5
    sp7 = Space(L, 7, 4, 2)
    r = np.zeros(K + 1); g = np.zeros(K + 1)
    refs = [dict(seeds=[find(sp7, p, 0)[0]], mask=mask_for(sp7, 0, p % 2, L)) for p in range(4)]
    res = rs_multi(sp7, refs, 2, r, g, tune={'items': (0, 1, 3), 'orders': {1, 2}}, keep=True)
    # r3, g3 (exact on this support) from a 3rd-order lockstep
    r3 = np.zeros(4); g3 = np.zeros(4)
    rs_multi(sp7, refs[:2] + refs[3:], 3, r3, g3, tune={'items': (0, 1, 2), 'orders': {1, 2, 3}})
    r[3] = r3[3]; g[3] = g3[3]
    cr = camp[L]
    assert abs(r[2] - cr['r'][2]) < 1e-11 and abs(g[2] - cr['g'][2]) < 1e-11 and abs(g[3] - cr['g'][3]) < 1e-10
    r[4] = cr['r'][4]; g[4] = cr['g'][4]
    sums = vacuum_table(L, K)
    tab = None
    gd, D = g2D_window(sp7.Efree, L, g, K, sums)
    W = Wwin(sp7.Efree, L)
    jets = {'g2D': (gd[:, 2], gd[:, 3]), 'g2D3W': (gd[:, 2], gd[:, 3] + G1 ** 3 * W)}
    jets['Dconn'] = jets['g2D3W']; jets['Dfull'] = jets['g2D3W']   # identical through eps^3 (verified to 1e-15)
    out = dict(L=L, r=r.tolist(), g=g.tolist(), refs={})
    for p in range(4):
        rr = res[p]
        p1, p2 = rr['psi1'], rr['psi2']
        rec = dict(E=rr['heff'][:, 0, 0].tolist(), M0=rr['first'][0, 0, 0], V0=rr['first'][0, 0, 1], mv1=list(rr['mv1']),
                   n11=float(p1 @ p1), n12=float(p1 @ p2))
        for pres in PRES:
            d2, d3 = jets[pres]
            rec[pres] = (float(p1 @ (d2 * p1)), float(p1 @ (d3 * p1)), float(p1 @ (d2 * p2)))
        out['refs'][p] = rec
    del res, sp7, gd, D, W, jets
    out['t_refs'] = time.time() - t0
    if dovac:
        spv = Space(L, 8, 8, 4)
        out['dim_vac'] = int(spv.dim)
        vac = {}
        for x in (float(L), L - .5, L - 1.):
            if vacmode == 'rs':
                if tab is None:
                    tab = low_table(L, r[:4].copy(), g[:4].copy(), 3)
                    tab = {xx: np.r_[v, np.zeros(K + 1 - len(v))] for xx, v in tab.items()}
                ec = vac_jets(spv, x, K, r, g, tab); er = vac_jets(spv, x, K, r, g, None)
                vac[str(x)] = dict(Ec=ec.tolist(), Eraw=er.tolist())
            else:
                # memory-lean eps^2, eps^3 jets of g^2 D + g1^3 W (windows relative to x)
                top = int(math.floor(x + 1e-9))
                up = np.clip(np.floor(x - spv.Efree + 1e-9).astype(np.int64), 0, top)
                gg = np.convolve(g, g)
                D0 = -(sums[top, 0] - sums[up, 0]) / 6
                d2 = gg[2] * D0
                d3 = gg[3] * D0
                del D0
                d3 += gg[2] * (-(sums[top, 1] - sums[up, 1]) / 6)
                nodd = lambda n: (np.maximum(n, 0) + 1) // 2
                d3 += G1 ** 3 * (nodd(top) - nodd(up))
                del up
                er, R = vac_q(spv, x, r, g, (d2, d3))
                del d2, d3
                vac[str(x)] = dict(Ec=(er + R).tolist(), Eraw=er.tolist(), R=R.tolist())
            print(f'   L={L} x={x} done ({time.time()-t0:.1f}s)', flush=True)
        out['vac'] = vac
        del spv
    out['seconds'] = time.time() - t0
    return out


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    opts = {a.split('=')[0]: (a.split('=')[1] if '=' in a else True) for a in sys.argv[1:] if a.startswith('--')}
    for a in args:
        L = int(a)
        o = run(L, '--novac' not in opts, opts.get('--vacmode', 'q'))
        json.dump(o, open(f'c5tab_{L}{opts.get("--tag","")}.json', 'w'))
        print(f'L={L} done in {o["seconds"]:.1f}s', flush=True)
