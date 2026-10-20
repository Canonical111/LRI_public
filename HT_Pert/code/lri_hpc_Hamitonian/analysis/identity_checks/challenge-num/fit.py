import json,math,sys
import numpy as np
rows=[json.loads(l) for l in open(sys.argv[1] if len(sys.argv)>1 else 'top_a.jsonl')]
rows=sorted({r['L']:r for r in rows}.values(),key=lambda r:r['L'])
L=np.array([r['L'] for r in rows],float)
Q={k:np.array([r[k] for r in rows]) for k in ('shift','Yc','Z','P8top')}
def X(l,t): 
    z=np.log(l); return np.column_stack([np.ones_like(l)]+[l**-p*z**q for p,q in t])
bases={
 'a {1,2,3}':[(1,0),(2,0),(3,0)],
 'b {1,1l,2,2l}':[(1,0),(1,1),(2,0),(2,1)],
 'c {1,2,2l,3,3l}':[(1,0),(2,0),(2,1),(3,0),(3,1)],
 'd {1,1l,2,2l,3,3l}':[(1,0),(1,1),(2,0),(2,1),(3,0),(3,1)],
 'e {.5,1,1.5,2,2.5}':[(.5,0),(1,0),(1.5,0),(2,0),(2.5,0)],
 'f {.5,1,1l,1.5,2,2l}':[(.5,0),(1,0),(1,1),(1.5,0),(2,0),(2,1)],
 'g {1,1.5,2,2l,2.5,3}':[(1,0),(1.5,0),(2,0),(2,1),(2.5,0),(3,0)],
 'h {1,2,2l,2l2,3,3l}':[(1,0),(2,0),(2,1),(2,2),(3,0),(3,1)],
 'i {0l..}: logL,1,2,2l,3':[(0,1),(1,0),(2,0),(2,1),(3,0)],
}
for key in ('shift','Yc','Z'):
    print('==',key)
    for lo in (24,48,80,120,160):
        for hi in (96,1e9):
            if hi==96 and lo>48: continue
            m=(L>=lo)&(L<=hi)
            if m.sum()<10: continue
            for n,t in bases.items():
                A=X(L[m],t); s=np.linalg.norm(A,axis=0)
                c=np.linalg.lstsq(A/s,Q[key][m],rcond=None)[0]/s
                res=np.max(abs(A@c-Q[key][m]))
                extra=' c(.5)=%.2e'%c[1] if t[0]==(.5,0) else (' c(logL)=%.2e'%c[1] if t[0]==(0,1) else '')
                print(f'lo={lo:3d} hi={int(min(hi,L.max())):3d} n={m.sum():3d} {n:26s} c0={c[0]:.10f} res={res:.1e}{extra}')
