"""Decompose Delta C5 (Dconn - g2D3W) on the references into its pieces, from res5_L.json files:
 X_p^(4), X_p^(5) = Dconn rows on p (vacuum window content), retune Delta r4, Delta g4 (Dconn - g2D3W),
 feed-forward Delta r4 m1_p + Delta g4 v1_p, and the retune functional X2-X1+(X0-X3)/3 at eps^5."""
import json, glob, math, sys
import numpy as np
rows = []
for f in sorted(glob.glob(sys.argv[1] if len(sys.argv) > 1 else 'res5_*.json')):
    o = json.load(open(f))
    Lam = o['Lam']
    if Lam != int(Lam): continue
    S = o['summary']; it = o['items']
    X4 = [S['Dconn']['rows'][f'phi{p}'][4] for p in range(4)]
    X5 = [S['Dconn']['rows'][f'phi{p}'][5] for p in range(4)]
    F = lambda X: X[2] - X[1] + (X[0] - X[3]) / 3
    dr4 = S['Dconn']['dr4'] - S['g2D3W']['dr4']; dg4 = S['Dconn']['dg4'] - S['g2D3W']['dg4']
    feed = [dr4 * it[f'phi{p}']['mv1'][0] + dg4 * it[f'phi{p}']['mv1'][1] for p in range(4)]
    dC5 = S['Dconn']['C'][5] - S['g2D3W']['C'][5]
    rows.append((int(Lam), F(X4), F(X5), F(feed), dC5, dC5 - F(X5) - F(feed), dr4, dg4, X5))
rows.sort()
print('  L   F(X4)=dC4     F(X5)         F(feed)       dC5(Dconn-g2D3W)  remainder   dr4        dg4       X5_p')
for r in rows:
    print(f'{r[0]:3d} {r[1]:+.10f} {r[2]:+.10f} {r[3]:+.10f} {r[4]:+.10f} {r[5]:+.1e} {r[6]:+.6f} {r[7]:+.6f} ' + ' '.join(f'{x:+.7f}' for x in r[8]))
