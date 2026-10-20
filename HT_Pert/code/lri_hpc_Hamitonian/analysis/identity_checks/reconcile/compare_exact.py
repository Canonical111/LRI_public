"""A (float, package kernels) vs B exact rationals at L=8,12,16 for all common prescriptions."""
import json
from fractions import Fraction as F
base='<TMP>/scratchpad/identity/'
A=json.load(open(base+'A/analysis_table.json'))
vmap={'raw':'raw','g2D':'g2D','Dfull':'Dfull_raw','Dconn':'Dfull_c'}
worst=0; n=0
for L in (8,12,16):
    e=json.load(open(base+f'B/exact_L{L}.json'))
    for va,vb in vmap.items():
        if vb not in e['variants']: print('missing',L,vb); continue
        b=e['variants'][vb]; a=A[str(L)][va]
        pairs=[('r4',a['r4'],b['r4']),('g4',a['g4'],b['g4'])]+[(f'C{k}',a['C'][k],b['C'][k]) for k in (2,3,4)]
        for s,key in (('dphi1','spacing_d1'),('dphi2','spacing_d2'),('dphi3','spacing_d3')):
            for k in (2,3,4): pairs.append((f'{s}_e{k}',a[s][k],b[key][k]))
        for nm,x,y in pairs:
            yv=float(F(y)); d=abs(x-yv)/max(1,abs(yv)); n+=1
            if d>worst: worst=d; wl=(L,va,nm,x,yv)
print('exact-vs-A comparisons:',n,' worst rel diff %.1e at'%worst, wl)
