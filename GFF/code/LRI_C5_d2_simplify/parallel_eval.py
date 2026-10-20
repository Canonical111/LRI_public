# 70-digit confirmation of the d=2 identities (run on a cluster node). Computes every single sum in parallel, then
#   L2 (gs:Lseries factorized), K2 (gs:Kseries factorized + Fourier-regularized strip limit), and checks
#   L2 + 2 log2 P4(2) = 0, P4(2)=8 pi^3 a b, K2 = 32 G^2 - 28 zeta(3) log2, a=(B- - B+)/(4pi^3), b=(B- + B+)/(8pi^3),
#   Sy=(pi b - 2 a log2)/4, Sxy=pi^2 a/4 + pi log2 b.
import json,sys,time,os,mpmath as mp
from multiprocessing import Pool
DPS=int(sys.argv[1]) if len(sys.argv)>1 else 70
def setp():mp.mp.dps=DPS+10
def robust(g):
    def f(x):
        with mp.workdps(mp.mp.dps+int(mp.log10(abs(x)+10))+15):v=g(mp.mpf(x))
        return +v
    return f
def emsum(g,a,N):
    f=robust(g);head=mp.fsum(f(k) for k in range(a,N));I=mp.quad(f,[N,2*N,4*N,16*N,64*N,mp.inf])
    J=max(6,int(mp.mp.dps*0.45));ders=list(mp.diffs(f,N,2*J));corr=mp.mpf(0);last=None
    for j in range(1,J+1):
        t=mp.bernoulli(2*j)/mp.factorial(2*j)*ders[2*j-1]
        if last is not None and abs(t)>abs(last):break
        corr+=t;last=t
    return head+I+ders[0]/2-corr
def task(spec):
    setp();h=mp.mpf(1)/2;kind=spec[0]
    ratio=lambda k,u,l:mp.exp(mp.loggamma(k+u)-mp.loggamma(k+l))
    if kind=='L':    # c^4 * prod basis^e ; basis x1 x2 x3 y z1 z2 z3
        e=spec[1]
        B=[lambda k:mp.psi(0,k+h)-mp.psi(0,k+1),lambda k:mp.psi(1,k+h)-mp.psi(1,k+1),lambda k:mp.psi(2,k+h)-mp.psi(2,k+1),
           lambda k:mp.psi(0,k+h)-mp.psi(0,h),lambda k:mp.psi(1,k+h),lambda k:mp.psi(2,k+h),lambda k:mp.psi(3,k+h)]
        def f(k):
            v=(ratio(k,h,1)/mp.sqrt(mp.pi))**4
            for i,p in enumerate(e):
                if p:v*=B[i](k)**p
            return v
        return spec,emsum(f,0,max(80,DPS))
    if kind=='K':    # (C|E) * prod basis^e ; basis x1..x4 w0..w3 ; pure w0^p gets omega log^p k/k subtracted
        wt,e=spec[1],spec[2]
        B=[lambda k,j=j:mp.psi(j-1,k+h)-mp.psi(j-1,k+1) for j in (1,2,3,4)]+[lambda k,j=j:mp.psi(j,k+1) for j in (0,1,2,3)]
        W=(lambda k:(ratio(k,h,1)/mp.sqrt(mp.pi))**2) if wt=='C' else (lambda k:(ratio(k,1,mp.mpf(3)/2)*mp.gamma(mp.mpf(3)/2))**2)
        om=1/mp.pi if wt=='C' else mp.pi/4
        pure=all(p==0 for i,p in enumerate(e) if i!=4);p=e[4]
        def A(k):
            v=W(k)
            for i,q in enumerate(e):
                if q:v*=B[i](k)**q
            return v
        Ar=lambda k:A(k)-(om*mp.log(k)**p/k if pure else 0)
        return spec,A(0)+emsum(Ar,1,max(80,DPS))
    if kind=='F':    # F- = 4F3(1/4,1/4,1/2,1/2;3/4,3/4,1;1), F+ = 4F3(3/4,3/4,1/2,1/2;5/4,5/4,1;1)
        u,l=(mp.mpf(1)/4,mp.mpf(3)/4) if spec[1]=='-' else (mp.mpf(3)/4,mp.mpf(5)/4)
        def f(k):return (ratio(k,u,l)*mp.gamma(l)/mp.gamma(u))**2*(ratio(k,h,1)/mp.sqrt(mp.pi))**2
        return spec,emsum(f,0,max(80,DPS))
