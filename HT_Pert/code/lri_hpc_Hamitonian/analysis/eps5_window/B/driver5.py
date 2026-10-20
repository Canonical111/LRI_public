"""Full-basis eps^5 runs (Pmax=11 default; all variants; full Dconn tables at small cutoffs).
Usage: driver5.py cut4 [cut4 ...]   -> full5_c{cut4}.json   (cut4 = 4*Lambda; Lambda may be L+1/4)

Variants (X = diagonal operator on every basis state, couplings retuned per variant):
  raw       : X = 0
  g2D       : package g(eps)^2 D(eps) (g = the variant's own tuned g; self-consistent at eps^5)
  g2D+g3W   : g2D + g1^3 W at eps^3 (third-order bubble = +1 per lost odd shell)
  Dconn     : X_i = Ec(Lam) - Ec(floor_half(Lam - E0_i)), Ec = vacuum with X_{L''}=[g^2D]_{2,3}+g1^3W on
              intermediates (self-consistent through eps^5); vacuum eps^5 uses the variant's own g4
  Dfull_raw : same with the literal raw vacuum table (double counts the bubble-bubble class)
"""
import sys, json, time, gc
import numpy as np
from htb5 import *

K = 5
STATES = {'p0': [], 'p1': [0], 'p2': [0, 0], 'p3': [0, 0, 0], 'd1': [1], 'd2': [0, 1], 'd3': [0, 0, 1]}
REFS = ('p0', 'p1', 'p3')


