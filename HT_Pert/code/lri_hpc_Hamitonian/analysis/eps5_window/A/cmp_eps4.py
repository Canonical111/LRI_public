"""(d) cross-check of the eps^2..eps^4 numbers of the new eps^5 code against A's earlier outputs
(analysis_table.json: raw/g2D/Dfull/Dconn r4, g4, C, descendant spacings) and the exact shift table."""
import json, sys, glob
A = '<PROJECT>/lri_hpc_Hamitonian/analysis/identity_checks/A/'
tabA = json.load(open(A + 'analysis_table.json'))
top = {}
for line in open('<PROJECT>/lri_hpc_Hamitonian/analysis/identity_checks/challenge-num/top_a.jsonl'):
    d = json.loads(line); top[d['L']] = d
mp = {'raw': 'raw', 'g2D': 'g2D', 'Dconn': 'Dconn', 'Dfull': 'Dfull'}
worst = 0.; n = 0
for f in sorted(glob.glob('res5_*.json')):
    o = json.load(open(f))
    Lam = o['Lam']
    if Lam != int(Lam) or str(int(Lam)) not in tabA: continue
    a = tabA[str(int(Lam))]
    S = o['summary']
    rows = []
    for mine, theirs in mp.items():
        s = S[mine]; t = a[theirs]
        for k in range(2, 5):
            rows.append((mine, 'C%d' % k, s['C'][k], t['C'][k]))
        for nm in ('dphi1', 'dphi2', 'd2phi', 'd3phi'):
            if 'v_' + nm in s and nm in t:
                for k in range(2, 5):
                    rows.append((mine, f'{nm}_e{k}', s['v_' + nm][k], t[nm][k]))
        if mine != 'raw':
            rows.append((mine, 'r4', S['raw']['r'][4] + s['dr4'], t['r4']))
            rows.append((mine, 'g4', S['raw']['g'][4] + s['dg4'], t['g4']))
    mx = 0.
    for (p, q, x, y) in rows:
        rel = abs(x - y) / max(1., abs(y)); mx = max(mx, rel); n += 1
    L = int(Lam)
    sh = S['Dconn']['C'][4] - S['g2D']['C'][4]
    shr = S['Dfull']['C'][4] - S['g2D']['C'][4]
    tsh = top.get(L, {}).get('shift', float('nan')); tshr = top.get(L, {}).get('shift_raw', float('nan'))
    print(f'L={L:3d} {len(rows)} numbers, max rel diff vs A(eps<=4) = {mx:.1e};  C4 shift Dconn-g2D {sh:.13f} vs topsum {tsh:.13f} ({sh-tsh:+.1e}); literal {shr-tshr:+.1e}')
    worst = max(worst, mx)
print('overall', n, 'numbers, worst', worst)
