"""Independent exact elementary checks of the extended terminal functional."""
import tail_boundary as tb
from math import comb,factorial
from fractions import Fraction as Q
import random,json
F=tb.F
random.seed(73218)
# Regression with archived functional on its original domain.
ntest=0
for _ in range(240):
    num=tuple(F(random.randint(-2,3)) for _ in range(random.randint(1,4)))
    den=((F(-random.randint(1,4)),random.randint(1,4)),)
    H=tb.mt.canon((tuple((F(0),F(random.choice([0,-1,-2]))) for _ in range(random.randint(0,3))),))
    kappa=random.randint(0,1);p=random.choice([0,-1,-2]);m=0 if p==kappa else random.randint(0,2)
    a=tb.functional(num,den,H,kappa,5,p,m);b=tb.mt.functional(num,den,H,kappa,5,p,m)
    assert a==b,(num,den,H,kappa,p,m,a,b)
    ntest+=1
# Independent closed primitive at w=1+z of z^k/(1+z)^p log(1+z)^r/r!.
# The exact primitive is a polynomial-log expression; evaluate its elementary
# expansion, not the hyperlog derivative recurrence used in the target code.
def primitive_terms(k,p,r):
    terms=[]
    for j in range(k+1):
        c=Q((-1)**(k-j)*comb(k,j),factorial(r));power=j-p
        if power==-1:terms.append((0,r+1,c/Q(r+1)))
        else:
            for i in range(r+1):
                terms.append((power+1,r-i,c*Q((-1)**i*factorial(r),factorial(r-i)*(power+1)**(i+1))))
    return terms

def conv(a,b,d):
    out=[Q(0)]*(d+1)
    for i,c in enumerate(a):
        for j,v in enumerate(b):
            if i+j<=d:out[i+j]+=c*v
    return out

def binom(a,k):return comb(a,k) if a>=0 and k<=a else ((-1)**k*comb(k-a-1,k) if a<0 else 0)

def exact_elementary(k,p,r,kap,N,target,lp):
    out=Q(0)
    for a,h,c in primitive_terms(k,p,r):
        if target==kap and lp==0 and h==0:out-=c  # lower w=1
        d=target-kap+a
        if d<0 or h<lp:continue
        # w=(1-(N-1)e)/e, log(w)=-ell+log(1-(N-1)e)
        pol=[Q(1)]
        logs=[Q(0)]+[Q(-(N-1)**j,j) for j in range(1,d+1)]
        for _ in range(h-lp):pol=conv(pol,logs,d)
        coef=sum((v*binom(a,d-j)*(-(N-1))**(d-j) for j,v in enumerate(pol) if j<=d),Q(0))
        out+=c*comb(h,lp)*(-1)**lp*coef
    return out
nel=0
for k in range(4):
 for p in range(1,5):
  for r in range(4):
   num=(F(0),)*k+(F(1),);den=((F(-1),p),);H=tb.mt.canon((tuple((F(0),F(-1)) for _ in range(r)),))
   for kap in [-1,0,1]:
    for target,lp in [(0,0),(-1,0),(-1,1),(-2,0),(-2,1)]:
     ans=tb.functional(num,den,H,kap,5,target,lp)
     ref=exact_elementary(k,p,r,kap,5,target,lp)
     assert str(ans)==str(ref),(k,p,r,kap,target,lp,ans,ref)
     nel+=1
out={'archived_domain_random_cases':ntest,'independent_elementary_primitive_cases':nel,'all_exact_equal':True,'includes_epsilon_minus_one_prefactor':True}
(tb.ROOT/'terminal_regression.json').write_text(json.dumps(out,indent=2));print(out)
