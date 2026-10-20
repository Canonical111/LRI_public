"""Memory-lean full-basis eps^5 driver (same physics as driver5.py, states processed sequentially).
Refs p0,p1,p3 tuned per variant; then p2, d1 (a1), d2 (a0 a1), d3 (a0^2 a1) one at a time.
Vacuum rows (Dconn, Dfull_raw) from RS vacuum tables at the needed half-integer cutoffs only;
operator part on intermediates = g2D+g3W (= Dconn exactly through eps^3, verified on all states at small L).
Usage: driver5b.py [--pmax 11] cut4 [cut4 ...] -> full5_c{cut4}.json"""
import sys, json, time, gc
import numpy as np
from htb5 import *

K = 5
STATES = {'p0': [], 'p1': [0], 'p2': [0, 0], 'p3': [0, 0, 0], 'd1': [1], 'd2': [0, 1], 'd3': [0, 0, 1]}
REFS = ('p0', 'p1', 'p3')
VARIANTS = ('raw', 'g2D', 'g2D+g3W', 'Dconn', 'Dfull_raw')


def run(cut4, Pmax=11, others=('p2', 'd1', 'd2', 'd3'), verbose=True):
    t0 = time.time()
    sp = Space(cut4, Pmax, None, K, keep_modes=False)
    Lt = cut4 // 4
    S = bubble_S_table(Lt + 2, K)
    Sf = np.array([[float(x) for x in row] for row in S])
    names = list(REFS) + [o for o in others]
    idx = {k: sp.index(STATES[k]) for k in names}
    out = {'cut4': cut4, 'Lambda': cut4 / 4, 'dim': sp.dim, 'Pmax': Pmax, 'variants': {v: {'E': {}} for v in VARIANTS}}
    # ---- refs base and raw tuning orders 1,2
    base = {k: St(sp, idx[k], K) for k in REFS}
    r = np.zeros(K + 1); g = np.zeros(K + 1)
    for n in (1, 2):
        tp = {k: st.source(n, r, g, None) for k, st in base.items()}
        raw = {k: tp[k][base[k].s] for k in base}
        r[n] = ((-.25 if n == 1 else 0.) - (raw['p1'] - raw['p0'])) / 2
        g[n] = ((.25 if n == 1 else 0.) - (raw['p3'] - raw['p0']) - 6 * r[n]) / 3
        for k, st in base.items():
            st.advance(n, tp[k], r[n], g[n], vertex=True)
    coup = {}

    def refs_variant(name, Xb):
        sts = {k: st.fork(2, Xb(g)) for k, st in base.items()}
        rr, gg = r.copy(), g.copy()
        for n in range(3, K + 1):
            rr, gg = run_orders(sts, rr, gg, Xb(gg), n, K, tune=REFS, n_to=n)
        coup[name] = (rr, gg)
        for k, st in sts.items():
            out['variants'][name]['E'][k] = list(map(float, st.E))
        del sts; gc.collect()

    refs_variant('raw', lambda gv: None)
    rraw, graw = coup['raw']
    t1 = time.time()
    # ---- vacuum tables at needed cutoffs (RS on P<=8), raw couplings; eps^5 g4-correction per variant
    jtop = cut4 // 2
    sp8 = Space(2 * jtop, 8, None, K, keep_modes=False)
    jneed = sorted({int(j) for j in half_index(sp.E4[list(idx.values())], cut4)} | {jtop})
    vac = vacuum_tables(sp8, rraw, graw, K, Sf, jneed)
    out['dim8'] = sp8.dim
    out['vac'] = {str(j): {k: v.tolist() for k, v in d.items()} for j, d in vac.items()}
    del sp8; gc.collect()
    t2 = time.time()
    g1 = graw[1]

    def Xtab(kind):
        def b(gv):
            X = g2D3W_diag(sp.E4, gv, cut4, Sf, K); X[:, 4:] = 0.
            for k, i in idx.items():
                j = int(half_index(np.array([sp.E4[i]]), cut4)[0])
                row = np.array(vac[jtop][kind]) - np.array(vac[j][kind])
                row[5] += 2 * g1 * (gv[4] - graw[4]) * (vac[jtop][kind][2] - vac[j][kind][2]) / g1 ** 2
                assert abs(row[2] - X[i, 2]) < 1e-12 and abs(row[3] - X[i, 3]) < 1e-12, (k, row, X[i])
                X[i, 4:] = row[4:]
            return X
        return b

    XB = {'raw': lambda gv: None,
          'g2D': lambda gv: g2D_diag(sp.E4, gv, cut4, Sf, K),
          'g2D+g3W': lambda gv: g2D3W_diag(sp.E4, gv, cut4, Sf, K),
          'Dconn': Xtab('conn'), 'Dfull_raw': Xtab('raw')}
    for v in VARIANTS[1:]:
        refs_variant(v, XB[v])
    del base; gc.collect()
    t3 = time.time()
    # ---- other states, one at a time
    for k in others:
        st0 = St(sp, idx[k], K)
        for n in (1, 2):
            t = st0.source(n, r, g, None)
            st0.advance(n, t, r[n], g[n], vertex=True)
        for v in VARIANTS:
            rr, gg = coup[v]
            X = XB[v](gg)
            st = st0.fork(2, X)
            run_orders({k: st}, rr, gg, X, 3, K, tune=None)
            out['variants'][v]['E'][k] = list(map(float, st.E))
            if X is not None:
                out['variants'][v].setdefault('Xrow', {})[k] = X[idx[k]].tolist()
            del st, X
        del st0; gc.collect()
    for v in VARIANTS:
        d = out['variants'][v]; E = {k: np.array(x) for k, x in d['E'].items()}
        d['r'] = coup[v][0].tolist(); d['g'] = coup[v][1].tolist()
        if 'p2' in E:
            d['C'] = (E['p2'] - E['p0']).tolist()
        for p in (1, 2, 3):
            if 'd%d' % p in E:
                d['spacing_d%d' % p] = (E['d%d' % p] - E['p%d' % p]).tolist()
    out['seconds'] = {'total': time.time() - t0, 'refs_raw': t1 - t0, 'vac': t2 - t1, 'refs_var': t3 - t2}
    if verbose:
        print(f"cut4={cut4} Lam={cut4/4} dim={sp.dim} dim8={out['dim8']} t={ {a: round(b, 1) for a, b in out['seconds'].items()} }", flush=True)
        for v, d in out['variants'].items():
            s = f"  {v:10s} r45={d['r'][4]:+.12f},{d['r'][5]:+.10f} g45={d['g'][4]:+.12f},{d['g'][5]:+.10f}"
            if 'C' in d: s += f" C4={d['C'][4]:.12f} C5={d['C'][5]:.10f}"
            if 'spacing_d1' in d: s += f" d1={np.array(d['spacing_d1'][3:])}"
            print(s, flush=True)
    return out


if __name__ == '__main__':
    args = sys.argv[1:]
    Pmax = 11
    if args and args[0] == '--pmax':
        Pmax = int(args[1]); args = args[2:]
    for c in [int(a) for a in args]:
        o = run(c, Pmax=Pmax)
        json.dump(o, open(f'full5_c{c}.json', 'w'), indent=1)
        gc.collect()
