# K_2 = 14 zeta(3) log2 + strip-ordered sum_{m,n} g(m,n), g = sum_i alpha_i A_i(m) B_i(n)  (factor_K2.py).
# Strip (diagonal-iterated) order = lim_{theta->0} F(theta), F(theta)=sum_{m,n} g e^{i(m-n)theta}=sum_i alpha_i A_i(z) conj(B_i(z)),
# z=e^{i theta}. Each A(z)= omega*Lambda_p(z)+C_A+o(1), Lambda_p(z)=sum_{m>=1} z^m log^p m/m (only for A=W*psi0(m+1)^p),
# with Lambda_p = (-1)^p p! [eps^p]{Gamma(-eps)w^eps+zeta(1+eps)}+O(w), z=e^{-w}, log w = log(theta) - i pi/2.
import json,sys,time,mpmath as mp
from emsum import emsum
dps=int(sys.argv[1]) if len(sys.argv)>1 else 20
mp.mp.dps=dps+10
h=mp.mpf(1)/2
d=json.load(open('K2_factorized.json'));names=d['names']
const={'kappa2':2*(mp.psi(1,1)-mp.psi(1,h)),'kappa4':2*(mp.psi(3,1)-mp.psi(3,h)),'psi1one':mp.psi(1,1),'psi3one':mp.psi(3,1),'cstar':2*mp.psi(0,1)}
def coef(s):return mp.mpf(eval(s,{**const,'mp':mp},{}) if any(k in s for k in const) else mp.mpf(eval(s.replace('/','*mp.mpf(1)/'),{'mp':mp})))
def Cw(k):return (mp.exp(mp.loggamma(k+h)-mp.loggamma(k+1))/mp.sqrt(mp.pi))**2
def Ew(k):return (mp.exp(mp.loggamma(k+1)-mp.loggamma(k+mp.mpf(3)/2))*mp.gamma(mp.mpf(3)/2))**2
basis=[lambda k,j=j:mp.psi(j-1,k+h)-mp.psi(j-1,k+1) for j in (1,2,3,4)]+[lambda k,j=j:mp.psi(j,k+1) for j in (0,1,2,3)]
omega={'C':1/mp.pi,'E':mp.pi/4}
def single(wt,expo):
    W=Cw if wt=='C' else Ew
    pure=all(p==0 for i,p in enumerate(expo) if i!=4)   # only w0=psi0(k+1) powers -> 1/m log^p m tail
    p=expo[4]
    def A(k):
        v=W(k)
        for i,e in enumerate(expo):
            if e:v*=basis[i](k)**e
        return v
    def Ar(k):return A(k)-(omega[wt]*mp.log(k)**p/k if pure else 0)
    N=max(40,dps)
    val=A(0)+emsum(Ar,1,N)
    return {'pure':pure,'p':p,'omega':omega[wt] if pure else mp.mpf(0),'C':val}
# Lambda_p as polynomial in L=log w: coefficients via eps-series
K=8
G1=mp.taylor(lambda e:mp.gamma(1-e),0,K+2)            # Gamma(-eps) = -(1/eps)Gamma(1-eps)
Z1=[(-1)**k*mp.stieltjes(k)/mp.factorial(k) for k in range(K+2)]   # zeta(1+eps)=1/eps+sum
def Lam(p):
    # returns dict power_of_L -> coeff for (-1)^p p! [eps^p]( -(1/eps)Gamma(1-eps) e^{eps L} + zeta(1+eps) )
    poly={}
    # -(1/eps) sum_a G1[a] eps^a sum_j L^j eps^j/j!  -> coeff of eps^p: -sum_{a+j=p+1} G1[a] L^j/j!
    for j in range(p+2):
        a=p+1-j
        poly[j]=poly.get(j,0)-G1[a]/mp.factorial(j)
    poly[0]=poly.get(0,0)+Z1[p]
    return {j:(-1)**p*mp.factorial(p)*c for j,c in poly.items()}
def polymul(a,b):
    out={}
    for i,x in a.items():
        for j,y in b.items():out[i+j]=out.get(i+j,0)+x*y
    return out
def shift(poly,c):  # substitute L = tau + c, return poly in tau
    out={}
    for j,x in poly.items():
        for k in range(j+1):out[k]=out.get(k,0)+x*mp.binomial(j,k)*c**(j-k)
    return out
t0=time.time();cache={}
def get(wt,e):
    key=(wt,tuple(e))
    if key not in cache:cache[key]=single(wt,e)
    return cache[key]
total={}
for t in d['terms']:
    a=get(t['mw'],t['m']);b=get(t['nw'],t['n']);al=coef(t['coef'])
    pa={0:a['C']}
    if a['pure']:
        for j,x in shift(Lam(a['p']),-1j*mp.pi/2).items():pa[j]=pa.get(j,0)+a['omega']*x
    pb={0:b['C']}
    if b['pure']:
        for j,x in shift(Lam(b['p']),+1j*mp.pi/2).items():pb[j]=pb.get(j,0)+b['omega']*x
    for j,x in polymul(pa,pb).items():total[j]=total.get(j,0)+al*x
K2=total[0]+14*mp.zeta(3)*mp.log(2)
mp.mp.dps=dps
print('tau-power coefficients (must vanish for j>=1):',{j:mp.nstr(abs(x),3) for j,x in sorted(total.items()) if j>0})
print('Im part:',mp.nstr(mp.im(K2),3))
print('K2 =',mp.nstr(mp.re(K2),dps-2),'  (C63d: 3.518109138587)   %.1fs'%(time.time()-t0))
json.dump({'dps':dps,'K2':str(mp.re(K2)),'singles':{f'{k[0]}|'+'|'.join(map(str,k[1])):{'C':str(v['C']),'pure':v['pure'],'p':v['p']} for k,v in cache.items()}},open(f'K2_value_dps{dps}.json','w'),indent=1)