if __name__=='__main__':
    t0=time.time();setp()
    L=json.load(open('L2_factorized.json'));K=json.load(open('K2_factorized.json'))
    specs={('L',tuple(t[s]))for t in L['terms'] for s in ('m','n')}|{('L',(0,0,0,1,0,0,0)),('L',(1,0,0,1,0,0,0)),('L',(0,0,0,0,1,0,0))}
    specs|={('K',t[w],tuple(t[s])) for t in K['terms'] for w,s in (('mw','m'),('nw','n'))}
    specs|={('F','-'),('F','+')}
    specs=sorted(specs,key=str)
    print(len(specs),'single sums on',os.cpu_count(),'cpus',flush=True)
    # per-sum cache (each finished sum is saved at once; a rerun skips saved ones), so a time limit loses nothing
    cache=f'cache_dps{DPS}';os.makedirs(cache,exist_ok=True);res={}
    fn=lambda s:os.path.join(cache,''.join(c if c.isalnum() or c in '-+' else '_' for c in repr(s))+'.txt')
    for s in specs:
        if os.path.exists(fn(s)):res[s]=mp.mpf(open(fn(s)).read().strip())
    todo=[s for s in specs if s not in res];print(len(res),'cached,',len(todo),'to compute',flush=True)
    if todo:
        with Pool(min(len(todo),os.cpu_count() or 4)) as pool:
            for s,v in pool.imap_unordered(task,todo):
                res[s]=v;tmp=fn(s)+'.tmp';open(tmp,'w').write(str(v));os.replace(tmp,fn(s))
                print('done',s,'%.0fs'%(time.time()-t0),flush=True)
    print('singles done %.0fs'%(time.time()-t0),flush=True)
    setp();h=mp.mpf(1)/2;pi,l2,G,z3=mp.pi,mp.log(2),mp.catalan,mp.zeta(3)
    # L2
    cst={'kappa2':2*(mp.psi(1,1)-mp.psi(1,h)),'psi1h':mp.psi(1,h),'psi3h':mp.psi(3,h)}
    ev=lambda s:mp.mpf(eval(s,{**cst},{})) if any(k in s for k in cst) else mp.mpf(mp.fraction(*map(int,s.split('/'))) if '/' in s else int(s))
    L2=-mp.fsum(ev(t['coef'])*res[('L',tuple(t['m']))]*res[('L',tuple(t['n']))] for t in L['terms'])
    S=lambda e:res[('L',e)]
    a=S((0,)*7);b=-2*S((1,0,0,0,0,0,0))/pi;Sy=S((0,0,0,1,0,0,0));Sxy=4*S((1,0,0,1,0,0,0))+S((0,0,0,0,1,0,0))
    g4=mp.gamma(mp.mpf(1)/4)**4;Bm=g4*res[('F','-')];Bp=64*pi**4/g4*res[('F','+')]
    # K2 (same assembly as eval_K2.py)
    cK={'kappa2':2*(mp.psi(1,1)-mp.psi(1,h)),'kappa4':2*(mp.psi(3,1)-mp.psi(3,h)),'psi1one':mp.psi(1,1),'psi3one':mp.psi(3,1),'cstar':2*mp.psi(0,1)}
    evK=lambda s:mp.mpf(eval(s,{**cK},{})) if any(k in s for k in cK) else mp.mpf(mp.fraction(*map(int,s.split('/'))) if '/' in s else int(s))
    G1=mp.taylor(lambda e:mp.gamma(1-e),0,12);Z1=[(-1)**k*mp.stieltjes(k)/mp.factorial(k) for k in range(12)]
    def Lam(p):
        poly={}
        for j in range(p+2):poly[j]=poly.get(j,0)-G1[p+1-j]/mp.factorial(j)
        poly[0]+=Z1[p];return {j:(-1)**p*mp.factorial(p)*c for j,c in poly.items()}
    def shift(poly,c):
        out={}
        for j,x in poly.items():
            for k in range(j+1):out[k]=out.get(k,0)+x*mp.binomial(j,k)*c**(j-k)
        return out
    def side(wt,e,sgn):
        pure=all(p==0 for i,p in enumerate(e) if i!=4);pol={0:res[('K',wt,e)]}
        if pure:
            om=1/pi if wt=='C' else pi/4
            for j,x in shift(Lam(e[4]),sgn*1j*pi/2).items():pol[j]=pol.get(j,0)+om*x
        return pol
    tot={}
    for t in K['terms']:
        pa=side(t['mw'],tuple(t['m']),-1);pb=side(t['nw'],tuple(t['n']),+1);al=evK(t['coef'])
        for i,x in pa.items():
            for j,y in pb.items():tot[i+j]=tot.get(i+j,0)+al*x*y
    K2=tot[0]+14*z3*l2
    mp.mp.dps=DPS
    chk={'L2':L2,'K2':mp.re(K2),'L2+2log2*P4(=8pi^3ab)':L2+16*pi**3*l2*a*b,
         'K2-(32G^2-28z3log2)':mp.re(K2)-(32*G**2-28*z3*l2),'Im K2':mp.im(K2),
         'logtheta coeffs max':max(abs(x) for j,x in tot.items() if j>0),
         'a-(B- - B+)/(4pi^3)':a-(Bm-Bp)/(4*pi**3),'b-(B- + B+)/(8pi^3)':b-(Bm+Bp)/(8*pi**3),
         'Sy-(pi b-2a log2)/4':Sy-(pi*b-2*a*l2)/4,'Sxy-(pi^2a/4+pi log2 b)':Sxy-(pi**2*a/4+pi*l2*b)}
    for k,v in chk.items():print(f'{k:28s} {mp.nstr(v,DPS-5) if k in ("L2","K2") else mp.nstr(v,5)}')
    json.dump({'dps':DPS,'seconds':time.time()-t0,'checks':{k:str(v) for k,v in chk.items()},'a':str(a),'b':str(b),'B-':str(Bm),'B+':str(Bp),
               'singles':{repr(k):str(v) for k,v in res.items()}},open(f'confirm_dps{DPS}.json','w'),indent=1)
