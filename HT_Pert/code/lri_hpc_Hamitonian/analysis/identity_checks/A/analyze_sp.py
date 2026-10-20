"""Single-particle descendants a_n|0>, v_n = E(a_n)-E(a_0)-n, five prescriptions, r4 from main run."""
import json, glob, math
import numpy as np
from analyze import load, prescriptions, Rclosed, extrap

D = load()
P = {L: prescriptions(D[L]) for L in D}
S = {}
for f in glob.glob('sp_L*.json'):
    d = json.load(open(f)); S[d['L']] = d
Ls = sorted(set(S) & set(P))
tab = {}
for L in Ls:
    d = S[L]; tab[L] = {}
    for pres in ('raw', 'g2D', 'Dfull', 'Dconn', 'Dshift'):
        r4 = P[L][pres]['r4']
        E = {}
        for nm, rec in d['states'].items():
            if pres == 'raw': h = np.array(rec['h_raw'])
            elif pres == 'g2D': h = np.array(rec['h_g2D'])
            elif pres in ('Dfull', 'Dconn'):
                h = np.array(rec['h_g2D']) + np.r_[0, 0, 0, np.array(rec['Dfull_s'][3:]) - np.array(rec['g2D_s'][3:])]
                if pres == 'Dconn': h[4] += Rclosed(L) - Rclosed(L - rec['E0'])
            elif pres == 'Dshift':
                h = np.array(rec['h_raw']) + np.r_[0, 0, np.array(rec['Dfull_s'][2:])]
            h = h.copy(); h[4] += r4 * rec['M0']
            E[nm] = h
        for n in range(1, 7):
            v = E[f'a{n}'] - E['a0']; v[0] -= n
            tab[L][(pres, n)] = v
# consistency with the main run (a1=dphi1, a2=d2phi, a3=d3phi)
mx = 0
for L in Ls:
    for pres in ('raw', 'g2D', 'Dfull', 'Dconn', 'Dshift'):
        for n, key in ((1, 'dphi1'), (2, 'd2phi'), (3, 'd3phi')):
            mx = max(mx, np.max(np.abs(tab[L][(pres, n)] - P[L][pres][key])))
print('max diff vs main run (a1,a2,a3):', mx)
W = {n: math.ceil(n / 2) for n in range(1, 7)}
Larr = np.array(Ls, float)
res = {}
for n in range(1, 7):
    for k in (2, 3, 4):
        for pres in ('raw', 'g2D', 'Dfull', 'Dconn'):
            y = np.array([tab[L][(pres, n)][k] for L in Ls])
            r = extrap(Larr, y)
            vals = np.array([v[0] for v in r.values()])
            cen = [r[x][0] for x in r if x[1] == 24 and x[0][0] in 'ab']
            res[(n, k, pres)] = (float(np.mean(cen)), float(vals.min()), float(vals.max()), float(y[-1]))
            print(f'a{n} (level {n}, W={W[n]}) e{k} {pres:6s} L={Ls[-1]}: {y[-1]:+.6f}  extrap {np.mean(cen):+.5f} [{vals.min():+.5f},{vals.max():+.5f}]  per W {np.mean(cen)/W[n]:+.5f}')
json.dump({f'a{n}|{k}|{p}': v for (n, k, p), v in res.items()}, open('analysis_sp_extrap.json', 'w'), indent=1)
json.dump({str(L): {f'{p}|{n}': tab[L][(p, n)].tolist() for (p, n) in tab[L]} for L in Ls}, open('analysis_sp_table.json', 'w'))
