"""Paired differences Delta C_k (variant - raw), k<=5, at a cutoff cut4, in the capped space P<=7, Q<=4
(exact for every term linear in a diagonal X starting at eps^2, through eps^5: distance-1 states only).
Dconn needs the vacuum window table Tc[j] (j = 2*L'' near the top) for the reference rows (eps^4, eps^5)."""
import numpy as np, json, sys, time
from htb5 import Space, St, run_orders, bubble_S_table, g2D_diag, g2D3W_diag, half_index

K = 5
REFS = ('p0', 'p1', 'p3')


class Capped:
    def __init__(self, cut4):
        t0 = time.time()
        self.cut4 = cut4
        self.sp = sp = Space(cut4, 7, 4, K, keep_modes=False)
        S = bubble_S_table(cut4 // 4 + 2, K)
        self.Sf = np.array([[float(x) for x in row] for row in S])
        self.idx = {'p%d' % p: sp.index([0] * p) for p in range(4)}
        base = {k: St(sp, i, K) for k, i in self.idx.items()}
        r = np.zeros(K + 1); g = np.zeros(K + 1)
        for n in (1, 2):
            tp = {k: st.source(n, r, g, None) for k, st in base.items()}
            raw = {k: tp[k][base[k].s] for k in base}
            r[n] = ((-.25 if n == 1 else 0.) - (raw['p1'] - raw['p0'])) / 2
            g[n] = ((.25 if n == 1 else 0.) - (raw['p3'] - raw['p0']) - 6 * r[n]) / 3
            for k, st in base.items():
                st.advance(n, tp[k], r[n], g[n], vertex=True)
        self.base, self.r, self.g = base, r, g
        self.res = {}
        self.res['raw'] = self.variant(lambda gv: None)
        self.seconds = time.time() - t0

    def variant(self, Xb):
        sts = {k: st.fork(2, Xb(self.g)) for k, st in self.base.items()}
        rr, gg = self.r.copy(), self.g.copy()
        for n in range(3, K + 1):
            Xn = Xb(gg)
            rr, gg = run_orders(sts, rr, gg, Xn, n, K, tune=REFS, n_to=n)
        E = {k: np.array(st.E) for k, st in sts.items()}
        return dict(r=rr, g=gg, C=E['p2'] - E['p0'], E=E)

    def g2D(self, with3W):
        sp = self.sp
        f = g2D3W_diag if with3W else g2D_diag
        return self.variant(lambda gv: f(sp.E4, gv, self.cut4, self.Sf, K))

    def dconn(self, Tc, jtop):
        """Tc: dict j -> Ec(j/2)[0..5] (conn vacuum); rows for the references from Tc; intermediates g2D+g3W."""
        sp = self.sp
        def Xb(gv):
            X = g2D3W_diag(sp.E4, gv, self.cut4, self.Sf, K)
            X[:, 4:] = 0.
            for k, i in self.idx.items():
                j = int(half_index(np.array([sp.E4[i]]), self.cut4)[0])
                row = np.array(Tc[jtop]) - np.array(Tc[j])
                assert abs(row[2] - X[i, 2]) < 1e-12 and abs(row[3] - X[i, 3]) < 1e-12, (k, row, X[i])
                X[i, 4:] = row[4:]
            return X
        return self.variant(Xb)

    def deltas(self, v):
        a = self.res['raw']; b = v
        return dict(dC=(b['C'] - a['C']).tolist(), dr=(b['r'] - a['r']).tolist(), dg=(b['g'] - a['g']).tolist())


def vac_table_from_vacwin(L, path='vacwin_L%d.json'):
    w = json.load(open(path % L))
    return {int(j): v['conn'] for j, v in w['E'].items()}, w


if __name__ == '__main__':
    out = {}
    for L in [int(a) for a in sys.argv[1:]]:
        cp = Capped(4 * L)
        Tc, w = vac_table_from_vacwin(L)
        res = {'L': L, 'dim': cp.sp.dim, 'r3': cp.res['raw']['r'][:4].tolist(), 'g3': cp.res['raw']['g'][:4].tolist()}
        res['g2D'] = cp.deltas(cp.g2D(False))
        res['g2D+g3W'] = cp.deltas(cp.g2D(True))
        res['Dconn'] = cp.deltas(cp.dconn(Tc, 2 * L))
        j = 2 * L
        res['A'] = (np.array(Tc[j]) - np.array(Tc[j - 1])).tolist(); res['B'] = (np.array(Tc[j]) - np.array(Tc[j - 2])).tolist()
        res['seconds'] = cp.seconds
        out[L] = res
        print(f"L={L} dim={cp.sp.dim} dC4 g2D {res['g2D']['dC'][4]:.13f} Dconn {res['Dconn']['dC'][4]:.13f} | dC5 g2D {res['g2D']['dC'][5]:.12f} "
              f"g2D+g3W {res['g2D+g3W']['dC'][5]:.12f} Dconn {res['Dconn']['dC'][5]:.12f}", flush=True)
    tag = '_'.join(sys.argv[1:]) if len(sys.argv) < 6 else f'{sys.argv[1]}-{sys.argv[-1]}'
    json.dump(out, open(f'capped5_{tag}.json', 'w'), indent=1)
