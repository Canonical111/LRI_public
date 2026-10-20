"""Collect the finite-cutoff tables for the report: final_tables.json and printed rows."""
import json, math
import numpy as np
import assemble_c5 as A
T = json.load(open('dC_table.json'))['table']
rows = []
for L in A.Ls:
    t = T[str(L)]
    w = {k: (A.window(L, k, 4), A.window(L, k, 5)) for k in ('W8', 'W6', 'W8r', 'W6r')}
    fx = -(w['W8'][1] + w['W6'][1]) / 3
    extra = t['Dconn']['dC5'] - t['g2D3W']['dC5']
    rows.append(dict(L=L, measured_window=bool(L <= A.Lv),
                     dC4_g2D=t['g2D']['dC4'], dC4_Dconn=t['Dconn']['dC4'], dC4_Dfull=t['Dfull']['dC4'],
                     dC5_g2D=t['g2D']['dC5'], dC5_g2D3W=t['g2D3W']['dC5'], dC5_Dconn=t['Dconn']['dC5'], dC5_Dfull=t['Dfull']['dC5'],
                     W8_4=w['W8'][0], W6_4=w['W6'][0], W8_5=w['W8'][1], W6_5=w['W6'][1], W8raw_5=w['W8r'][1],
                     Dconn5_ref=[0., w['W8'][1], w['W8'][1], w['W8'][1] + w['W6'][1]],
                     F_X5=fx, F_feed=extra - fx, dr4_Dconn_minus_g2D3W=t['Dconn']['dr4'] - t['g2D3W']['dr4'],
                     dg4_Dconn_minus_g2D3W=t['Dconn']['dg4'] - t['g2D3W']['dg4'],
                     dr5_Dconn=t['Dconn']['dr5'], dg5_Dconn=t['Dconn']['dg5']))
json.dump(rows, open('final_tables.json', 'w'), indent=1)
print('  L  dC5(Dconn-raw)     dC5(g2D)       dC5(g2D3W)     dC4(Dconn)     W8_5          W6_5          F(X5)        F(feed)')
for r in rows:
    print(f"{r['L']:4d} {r['dC5_Dconn']:.12f} {r['dC5_g2D']:.12f} {r['dC5_g2D3W']:.12f} {r['dC4_Dconn']:.12f} {r['W8_5']:+.10f} {r['W6_5']:+.10f} {r['F_X5']:.10f} {r['F_feed']:.10f}{'' if r['measured_window'] else ' (window continued)'}")
