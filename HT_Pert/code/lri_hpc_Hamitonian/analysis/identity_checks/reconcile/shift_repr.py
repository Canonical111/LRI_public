import json, math, glob, itertools
import numpy as np
base='<TMP>/scratchpad/identity/'
sh={}
d=json.load(open(base+'B/shift_all.json'))
for l,s in zip(d['L'],d['shift']): sh[int(l)]=s
for f in glob.glob(base+'A/c4shift_*.json'):
    for k,v in json.load(open(f)).items():
        l=int(k); sh[l]=v['dC4']-math.fsum(1/e for e in range(1,l,2))/8748
Ls=np.array(sorted(sh),float); S=np.array([sh[int(l)] for l in Ls])
print('L available:',[int(x) for x in Ls])
def cols(l,terms): return np.column_stack([np.ones_like(l)]+[l**-p*np.log(l)**q for p,q in terms])
cands={
 '1,1l,2,2l':[(1,0),(1,1),(2,0),(2,1)],
 '1,1l,2,2l,3':[(1,0),(1,1),(2,0),(2,1),(3,0)],
 '1,1l,2,2l,3,3l':[(1,0),(1,1),(2,0),(2,1),(3,0),(3,1)],
 '1,1l,1.5,2,2l,3':[(1,0),(1,1),(1.5,0),(2,0),(2,1),(3,0)],
 '1,1l,1.5,2,2l,2.5,3':[(1,0),(1,1),(1.5,0),(2,0),(2,1),(2.5,0),(3,0)],
 '1,1l,2,2l,2l2,3,3l':[(1,0),(1,1),(2,0),(2,1),(2,2),(3,0),(3,1)],
 '1,1l,1l2,2,2l,3,3l':[(1,0),(1,1),(1,2),(2,0),(2,1),(3,0),(3,1)],
}
for lo in (16,24,32):
  m=Ls>=lo
  for n,t in cands.items():
    c=np.linalg.lstsq(cols(Ls[m],t),S[m],rcond=None)[0]
    r=np.max(abs(cols(Ls[m],t)@c-S[m]))
    pred=lambda l: float(cols(np.array([float(l)]),t)@c)
    print(f'lo={lo} {n:22s} c0={c[0]:.10f} maxres={r:.1e} pred(118)={pred(118):.12f} pred(92)={pred(92):.12f}')
