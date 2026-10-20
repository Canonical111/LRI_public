"""Complete Delta C4, Delta C5 (Dconn - raw) at every even L from implementation B's pieces:
 capped-space operator responses (rowresp_*.json) + closed-form window rows (top5.jsonl)."""
import json, glob, math, numpy as np
rr = {}
for f in glob.glob('rowresp_*.json'):
    for k, v in json.load(open(f)).items(): rr[int(k)] = v
top = {}
for line in open('top5.jsonl'):
    r = json.loads(line); top[r['L']] = r
vac = {}
for f in glob.glob('vacwin_L*.json'):
    w = json.load(open(f)); L = w['L']; E = w['E']; j = 2 * L
    c = lambda jj: np.array(E[str(jj)]['conn'])
    vac[L] = dict(A=c(j) - c(j - 1), B=c(j) - c(j - 2))
rows = []
for L in sorted(set(rr) & set(top)):
    x = rr[L]; t = top[L]
    dC4g = x['g2D']['dC'][4]; dC5g = x['g2D']['dC'][5]; dC5g3 = x['g2D+g3W']['dC'][5] - dC5g
    rho5B = x['rowB4']['dC'][5]; rho5A = x['rowA4']['dC'][5]
    A4, B4, A5, B5 = t['A4'], t['B4'], t['A5'], t['B5']
    rows4 = rho5A * A4 + rho5B * B4
    row = dict(L=L, dC4_g2D=dC4g, shift4=-B4 / 3, dC4_Dconn=dC4g - B4 / 3,
               dC5_g2D=dC5g, dC5_g3W=dC5g3, dC5_rows4=rows4, dC5_rows5=-B5 / 3,
               dC5_Dconn=dC5g + dC5g3 + rows4 - B5 / 3, A4=A4, B4=B4, A5=A5, B5=B5, rho5A=rho5A, rho5B=rho5B,
               dr4_Dconn=x['g2D']['dr'][4] - A4 / 2, dg4_Dconn=x['g2D']['dg'][4] + A4 - B4 / 3)
    if L in vac:
        row['check_B5_vs_fullRS'] = B5 - vac[L]['B'][5]; row['check_A5_vs_fullRS'] = A5 - vac[L]['A'][5]
    rows.append(row)
json.dump(rows, open('dC5_table.json', 'w'), indent=1)
keys = list(rows[0].keys())
with open('dC5_table.csv', 'w') as f:
    f.write(','.join(keys) + '\n')
    for r in rows: f.write(','.join(repr(r.get(k, '')) for k in keys) + '\n')
print(' L   dC4_Dconn         dC5_Dconn         dC5_g2D          dC5_g3W          rows4           -B5/3            B5')
for r in rows:
    if r['L'] % 8 == 0 or r['L'] >= 110:
        print(f"{r['L']:3d} {r['dC4_Dconn']:.13f} {r['dC5_Dconn']:.13f} {r['dC5_g2D']:.12f} {r['dC5_g3W']:+.12f} {r['dC5_rows4']:.12f} {r['dC5_rows5']:.12f} {r['B5']:.12f}")
print('max |B5 closed - fullRS| =', max(abs(r.get('check_B5_vs_fullRS', 0)) for r in rows), ' A5:', max(abs(r.get('check_A5_vs_fullRS', 0)) for r in rows))
