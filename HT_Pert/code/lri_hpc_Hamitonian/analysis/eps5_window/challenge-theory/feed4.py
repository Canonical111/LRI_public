"""Exact linear feed of hypothetical eps^4 level-local residual defects (delta8 on the P=8 level at E=L, delta6 on the
P=6 level at E=L-1/2) into (i) C5 at even Lambda and (ii) v5(dphi) at Lambda=L+1/4, with r4,g4,r5,g5 retuned exactly as
in A's linear assembly (run5.py), using A's saved first-order coefficients M0, V0, mv1=(dE5/dr4, dE5/dg4).
No odd shell lies in any of the windows involved, so A's 2*g1*dg4*D0win term vanishes."""
import json, numpy as np
A = '<TMP>/scratchpad/eps5/A'
Bt = {r['L']: r for r in json.load(open(A + '/../B/dC5_table.json'))}
def retune(it, X4):
    n = list(it)
    M = {k: it[k]['M0'] for k in n}; V = {k: it[k]['V0'] for k in n}; mv = {k: it[k]['mv1'] for k in n}
    Am = np.array([[M['phi1'] - M['phi0'], V['phi1'] - V['phi0']], [M['phi3'] - M['phi0'], V['phi3'] - V['phi0']]])
    b = -np.array([X4['phi1'] - X4['phi0'], X4['phi3'] - X4['phi0']])
    dr4, dg4 = np.linalg.solve(Am, b)
    e5 = {k: dr4 * mv[k][0] + dg4 * mv[k][1] for k in n}
    b5 = -np.array([e5['phi1'] - e5['phi0'], e5['phi3'] - e5['phi0']])
    dr5, dg5 = np.linalg.solve(Am, b5)
    E5 = {k: e5[k] + dr5 * M[k] + dg5 * V[k] for k in n}
    return E5
rows = []
for L in (16, 24, 32, 40, 48, 56, 60):
    ev = json.load(open(f'{A}/res5_{L}.json'))['items']
    ph = json.load(open(f'{A}/res5_{L}.25.json'))['items']
    out = dict(L=L)
    for lab, (d8, d6) in {'d8': (1., 0.), 'd6': (0., 1.)}.items():
        # even Lambda = L: windows phi1,phi2 -> {L}; phi3 -> {L, L-1/2}
        X = {k: 0. for k in ev}; X['phi1'] = X['phi2'] = d8; X['phi3'] = d8 + d6
        E5 = retune(ev, X); out['C5_' + lab] = E5['phi2'] - E5['phi0']
        # Lambda = L+1/4: phi2, phi3 -> {L}; dphi1 -> {L, L-1/2}
        X = {k: 0. for k in ph}; X['phi2'] = X['phi3'] = d8; X['dphi1'] = d8 + d6
        E5 = retune(ph, X); out['v5ph14_' + lab] = E5['dphi1'] - E5['phi1']
    if L in Bt:
        out['B_rhoA_plus_rhoB'] = Bt[L]['rho5A'] + Bt[L]['rho5B']; out['B_rhoB'] = Bt[L]['rho5B']
    rows.append(out)
    print(f"L={L}: C5 feed = {out['C5_d8']:+.6f} d8 {out['C5_d6']:+.6f} d6 (B: rhoA+rhoB={out.get('B_rhoA_plus_rhoB', float('nan')):+.6f}, rhoB={out.get('B_rhoB', float('nan')):+.6f}) | "
          f"v5(dphi) at L+1/4 feed = {out['v5ph14_d8']:+.2e} d8 {out['v5ph14_d6']:+.2e} d6")
json.dump(rows, open('feed4.json', 'w'), indent=1)
