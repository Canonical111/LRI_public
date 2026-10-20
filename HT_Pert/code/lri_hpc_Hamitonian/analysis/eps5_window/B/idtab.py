import json, glob, numpy as np, sys
ph = sys.argv[1] if len(sys.argv)>1 else '0'
files = sorted(glob.glob('full5_c*.json'), key=lambda x:int(x.split('_c')[1][:-5]))
print(f'phase {ph}: spacing d1 (a1 vs a0) at eps^4 | eps^5 ; and d2 (a0a1 vs a0^2) eps^5')
print('  Lam     raw4      g3W4     Dconn4  |   raw5      g2D5    g2D+g3W5   Dconn5   Dfull5  | d2: raw5  g2D+g3W5  Dconn5')
for f in files:
    o=json.load(open(f)); c=o['cut4']
    if (ph=='0' and c%4) or (ph=='1' and c%4!=1): continue
    v=o['variants']
    s=lambda n,k,d='spacing_d1': v[n][d][k]
    print(f"{o['Lambda']:6.2f} {s('raw',4):+.5f} {s('g2D+g3W',4):+.5f} {s('Dconn',4):+.5f} | {s('raw',5):+.5f} {s('g2D',5):+.5f} {s('g2D+g3W',5):+.5f} {s('Dconn',5):+.5f} {s('Dfull_raw',5):+.5f} | {s('raw',5,'spacing_d2'):+.4f} {s('g2D+g3W',5,'spacing_d2'):+.4f} {s('Dconn',5,'spacing_d2'):+.4f}")
