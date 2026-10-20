import json, glob, numpy as np, mpmath as mp, sys
mp.mp.dps=40
def load():
    D={}
    for f in glob.glob('vacwin_L*.json'):
        w=json.load(open(f)); L=w['L']; E=w['E']; j=2*L
        c=lambda jj: np.array(E[str(jj)]['conn'])
        D[L]=dict(A=c(j)-c(j-1), B=c(j)-c(j-2), D3=c(j)-c(j-3), S2w=E[str(j)]['S2g']-E[str(j-3)]['S2g'])
    return D
def fit(Ls, y, funcs):
    X=mp.matrix([[f(mp.mpf(L)) for f in funcs] for L in Ls]); Y=mp.matrix([mp.mpf(v) for v in y])
    p,res=mp.qr_solve(X,Y)
    r=[float(Y[i]-sum(X[i,k]*p[k] for k in range(len(funcs)))) for i in range(len(Ls))]
    return [float(x) for x in p], max(abs(x) for x in r)
F={'1':lambda L:1,'lg':lambda L:mp.log(L),'1/L':lambda L:1/L,'lg/L':lambda L:mp.log(L)/L,'1/L2':lambda L:1/L**2,'lg/L2':lambda L:mp.log(L)/L**2,
   '1/L3':lambda L:1/L**3,'L-.5':lambda L:L**-0.5,'lgL-.5':lambda L:mp.log(L)*L**-0.5,'lg2/L':lambda L:mp.log(L)**2/L,'lg2':lambda L:mp.log(L)**2,'lg2/L2':lambda L:mp.log(L)**2/L**2,'1/L4':lambda L:1/L**4,'lg2L-.5':lambda L:mp.log(L)**2*L**-0.5,'L-1.5':lambda L:L**-1.5,'lgL-1.5':lambda L:mp.log(L)*L**-1.5}
bases={'a':['1','lg','1/L','lg/L','1/L2','lg/L2'],'a+':['1','lg','1/L','lg/L','1/L2','lg/L2','1/L3'],
       'b':['1','1/L','lg/L','1/L2','lg/L2','1/L3'],'b+':['1','1/L','lg/L','lg2/L','1/L2','lg/L2','1/L3'],
       'c':['1','lg','L-.5','1/L','lg/L','1/L2'],'d':['1','lg','lg2/L','lg/L','1/L','1/L2','lg/L2'],
       'e':['1','lg','lg2','1/L','lg/L','1/L2','lg/L2'],'f':['1','L-.5','lgL-.5','1/L','lg/L','1/L2']}
if __name__=='__main__':
    D=load(); Ls=sorted(D)
    for q,k in (('A',5),('B',5),('A',4),('B',4)):
        print(f'--- {q}{k}  (Lmax={Ls[-1]})')
        for lo in (24,32,40):
            sel=[L for L in Ls if L>=lo]
            for bn,b in bases.items():
                p,res=fit(sel,[D[L][q][k] for L in sel],[F[x] for x in b])
                s=' '.join(f'{n}={v:+.6g}' for n,v in zip(b,p))
                print(f'lo={lo:2d} {bn:3s} res={res:.1e}  {s}')
