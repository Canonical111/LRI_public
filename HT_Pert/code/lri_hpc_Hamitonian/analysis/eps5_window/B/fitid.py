"""Extrapolate eps^4/eps^5 descendant spacings (dphi: a1 vs a0; dphi2: a0a1 vs a0^2) at even Lambda and Lambda=L+1/4."""
import json, glob, sys, numpy as np, mpmath as mp
mp.mp.dps = 40
def load(phase):
    D = {}
    for f in glob.glob('full5_c*.json'):
        o = json.load(open(f)); c = o['cut4']
        if c % 4 != phase: continue
        D[c // 4] = o['variants']
    return D
def fit(Ls, y, funcs):
    X = mp.matrix([[f(mp.mpf(L)) for f in funcs] for L in Ls]); Y = mp.matrix([mp.mpf(v) for v in y])
    p, _ = mp.qr_solve(X, Y)
    r = [float(Y[i] - sum(X[i, k] * p[k] for k in range(len(funcs)))) for i in range(len(Ls))]
    return [float(v) for v in p], max(abs(v) for v in r)
lg = mp.log
x = lambda L: L ** mp.mpf(-0.5)
B = {
 'P3':  [lambda L: 1, x, lambda L: x(L)**2, lambda L: x(L)**3],
 'P3l': [lambda L: 1, x, lambda L: x(L)*lg(L), lambda L: x(L)**2, lambda L: x(L)**3],
 'P3ll':[lambda L: 1, x, lambda L: x(L)*lg(L), lambda L: x(L)*lg(L)**2, lambda L: x(L)**2, lambda L: x(L)**3],
 'P4l': [lambda L: 1, x, lambda L: x(L)*lg(L), lambda L: x(L)**2, lambda L: x(L)**2*lg(L), lambda L: x(L)**3],
 'P4ll':[lambda L: 1, x, lambda L: x(L)*lg(L), lambda L: x(L)*lg(L)**2, lambda L: x(L)**2, lambda L: x(L)**2*lg(L), lambda L: x(L)**3],
 'LG':  [lambda L: 1, lambda L: lg(L), x, lambda L: x(L)*lg(L), lambda L: x(L)**2, lambda L: x(L)**3],
}
if __name__ == '__main__':
    phase = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    order = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    D = load(phase); Ls = sorted(D)
    print(f'phase {phase}/4, order eps^{order}, L = {Ls[0]}..{Ls[-1]}')
    for key in ('spacing_d1', 'spacing_d2'):
        for v in ('raw', 'g2D', 'g2D+g3W', 'Dconn', 'Dfull_raw'):
            out = []
            for lo in (16, 24, 32):
                sel = [L for L in Ls if L >= lo]
                for bn, b in B.items():
                    if len(sel) < len(b) + 3: continue
                    p, res = fit(sel, [D[L][v][key][order] for L in sel], b)
                    out.append((lo, bn, p[0], res, p[1] if bn == 'LG' else None))
            vals = [o[2] for o in out]
            last = D[Ls[-1]][v][key][order]
            print(f"{key} {v:10s} L={Ls[-1]}: {last:+.5f} | extrap median {np.median(vals):+.4f} range [{min(vals):+.4f},{max(vals):+.4f}] | " +
                  ' '.join(f"{o[0]}/{o[1]}:{o[2]:+.3f}" + (f"(lg{o[4]:+.3f})" if o[4] is not None else '') for o in out if o[0] in (16, 24)))
