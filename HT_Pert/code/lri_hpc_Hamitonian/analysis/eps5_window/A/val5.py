"""Validation of eng5 at small L:
 (1) raw lockstep tuning through eps^5 vs package calibrate(order 5) and campaign C_k;
 (2) Dconn^(2), Dconn^(3) from the raw low table vs closed forms g^2D and g^2D + g1^3 W (all quarter E0, several Lam);
 (3) vacuum jets: self-consistent minus raw at eps^4 vs A's closed form R(L')."""
import sys, json, math, time
from eng5 import *
sys.path.insert(0, '<PROJECT>/lri_hpc_Hamitonian/analysis/extended')
camp = {}
for f in ['thermal_new.json', 'prior_c7/C7_completed_runs.json', 'C7_extension.json']:
    try:
        for row in json.load(open('<PROJECT>/lri_hpc_Hamitonian/analysis/extended/' + f)):
            camp[row['cutoff']] = row
    except Exception as e:
        print('skip', f, e)


def Rclosed(Lp, g1=1 / 3):
    s = 0.
    top = int(math.floor(Lp + 1e-9))
    for E in range(1, top + 1, 2):
        n = sum(1 for k in range(1, top + 1) if k % 2 == 1 and Lp - E < k <= Lp)
        s += n / E
    return -(g1 ** 4 / 36) * s


for L in [int(a) for a in sys.argv[1:]]:
    t0 = time.time()
    K = 5
    sp = Space(L, 11, 8, K - 1)
    _, Ecal, rcal, gcal = calibrate(sp, K)
    r = np.zeros(K + 1); g = np.zeros(K + 1)
    items = [dict(seeds=[find(sp, p, 0)[0]], mask=mask_for(sp, 0, p % 2, L)) for p in range(4)]
    res = rs_multi(sp, items, K, r, g, tune={'items': (0, 1, 3), 'orders': set(range(1, K + 1))})
    E = [x['heff'][:, 0, 0] for x in res]
    C = E[2] - E[0]
    print(f'L={L} dim={sp.dim} t={time.time()-t0:.1f}s')
    print('  r-rcal', np.abs(r - rcal).max(), ' g-gcal', np.abs(g - gcal).max())
    if L in camp:
        cc = np.array(camp[L]['C'][:K + 1])
        print('  C - campaign (rel):', [f'{(C[k]-cc[k])/abs(cc[k]):.1e}' for k in range(2, K + 1)], ' C5=', C[5])
    # (2) low table and closed forms
    tab = low_table(L, r, g, 3)
    Ef = np.array(sorted({x / 4 for x in range(0, 4 * L + 1)}))
    for Lam in [L, L + .25, L + .5, L + .75, L - 1 + .25]:
        if Lam > L: continue
        d = dconn23(Ef, Lam, tab, 3)
        gd, D = g2D_window(Ef, Lam, g, 3)
        W = Wwin(Ef, Lam)
        ok = Ef <= Lam
        e2 = np.abs(d[ok, 2] - gd[ok, 2]).max(); e3 = np.abs(d[ok, 3] - gd[ok, 3] - G1 ** 3 * W[ok]).max()
        print(f'  Lam={Lam}: max|Dconn2-g2D2|={e2:.1e}  max|Dconn3-g2D3-g1^3W|={e3:.1e}')
    # (3) vacuum jets self-consistent vs raw
    sv = Space(L, 8, 8, K - 1)
    for x in [L, L - .5, L - 1, L - 1.5]:
        ec = vac_jets(sv, x, K, r, g, tab)
        er = vac_jets(sv, x, K, r, g, None)
        print(f'  x={x}: Ec-Eraw = {np.round(ec-er,13).tolist()}  Rclosed={Rclosed(x):+.13f}')
