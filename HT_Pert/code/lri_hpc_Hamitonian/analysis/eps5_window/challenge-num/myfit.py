"""Skeptic's own re-implementation of the campaign thermal fit (no import of analyze_joint / diagnose_systematic code;
only the raw JSON rows and the reconciled correction table are read).

Order-k target (k=4,5): y_k(L) = C_k(L) + sum_{j=1}^{k-2} e_j(L) (C_{k-j}(L) - lim_{k-j}),  e = coefficients of
exp(log L * sum_j w_j eps^j) with w from the extended gap reference; design [1, x=C2(L)-C2inf, L^-p log^j L ...].
"""
import json, math, sys
import numpy as np

EXT = '<PROJECT>/lri_hpc_Hamitonian/analysis/extended'
RC = '<TMP>/scratchpad/eps5/reconcile'
EX4, EX5 = 45.42488010356, -731.13947662454
C2INF = (math.pi + 4 * math.log(2)) / 9
C3INF = -3.71985632290183342249
BASES = {
    'A': [(1, 0), (1.5, 0), (1.5, 1), (2, 0)],
    'B': [(1, 0), (1.5, 0), (1.5, 1), (2, 0), (2, 1)],
    'C': [(1, 0), (1, 1), (1.5, 0), (1.5, 1)],
    'D': [(1, 0), (1, 1), (1.5, 0), (1.5, 1), (2, 0)],
    'E': [(1, 0), (1, 1), (1.5, 0), (1.5, 1), (2, 0), (2, 1)],
    'F': [(1, 0), (1.5, 0), (1.5, 1), (1.5, 2), (2, 0)],
}


def rows():
    out = {}
    for f in ('thermal_new.json', 'prior_c7/C7_completed_runs.json', 'C7_extension.json'):
        try:
            for r in json.load(open(f'{EXT}/{f}')):
                out[r['cutoff']] = r
        except FileNotFoundError:
            pass
    Ls = sorted(out)
    return np.array(Ls, float), np.array([out[l]['C'][:6] for l in Ls])


def ecoef(L, w, kmax):
    z = np.log(L)
    e = [np.ones_like(z)]
    for k in range(1, kmax + 1):
        e.append(sum(z * j * w[j] * e[k - j] for j in range(1, k + 1)) / k)
    return e


def solve(X, y):
    s = np.linalg.norm(X, axis=0)
    Q, R = np.linalg.qr(X / s)
    p = np.linalg.solve(R, Q.T @ y) / s
    # intercept gain: l1 norm of the row of the pseudo-inverse giving p[0]
    pinv = np.linalg.solve(R, Q.T) / s[:, None]
    return p, float(np.max(np.abs(X @ p - y))), float(np.sum(np.abs(pinv[0])))


def fit(L, C, terms4, terms5, w, extra5=None):
    x = C[:, 2] - C2INF
    lim = {2: C2INF, 3: C3INF}
    info = {}
    for k, terms in ((4, terms4), (5, terms5)):
        e = ecoef(L, w, k - 2)
        y = C[:, k] + sum(e[j] * (C[:, k - j] - lim[k - j]) for j in range(1, k - 1))
        cols = [np.ones_like(L), x] + [L ** (-p) * np.log(L) ** j for p, j in terms]
        X = np.column_stack(cols)
        p, res, gain = solve(X, y)
        lim[k] = p[0]; info[k] = (res, gain)
    return lim, info


if __name__ == '__main__':
    L, C = rows()
    assert list(L) == list(range(2, 119, 2)), L
    T = {int(k): v for k, v in json.load(open(RC + '/dC_reconciled.json')).items()}
    w = {int(k): v for k, v in json.load(open(EXT + '/extended_summary.json'))['gap_reference']['extended'].items()}
    col = lambda key: np.array([T[int(l)][key] for l in L])
    z = np.log(L); a = 1 / 17496.; b5 = 5.5388e-4
    d4 = col('dC4_Dconn'); d5 = col('dC5_Dconn')
    data = {}
    data['raw'] = C.copy()
    X = C.copy(); X[:, 4] += d4; X[:, 5] += d5; data['full'] = X
    X = C.copy(); X[:, 4] += d4 - a * z; X[:, 5] += d5 - (b5 - 2 * a) * z; data['MS'] = X
    X = C.copy(); X[:, 5] += d5; data['C5only'] = X                       # inconsistent: C4 uncorrected
    X = C.copy(); X[:, 4] += d4; X[:, 5] += d5 - (b5 - 2 * a) * z; data['C4full_C5MS'] = X
    X = C.copy(); X[:, 4] += d4 - a * z; X[:, 5] += d5; data['C4MS_C5full'] = X
    print('basis lo   ' + ' '.join(f'{k:>12s}' for k in data) + '   res5(raw/full)  gain5   C4(full)')
    out = {}
    for lo in (16, 40, 50, 60, 70):
        m = L >= lo
        for b in 'ABCDEF':
            r = {k: fit(L[m], D[m], BASES[b], BASES[b], w) for k, D in data.items()}
            out[(b, lo)] = r
            print(f'{b:5s} {lo:3d} ' + ' '.join(f'{r[k][0][5]:12.4f}' for k in data) +
                  f"   {r['raw'][1][5][0]:.1e}/{r['full'][1][5][0]:.1e} {r['full'][1][5][1]:.1e} {r['full'][0][4]:.5f}")
    print()
    for lo in (40, 50, 60, 70):
        e = out[('E', lo)]; A = out[('A', lo)]
        print(f"lo={lo}: E full {e['full'][0][5]:.4f} (miss {e['full'][0][5]-EX5:+.4f}), MS {e['MS'][0][5]:.4f}; shift full-raw {e['full'][0][5]-e['raw'][0][5]:+.4f};"
              f" A full {A['full'][0][5]:.4f} (miss {A['full'][0][5]-EX5:+.4f}); A-F spread full {max(out[(b,lo)]['full'][0][5] for b in 'ABCDEF')-min(out[(b,lo)]['full'][0][5] for b in 'ABCDEF'):.3f}"
              f" raw {max(out[(b,lo)]['raw'][0][5] for b in 'ABCDEF')-min(out[(b,lo)]['raw'][0][5] for b in 'ABCDEF'):.3f}")
