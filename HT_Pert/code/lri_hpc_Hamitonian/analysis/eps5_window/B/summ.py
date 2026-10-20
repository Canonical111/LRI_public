import json, glob, sys
import numpy as np
files = sorted(glob.glob(sys.argv[1] if len(sys.argv)>1 else 'full5_c*.json'), key=lambda x:int(x.split('_c')[1][:-5]))
print('   Lam   dC4[g2D]        dC5[g2D]       dC5[g2D+g3W]   dC5[Dconn]     dC5[Dfull_raw]  | dC5(g3W) /(-2 dC4g2D)')
for f in files:
    o=json.load(open(f)); v=o['variants']; L=o['Lambda']
    C={k:np.array(d['C']) for k,d in v.items()}
    dg=C['g2D']-C['raw']; d3=C['g2D+g3W']-C['raw']; dc=C['Dconn']-C['raw']; dr=C['Dfull_raw']-C['raw']
    print(f"{L:6.2f} {dg[4]:.12f} {dg[5]:.12f} {d3[5]:.12f} {dc[5]:.12f} {dr[5]:.12f} | {(d3[5]-dg[5]):.12f} {(d3[5]-dg[5])/(-2*dg[4]):.6f}  dC4conn {dc[4]:.12f}")
print()
print('  Lam  spacing d1 eps^3, eps^4, eps^5 per variant')
for f in files:
    o=json.load(open(f)); v=o['variants']; L=o['Lambda']
    print(f"{L:6.2f} "+'  '.join(f"{k}: {d['spacing_d1'][3]:+.6f} {d['spacing_d1'][4]:+.6f} {d['spacing_d1'][5]:+.6f}" for k,d in v.items()))
