"""Collect desc_L*.json, build five prescriptions, retune r4,g4, extrapolate.
 raw      : raw HT
 g2D      : package isolated g(eps)^2 D(eps) as a diagonal operator (as lri_eh)
 Dfull    : g2D operator + diag at the state of [E_vac(L)-E_vac(L-E0)] - [g^2D]_s at eps^3,eps^4
            (== complete Dfull diagonal OPERATOR through eps^4; verified --fullop)
 Dconn    : Dfull with E_vac -> E_vac + R (vacuum computed with the same g^2D operator, windows
            from L'), i.e. the unlinked bubble-bubble leftover counted once (by the g^2D response)
 Dshift   : raw + final diagonal shift Dfull_s (no operator response)
"""
import json, glob, math, sys
import numpy as np
sys.path.insert(0, '.')
from ht4 import series_eig2

def Rclosed(Lp, g1=1/3):
    s = 0.
    top = int(math.floor(Lp + 1e-9))
    for E in range(1, top + 1, 2):
        n = sum(1 for k in range(1, top + 1) if k % 2 == 1 and Lp - E < k <= Lp)
        s += n / E
    return -(g1**4 / 36) * s

def load(pattern='desc_L*_p*q*.json'):
    D = {}
    for f in glob.glob(pattern):
        d = json.load(open(f))
        L = d['L']
        # prefer the larger basis (more states) if duplicates
        if L not in D or len(d['states']) > len(D[L]['states']):
            D[L] = d
    return D

def prescriptions(d):
    L = d['L']
    out = {}
    for pres in ('raw', 'g2D', 'Dfull', 'Dconn', 'Dshift'):
        H = {}
        for name, rec in d['states'].items():
            n = len(rec['seeds']); I = np.eye(n)
            if pres == 'raw': h = np.array(rec['h_raw'])
            elif pres == 'g2D': h = np.array(rec['h_g2D'])
            elif pres == 'Dfull': h = np.array(rec['h_Dfull'])
            elif pres == 'Dconn':
                h = np.array(rec['h_Dfull']).copy()
                h[4] += (Rclosed(L) - Rclosed(L - rec['E0'])) * I
            elif pres == 'Dshift':
                h = np.array(rec['h_raw']).copy()
                for k in range(2, 5): h[k] += rec['Dfull_s'][k] * I
            H[name] = h
        e = {p: H[f'phi{p}'][:, 0, 0] for p in (0, 1, 3)}
        r4 = -(e[1][4] - e[0][4]) / 2
        g4 = (-(e[3][4] - e[0][4]) - 6 * r4) / 3
        E = {}
        for name, rec in d['states'].items():
            h = H[name].copy()
            h[4] += r4 * np.array(rec['M0']) + g4 * np.array(rec['V0'])
            E[name] = [h[:, 0, 0]] if h.shape[1] == 1 else series_eig2(h)
        s = {'r4': r4, 'g4': g4, 'C': (E['phi2'][0] - E['phi0'][0])}
        for n in range(1, 5):
            if f'dphi{n}' in E and f'phi{n}' in E:
                v = E[f'dphi{n}'][0] - E[f'phi{n}'][0]; v = v.copy(); v[0] -= 1; s[f'dphi{n}'] = v
        if 'd2phi' in E:
            v = E['d2phi'][0] - E['phi1'][0]; v = v.copy(); v[0] -= 2; s['d2phi'] = v
            v = E['d3phi'][0] - E['phi1'][0]; v = v.copy(); v[0] -= 3; s['d3phi'] = v
        if 'P2N2' in E:
            br = [x - E['phi2'][0] for x in E['P2N2']]
            br.sort(key=lambda x: abs(x[1]))
            v = br[0].copy(); v[0] -= 2; s['P2N2desc'] = v
            s['P2N2prim'] = br[1].copy()
        out[pres] = s
    return out

BASES = {
    'a:1,x,x2,x3':        lambda x, L: [x**0, x, x**2, x**3],
    'b:1,x,x2,x3,x4':     lambda x, L: [x**0, x, x**2, x**3, x**4],
    'c:1,x,xlogL,x2,x3':  lambda x, L: [x**0, x, x * np.log(L), x**2, x**3],
    'd:1,x,x2,x2logL,x3': lambda x, L: [x**0, x, x**2, x**2 * np.log(L), x**3],
    'e:1,logL,x,x2,x3':   lambda x, L: [x**0, np.log(L), x, x**2, x**3],
}

def extrap(L, y, lmins=(16, 24, 32), bases=BASES):
    """x = L^-1/2. returns dict (basis,lmin)->(const, maxres)."""
    res = {}
    for bn, b in bases.items():
        for lo in lmins:
            m = L >= lo
            if m.sum() < len(b(L[:1]**-.5, L[:1])) + 3: continue
            X = np.array(b(L[m]**-.5, L[m])).T
            c = np.linalg.lstsq(X, y[m], rcond=None)[0]
            res[(bn, lo)] = (c[0], float(np.max(np.abs(X @ c - y[m]))))
    return res

if __name__ == '__main__':
    D = load()
    Ls = sorted(D)
    P = {L: prescriptions(D[L]) for L in Ls}
    json.dump({str(L): {p: {k: (v.tolist() if hasattr(v, 'tolist') else v) for k, v in s.items()} for p, s in P[L].items()} for L in Ls},
              open('analysis_table.json', 'w'))
    keys = ['dphi1', 'dphi2', 'dphi3', 'dphi4', 'd2phi', 'd3phi', 'P2N2desc']
    print('L range', Ls[0], Ls[-1], 'count', len(Ls))
    final = {}
    for key in keys:
        for k in (2, 3, 4):
            for pres in ('raw', 'g2D', 'Dfull', 'Dconn', 'Dshift'):
                Lk = np.array([L for L in Ls if key in P[L][pres]], float)
                if len(Lk) < 8: continue
                y = np.array([P[int(L)][pres][key][k] for L in Lk])
                r = extrap(Lk, y)
                vals = np.array([v[0] for v in r.values()])
                # central: basis a and b with lmin 24
                cen = [r[x][0] for x in r if x[1] == 24 and x[0][0] in 'ab']
                c0 = float(np.mean(cen)) if cen else float(np.median(vals))
                final[(key, k, pres)] = (c0, float(vals.min()), float(vals.max()), y[-1], int(Lk[-1]))
                print(f'{key:9s} e{k} {pres:6s}  L={int(Lk[-1])}: {y[-1]:+.6f}   extrap central {c0:+.5f}  range [{vals.min():+.5f}, {vals.max():+.5f}]')
    json.dump({f'{a}|{b}|{c}': v for (a, b, c), v in final.items()}, open('analysis_extrap.json', 'w'), indent=1)
