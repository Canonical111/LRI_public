import json, glob, numpy as np, sys
sys.path.insert(0,'<PROJECT>/lri_eh_hpc/lri_eh')
from exact import exact as dC4exact
files=sorted(glob.glob('big_L*.json'),key=lambda f:int(f[5:-5]))
R=[json.load(open(f)) for f in files]
V=['raw','g2D','g2D+g3W','Dfull_raw','Dfull_c']
print('delta C4 (variant - raw) and check vs exact rational g2D formula')
print(' L   dC4_g2D            exact-diff   dC4_Dfull_raw-g2D   dC4_Dfull_c-g2D   C4raw')
for d in R:
    L=d['L'];c={v:d['variants'][v]['C'][4] for v in V}
    ex=float(dC4exact(L)) if L>=2 else 0
    print(f"{L:3d} {c['g2D']-c['raw']:.15f} {c['g2D']-c['raw']-ex:+.1e} {c['Dfull_raw']-c['g2D']:+.15f} {c['Dfull_c']-c['g2D']:+.15f} {c['raw']:.12f}")
for p in (1,2,3):
  for k in (2,3,4):
    print(f'\nspacing violation dphi^{p} eps^{k}:  '+'  '.join(f'{v:>18s}' for v in V))
    for d in R:
        L=d['L']
        print(f"{L:3d} "+'  '.join(f"{d['variants'][v]['spacing_d%d'%p][k]:+.12e}" for v in V))