def run(cut4, Pmax=11, full_tables=True, verbose=True, states=STATES):
    t0 = time.time()
    sp = Space(cut4, Pmax, None, K)
    Lt = cut4 // 4
    S = bubble_S_table(Lt + 2, K)
    Sf = np.array([[float(x) for x in row] for row in S])
    idx = {k: sp.index(v) for k, v in states.items()}
    base = {k: St(sp, i, K) for k, i in idx.items()}
    r = np.zeros(K + 1); g = np.zeros(K + 1)
    for n in (1, 2):
        tp = {k: st.source(n, r, g, None) for k, st in base.items()}
        raw = {k: tp[k][base[k].s] for k in base}
        r[n] = ((-.25 if n == 1 else 0.) - (raw['p1'] - raw['p0'])) / 2
        g[n] = ((.25 if n == 1 else 0.) - (raw['p3'] - raw['p0']) - 6 * r[n]) / 3
        for k, st in base.items():
            st.advance(n, tp[k], r[n], g[n], vertex=True)
    t1 = time.time()
    out = {'cut4': cut4, 'Lambda': cut4 / 4, 'dim': sp.dim, 'Pmax': Pmax, 'variants': {}}

    def do_variant(name, Xb):
        """Xb(gv) -> X (dim x K+1); columns <=4 must not depend on gv[4], column 5 may."""
        X = Xb(g)
        sts = {k: st.fork(2, X) for k, st in base.items()}
        if X is not None:
            for p in REFS:
                assert abs(X[sts[p].s, 2]) < 1e-14 and abs(X[sts[p].s, 3]) < 1e-14, (name, p, X[sts[p].s])
        rr, gg = r.copy(), g.copy()
        for n in range(3, K + 1):
            Xn = Xb(gg)           # X^(k), k<=n, needs g_1..g_{n-1}: all tuned by now
            if X is not None:
                assert np.max(np.abs(Xn[:, :3] - X[:, :3])) < 1e-13
            rr, gg = run_orders(sts, rr, gg, Xn, n, K, tune=REFS, n_to=n)
        X5 = Xn
        E = {k: np.array(st.E) for k, st in sts.items()}
        d = {'r': rr.tolist(), 'g': gg.tolist(), 'C': (E['p2'] - E['p0']).tolist(),
             'E': {k: v.tolist() for k, v in E.items()}}
        for p in (1, 2, 3):
            if 'd%d' % p in E:
                d['spacing_d%d' % p] = (E['d%d' % p] - E['p%d' % p]).tolist()
        if X5 is not None:
            d['Xrow'] = {k: X5[i].tolist() for k, i in idx.items()}
        out['variants'][name] = d
        return rr, gg

    rraw, graw = do_variant('raw', lambda gv: None)
    t2 = time.time()
    # vacuum tables (raw couplings; eps^5 depends on g4 only via 2 g1 g4 S2, S2 = E^(2)/g1^2)
    jtop = cut4 // 2
    sp8 = Space(2 * jtop, 8, None, K)
    jneed = sorted({int(j) for j in half_index(sp.E4[list(idx.values())], cut4)} | {jtop})
    jl = list(range(0, jtop + 1)) if full_tables else jneed
    vac = vacuum_tables(sp8, rraw, graw, K, Sf, jl)
    out['dim8'] = sp8.dim
    out['vac'] = {str(j): {k: v.tolist() for k, v in d.items()} for j, d in vac.items()}
    t3 = time.time()
    Tr = np.full((jtop + 1, K + 1), np.nan); Tc = np.full((jtop + 1, K + 1), np.nan)
    for j in jl:
        Tr[j] = vac[j]['raw']; Tc[j] = vac[j]['conn']
    g1 = graw[1]

    def tab_g4(T, gv):
        T = T.copy()
        T[:, 5] += 2 * g1 * (gv[4] - graw[4]) * T[:, 2] / g1 ** 2
        return T

    X3raw = g2D3W_diag(sp.E4, graw, cut4, Sf, K)
    if full_tables:
        Xc = table_diag(sp.E4, cut4, Tc); Xr = table_diag(sp.E4, cut4, Tr)
        out['check_Dconn2_eq_g2D2'] = float(np.max(np.abs(Xc[:, 2] - X3raw[:, 2])))
        out['check_Dconn3_eq_g2D3+g1^3W'] = float(np.max(np.abs(Xc[:, 3] - X3raw[:, 3])))
        out['check_Dconn_eq_Draw_upto3'] = float(np.max(np.abs(Xc[:, :4] - Xr[:, :4])))
        del Xc, Xr

    def Xtab(T):
        def b(gv):
            Tg = tab_g4(T, gv)
            if full_tables:
                return table_diag(sp.E4, cut4, Tg)
            X = g2D3W_diag(sp.E4, gv, cut4, Sf, K); X[:, 4:] = 0.
            for k, i in idx.items():
                j = int(half_index(np.array([sp.E4[i]]), cut4)[0])
                X[i] = Tg[jtop] - Tg[j]
            return X
        return b

    do_variant('g2D', lambda gv: g2D_diag(sp.E4, gv, cut4, Sf, K))
    do_variant('g2D+g3W', lambda gv: g2D3W_diag(sp.E4, gv, cut4, Sf, K))
    do_variant('Dconn', Xtab(Tc))
    do_variant('Dfull_raw', Xtab(Tr))
    out['seconds'] = {'total': time.time() - t0, 'base': t1 - t0, 'raw': t2 - t1, 'vac': t3 - t2}
    if verbose:
        print(f"cut4={cut4} Lam={cut4/4} dim={sp.dim} dim8={sp8.dim} t={ {k: round(v, 1) for k, v in out['seconds'].items()} }", flush=True)
        for k in ('check_Dconn2_eq_g2D2', 'check_Dconn3_eq_g2D3+g1^3W', 'check_Dconn_eq_Draw_upto3'):
            if k in out:
                print('  ', k, out[k])
        for v, d in out['variants'].items():
            print(f"  {v:10s} r45={d['r'][4]:+.12f},{d['r'][5]:+.10f} g45={d['g'][4]:+.12f},{d['g'][5]:+.10f} C4={d['C'][4]:.12f} C5={d['C'][5]:.10f} "
                  f"d1={np.array(d.get('spacing_d1', [0]*6)[2:])}", flush=True)
    return out


if __name__ == '__main__':
    for c in [int(a) for a in sys.argv[1:]]:
        o = run(c, full_tables=(c <= 4 * 36))
        json.dump(o, open(f'full5_c{c}.json', 'w'), indent=1)
        gc.collect()
