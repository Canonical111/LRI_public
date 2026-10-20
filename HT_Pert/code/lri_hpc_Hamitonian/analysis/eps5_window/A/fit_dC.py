"""Large-L form of Delta C4, Delta C5 (prescription - raw) from dC_table.json:
 fits c + b log L + tails (several tail sets, Lmin), and the same with b fixed to 0.  Also the pieces
 g3W part (= -2 dC4_g2D), Dconn - g2D3W, Dfull - Dconn."""
import json
import numpy as np
T = json.load(open('dC_table.json'))['table']
Ls = np.array(sorted(int(k) for k in T), float)
get = lambda pres, q: np.array([T[str(int(L))][pres][q] for L in Ls])
series = {
    'dC4 g2D': get('g2D', 'dC4'),
    'dC4 Dconn': get('Dconn', 'dC4'),
    'dC4 Dconn-g2D': get('Dconn', 'dC4') - get('g2D', 'dC4'),
    'dC5 g2D': get('g2D', 'dC5'),
    'dC5 g2D3W': get('g2D3W', 'dC5'),
    'dC5 g3W part (g2D3W-g2D)': get('g2D3W', 'dC5') - get('g2D', 'dC5'),
    'dC5 Dconn': get('Dconn', 'dC5'),
    'dC5 Dconn-g2D3W': get('Dconn', 'dC5') - get('g2D3W', 'dC5'),
    'dC5 Dfull-Dconn': get('Dfull', 'dC5') - get('Dconn', 'dC5'),
    'dC4 Dfull-Dconn': get('Dfull', 'dC4') - get('Dconn', 'dC4'),
}
TAILS = {
    't1': lambda L: [L ** -.5, L ** -1, np.log(L) * L ** -.5, L ** -1.5, np.log(L) / L],
    't2': lambda L: [L ** -.5, L ** -1, L ** -1.5, np.log(L) / L, L ** -2],
    't3': lambda L: [L ** -.5, np.log(L) * L ** -.5, L ** -1, np.log(L) / L, L ** -1.5, np.log(L) * L ** -1.5],
    't4': lambda L: [L ** -1, np.log(L) / L, L ** -2, np.log(L) / L ** 2, L ** -3],
}
out = {}
for name, y in series.items():
    res = []
    for tn, tf in TAILS.items():
        for lo in (24, 40, 56):
            m = Ls >= lo
            for withlog in (True, False):
                L = Ls[m]
                cols = [L ** 0] + ([np.log(L)] if withlog else []) + tf(L)
                X = np.column_stack(cols); s = np.linalg.norm(X, axis=0)
                p = np.linalg.lstsq(X / s, y[m], rcond=None)[0] / s
                r = float(np.max(np.abs(X @ p - y[m])))
                res.append(dict(tail=tn, lo=lo, log=withlog, c=float(p[0]), b=float(p[1]) if withlog else 0., res=r))
    best = min(r['res'] for r in res if r['log'])
    goodL = [r for r in res if r['log'] and r['res'] <= 30 * best]
    bestn = min(r['res'] for r in res if not r['log'])
    goodN = [r for r in res if not r['log'] and r['res'] <= 30 * bestn]
    out[name] = dict(with_log=dict(c=[min(r['c'] for r in goodL), max(r['c'] for r in goodL)],
                                   b=[min(r['b'] for r in goodL), max(r['b'] for r in goodL)], best_res=best),
                     no_log=dict(c=[min(r['c'] for r in goodN), max(r['c'] for r in goodN)], best_res=bestn),
                     at118=float(y[-1]), all=res)
    o = out[name]
    print(f"{name:26s} L=118: {y[-1]:+.10f} | c+b logL: c {o['with_log']['c'][0]:+.6f}..{o['with_log']['c'][1]:+.6f} b {o['with_log']['b'][0]:+.2e}..{o['with_log']['b'][1]:+.2e} (res {best:.0e}) | no log: c {o['no_log']['c'][0]:+.6f}..{o['no_log']['c'][1]:+.6f} (res {bestn:.0e})")
json.dump(out, open('fit_dC.json', 'w'), indent=1)
print('1/17496 =', 1 / 17496)
