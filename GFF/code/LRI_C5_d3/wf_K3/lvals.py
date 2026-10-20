"""L-values of eta-product newforms via the standard incomplete-gamma (Lavrik) series; sign eps fixed by self-consistency."""
import mpmath as mp, json, os, sys
def eta_prod(spec, nmax):
    # spec: list of (m, e) for eta(m tau)^e; returns (q-shift numerator/24, coeff list) of prod (q^{m/24} prod (1-q^{mn}))^e
    sh=sum(m*e for m,e in spec)
    assert sh%24==0; off=sh//24
    c=[0]*(nmax+1); c[0]=1
    for m,e in spec:
        for _ in range(abs(e)):
            if e>0:
                for n in range(1,nmax//m+1):
                    step=m*n
                    for i in range(nmax,step-1,-1): c[i]-=c[i-step]
            else:
                for n in range(1,nmax//m+1):
                    step=m*n
                    for i in range(step,nmax+1): c[i]+=c[i-step]
    a=[0]*(nmax+1+off)
    for i in range(nmax+1-off): a[i+off]=c[i]
    return a[:nmax+1]
def Lfun(a,N,k,s,eps):
    x0=2*mp.pi/mp.sqrt(N)
    tot=0
    for n in range(1,len(a)):
        if a[n]==0: continue
        x=x0*n
        tot+=a[n]*(x**(-s)*mp.gammainc(s,x)+eps*x**(-(k-s))*mp.gammainc(k-s,x))
    return tot*(2*mp.pi)**s/(mp.sqrt(N)**s*mp.gamma(s))
FORMS={'E32':([(4,2),(8,2)],32,2),'f16w3':([(4,6)],16,3),'f8w3':([(1,2),(2,1),(4,1),(8,2)],8,3),'g8w4':([(2,4),(4,4)],8,4),'E64':([(8,2),(4,-1),(16,-1)],64,2) }
def build(dps):
    fn='lvals_%d.json'%dps
    if os.path.exists(fn):
        return {k:mp.mpf(v) for k,v in json.load(open(fn)).items()}
    mp.mp.dps=dps+20
    out={}
    for name,(spec,N,k) in FORMS.items():
        nmax=int((dps+30)*2.31*mp.sqrt(N)/(2*mp.pi))+20
        try:
            a=eta_prod(spec,nmax)
        except AssertionError:
            print('skip',name); continue
        # choose eps by consistency at s=k/2+0.3 vs s mirrored: Lambda(s)=eps Lambda(k-s) holds by construction; instead compare with Dirichlet at large s
        s=mp.mpf(k)+3
        with mp.workdps(30):
            direct=mp.fsum(a[n]*mp.mpf(n)**(-s) for n in range(1,min(len(a),4000)))
            e=min((1,-1),key=lambda ep: abs(Lfun(a[:200],N,k,s,ep)-direct))
            err=abs(Lfun(a[:200],N,k,s,e)-direct)
        print(name,'eps',e,'check',mp.nstr(err,3),'a[1..10]',a[1:11],flush=True)
        for sv in range(1,k+3):
            out['L_%s_%d'%(name,sv)]=Lfun(a,N,k,mp.mpf(sv),e)
    json.dump({kk:mp.nstr(v,dps+10) for kk,v in out.items()},open(fn,'w'))
    return out
if __name__=='__main__':
    o=build(int(sys.argv[1]))
    for kk,v in o.items(): print(kk,mp.nstr(v,20))
