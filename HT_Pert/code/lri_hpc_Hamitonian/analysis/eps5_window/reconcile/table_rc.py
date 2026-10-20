"""Reconciled complete Delta C4, Delta C5 (Dconn - raw) at every even L = 2..118 (+ B's 120..152 for asymptotics).
Pieces (each from the most accurate source):
  g2D   : package lri_eh d5_all delta_C[5] (L=4..118; = A to 6e-14; B has 5e-11 noise); L=2 exact rationals (this dir)
  bubble: -2 * exact g2D delta C4 (lri_eh exact.fast) -- exact identity (A to 1e-13, B exact-rational zero)
  rows4 : rho5A*A4 + rho5B*B4 (B capped space; = A's F_feed to 2e-12)
  rows5 : -B5/3 with B5 from B's closed-form top sums (exact at all L; = A's measured windows to 1.5e-13 at L<=100;
          A's continued values at 102..118 deviate by up to 2e-9 in B5 -> 6.6e-10 in Delta C5)
  shift4: -B4/3 (topsum exact) ; Delta C4 = fast(L) + shift4
L=2: from exact rationals (htb5_exact, cut4=8)."""
import json, sys, math
sys.dont_write_bytecode = True
from fractions import Fraction as F
import numpy as np
S = '<TMP>/scratchpad/eps5'
sys.path.insert(0, '<PROJECT>/lri_eh_hpc/lri_eh')
from exact import fast
P = {int(k): v['delta_C'] for k, v in json.load(open('<PROJECT>/lri_hpc_Hamitonian/analysis/eh_addon_review/physics-impact/d5_all.json')).items()}
B = {r['L']: r for r in json.load(open(S + '/B/dC5_table.json'))}
A = {int(k): v for k, v in json.load(open(S + '/A/dC_table.json'))['table'].items()}
Af = {r['L']: r for r in json.load(open(S + '/A/final_tables.json'))}
e2 = json.load(open(S + '/reconcile/exactL2/exact5_c8.json'))['variants']
fr = lambda v, k: F(v['C'][k])
table = {}
# L=2 exact
d4 = fr(e2['Dconn'], 4) - fr(e2['raw'], 4); d5 = fr(e2['Dconn'], 5) - fr(e2['raw'], 5)
g4 = fr(e2['g2D'], 4) - fr(e2['raw'], 4); g5 = fr(e2['g2D'], 5) - fr(e2['raw'], 5)
w5 = fr(e2['g2D+g3W'], 5) - fr(e2['g2D'], 5)
table[2] = dict(L=2, source='exact rationals (cut4=8)', dC4_g2D=float(g4), shift4=float(d4 - g4), dC4_Dconn=float(d4),
                dC5_g2D=float(g5), dC5_bubble=float(w5), dC5_rows=float(d5 - g5 - w5), dC5_rows4=None, dC5_rows5=None,
                dC5_Dconn=float(d5), dC5_Dfull=float(fr(e2['Dfull_raw'], 5) - fr(e2['raw'], 5)))
assert abs(float(g4) - fast(2)) < 1e-15 and abs(float(w5) + 2 * float(g4)) < 1e-15
for L in range(4, 153, 2):
    if L not in B: continue
    b = B[L]
    g2 = P[L][5] if L in P else b['dC5_g2D']
    dc4 = fast(L)
    bub = -2 * dc4
    r4, r5 = b['dC5_rows4'], b['dC5_rows5']
    rec = dict(L=L, source=('pkg g2D + exact bubble + B rows' if L in P else 'B (g2D capped space) + exact bubble + B rows'),
               dC4_g2D=dc4, shift4=b['shift4'], dC4_Dconn=dc4 + b['shift4'], dC5_g2D=g2, dC5_bubble=bub,
               dC5_rows4=r4, dC5_rows5=r5, dC5_rows=r4 + r5, dC5_Dconn=g2 + bub + r4 + r5, B5=b['B5'], A5=b['A5'],
               A4=b['A4'], B4=b['B4'])
    if L in A:
        rec['A_dC5_Dconn'] = A[L]['Dconn']['dC5']; rec['A_dC5_Dfull'] = A[L]['Dfull']['dC5']
        rec['dC5_Dfull'] = A[L]['Dfull']['dC5'] + (rec['dC5_Dconn'] - A[L]['Dconn']['dC5'])
    rec['B_dC5_Dconn'] = b['dC5_Dconn']
    table[L] = rec
# checks vs exact rationals at L=4,6 (cut4 16, 24)
for L, c in ((4, 16), (6, 24)):
    e = json.load(open(S + f'/reconcile/exactL2/exact5_c{c}.json'))['variants']
    ex5 = float(fr(e['Dconn'], 5) - fr(e['raw'], 5)); ex4 = float(fr(e['Dconn'], 4) - fr(e['raw'], 4))
    print(f'L={L}: reconciled dC5 - exact = {table[L]["dC5_Dconn"] - ex5:+.2e}; dC4 - exact = {table[L]["dC4_Dconn"] - ex4:+.2e}')
# B exact at 8,12,16
for L, c in ((8, 32), (12, 48), (16, 64)):
    e = json.load(open(S + f'/B/exact5_c{c}.json'))['variants']
    ex5 = float(fr(e['Dconn'], 5) - fr(e['raw'], 5))
    print(f'L={L}: reconciled dC5 - exact = {table[L]["dC5_Dconn"] - ex5:+.2e}')
mA = max(abs(table[L]['dC5_Dconn'] - table[L]['A_dC5_Dconn']) for L in table if 'A_dC5_Dconn' in table[L] and L <= 100)
mA2 = max(abs(table[L]['dC5_Dconn'] - table[L]['A_dC5_Dconn']) for L in table if 'A_dC5_Dconn' in table[L] and L > 100)
mB = max(abs(table[L]['dC5_Dconn'] - table[L]['B_dC5_Dconn']) for L in table if L >= 4 and L <= 118)
print(f'reconciled vs A: L<=100 {mA:.1e}, L=102..118 {mA2:.1e}; vs B (L<=118): {mB:.1e}')
json.dump({str(k): v for k, v in sorted(table.items())}, open(S + '/reconcile/dC_reconciled.json', 'w'), indent=1)
with open(S + '/reconcile/dC_reconciled.csv', 'w') as f:
    f.write('L,dC4_g2D,shift4,dC4_Dconn,dC5_g2D,dC5_bubble,dC5_rows4,dC5_rows5,dC5_Dconn,dC5_Dfull_literal\n')
    for L in sorted(table):
        t = table[L]
        f.write(','.join([str(L)] + [('%.13f' % t[k]) if t.get(k) is not None else '' for k in
                                     ('dC4_g2D', 'shift4', 'dC4_Dconn', 'dC5_g2D', 'dC5_bubble', 'dC5_rows4', 'dC5_rows5', 'dC5_Dconn', 'dC5_Dfull')]) + '\n')
print('  L   dC4_Dconn        dC5_g2D          bubble           rows4           rows5           dC5_Dconn')
for L in sorted(table):
    if L > 118: continue
    t = table[L]
    print(f"{L:4d} {t['dC4_Dconn']:.13f} {t['dC5_g2D']:.13f} {t['dC5_bubble']:+.13f} " +
          (f"{t['dC5_rows4']:.13f} {t['dC5_rows5']:.13f}" if t['dC5_rows4'] is not None else f"(rows {t['dC5_rows']:.13f})          ") +
          f" {t['dC5_Dconn']:.13f}")
