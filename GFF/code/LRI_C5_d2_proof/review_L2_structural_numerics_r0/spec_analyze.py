import json, sys, mpmath as mp
mp.mp.dps=80
ref={'2/5':'384.99338524641731699999644567798014102292493989134565425443693406100781539983714',
     '1/2':'250.48731558186728553185175688791140716835571092358366654053930763622482567425988',
     '3/5':'229.69474632501046387324936291069661870738729361131655258421136561062700003640701'}
fn=sys.argv[1]; D=json.load(open(fn)); xs=D['x']; x=mp.mpf(xs.split('/')[0])/int(xs.split('/')[1])
I={int(k):mp.mpf(v) for k,v in D['I'].items()}
print('x=',xs,' probe rel diffs (dps vs dps+20):',[mp.nstr(abs(mp.mpf(D['probe'][k])-I[int(k)])/I[int(k)],3) for k in D['probe']])
p=8*x-7; gam=mp.gamma(1-x)/mp.gamma(x)
def total(N, M, fitls):
    # least squares (square solve if len==M) for c_m in I_l = sum c_m (l/2)^(p-2m)
    A=mp.matrix(len(fitls),M); b=mp.matrix(len(fitls),1)
    for i,l in enumerate(fitls):
        lam=mp.mpf(l)/2
        for m in range(M): A[i,m]=lam**(p-2*m)/lam**p
        b[i]=I[l]/lam**p
    c=mp.lu_solve(A,b) if len(fitls)==M else mp.qr_solve(A,b)[0]
    tail=2*sum(c[m]*mp.mpf(2)**(-(p-2*m))*mp.zeta(-(p-2*m),N+1) for m in range(M))
    head=I[0]+2*sum(I[l] for l in range(1,N+1))
    return gam**4*(head+tail)
Nmax=D['N']; big=sorted(l for l in I if l>Nmax)
R=mp.mpf(ref[xs])
for N,M,step in [(1000,10,100),(1000,14,70),(1500,12,100),(2000,10,None),(2000,14,None),(800,16,50)]:
    if step is None: fitls=[Nmax]+big[:M-1]
    else: fitls=list(range(N,Nmax+1,step))[:M] if len(range(N,Nmax+1,step))>=M else None
    if fitls is None or len(fitls)<M: continue
    W=total(N,M,fitls)
    print(f'N={N} M={M} fit={fitls[0]}..{fitls[-1]}  W_spec={mp.nstr(W,55)}  rel diff vs Phi*Sigma: {mp.nstr(abs(W-R)/R,3)}')
