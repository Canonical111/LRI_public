import json, numpy as np, mpmath as mp
from fitwin import load, fit, F, bases
D=load(); Ls=sorted(D)
train=[L for L in Ls if 40<=L<=80]; test=[L for L in Ls if L>80]
for q in ('A','B'):
    print('---',q,'5: predict', test)
    for bn,b in bases.items():
        p,res=fit(train,[D[L][q][5] for L in train],[F[x] for x in b])
        pred=[sum(pi*float(F[x](mp.mpf(L))) for pi,x in zip(p,b)) for L in test]
        err=[pr-D[L][q][5] for pr,L in zip(pred,test)]
        # extrapolate to 118
        p118=sum(pi*float(F[x](mp.mpf(118))) for pi,x in zip(p,b))
        print(f'{bn:3s} res={res:.1e} errs='+' '.join(f'{e:+.1e}' for e in err)+f'  pred118={p118:.10f}')
