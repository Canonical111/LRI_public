"""Fresh independent summation and elliptic-quadrature checks.
The asymptotic tail is an accelerator, not an interval certificate. The separate
explicit direct-tail inequality in DERIVATION.md applies to exact partial sums.
"""
from pathlib import Path
from fractions import Fraction as F
import time,json,sys
from functools import lru_cache
import sympy as s
import mpmath as mp
ROOT=Path(__file__).resolve().parent
@lru_cache(None)
def asymptotic_coefficients(J):
    # g(n)=Gamma(x+1/4)/Gamma(x+3/4), x=n+1/4.
    b=[s.S.Zero]+[-2*s.bernoulli(2*j+1,s.Rational(1,4))/(2*j*(2*j+1)) for j in range(1,J+1)]
    def mul(a,b):return [sum(a[j]*b[k-j] for j in range(k+1)) for k in range(J+1)]
    def expmul(m):
        c=[s.S.One]
        for k in range(1,J+1):c.append(s.expand(sum(j*m*b[j]*c[k-j] for j in range(1,k+1))/k))
        return c
    D=[s.Rational(1,2)]+[2*j*(2*j+1)*b[j] for j in range(1,J+1)]
    H=[s.Rational(1,4)]+[j*b[j] for j in range(1,J+1)]
    T=[(2*j+2)*D[j] for j in range(J+1)]
    E4,E6=expmul(4),expmul(6)
    cd=mul(E4,D);c6=[4*x for x in mul(E6,D)]
    inner=[8*a+b for a,b in zip(mul(H,D),T)]
    cc=mul(E4,inner)
    cw=[8*a+5*b for a,b in zip(cd,c6)]
    return {key:tuple(F(int(c.p),int(c.q)) for c in values) for key,values in [('T4',cd),('D6',c6),('Csum',cc),('Wraw',cw)]}

def rat(v):return mp.mpf(v.numerator)/v.denominator

def series(N,J):
    a=mp.mpf(1);h=mp.log(2);de=mp.pi**2/3;ta=12*mp.zeta(3)
    out={key:mp.mpf(0) for key in ['T4','D6','Csum','Wraw']}
    for n in range(N):
        w4=a**4;q6=(4*n+1)*a**6
        out['T4']+=w4*de;out['D6']+=q6*de
        out['Csum']+=w4*(8*h*de+ta)
        out['Wraw']+=(8*w4+5*mp.pi*q6)*de
        h+=mp.mpf(1)/(2*n+2)-mp.mpf(1)/(2*n+1)
        de-=mp.mpf(4)/(2*n+1)**2-mp.mpf(1)/(n+1)**2
        ta-=mp.mpf(16)/(2*n+1)**3-mp.mpf(2)/(n+1)**3
        a*=mp.mpf(2*n+1)/(2*n+2)
    co=asymptotic_coefficients(J);x=N+mp.mpf(1)/4
    for key in out:
        base=5 if key=='Csum' else 4
        pref=mp.pi**(-3 if key=='D6' else -2)
        out[key]+=pref*mp.fsum(rat(c)*mp.zeta(base+2*j,x) for j,c in enumerate(co[key]))
    out['Wcentral']=out['Wraw']-(8+5*mp.pi)*mp.pi**2/3
    return out

def moment(a,b,i=0,j=0):
    a=mp.mpf(a);b=mp.mpf(b);end=mp.root(mp.mpf('.5'),4)
    def f(y):
        if not y:return mp.mpf(0)
        t=y**4;v=1-t;lt=4*mp.log(y);lv=mp.log1p(-t)
        prod=1/(mp.agm(1,mp.sqrt(v))*mp.agm(1,y*y))
        return 4*y**3*prod*(t**(a-1)*v**(b-1)*lt**i*lv**j+t**(b-1)*v**(a-1)*lv**i*lt**j)
    return mp.quad(f,[0,end/2,end])

def original_wpositive():
    end=mp.root(mp.mpf('.5'),4)
    def f(y):
        if not y:return mp.mpf(0)
        t=y**4;v=1-t;lt=4*mp.log(y);lv=mp.log1p(-t)
        prod=1/(mp.agm(1,mp.sqrt(v))*mp.agm(1,y*y))
        factor=(8*lt**2-8*mp.pi**2)/mp.sqrt(t)+(8*lv**2-8*mp.pi**2)/mp.sqrt(v)
        factor+=(10*(lt-lv)**2-10*mp.pi**2)/mp.sqrt(t*v)
        return 4*y**3*prod*factor
    return mp.quad(f,[0,end/2,end])

def direct(N):
    a=mp.mpf('.5');de=mp.pi**2/3-3;total=mp.mpf(0)
    for n in range(1,N):
        total+=a**4*(8+5*mp.pi*(4*n+1)*a**2)*de
        de-=mp.mpf(4)/(2*n+1)**2-mp.mpf(1)/(n+1)**2
        a*=mp.mpf(2*n+1)/(2*n+2)
    return total

def main(dps,N,J):
    mp.mp.dps=dps;st=time.time();val=series(N,J)
    val2=series(N+40,J+8)
    wp=original_wpositive()
    Bs=4*mp.pi**2*moment('.5','.5');Bd=4*mp.pi**2*moment('.5',1)
    Q=mp.gamma(mp.mpf('.25'))**4/mp.pi
    K=5*Bd/(2*mp.pi)-5*Bs/(4*mp.pi)+6*mp.pi**2+mp.mpf(14733)/4480+81920*mp.catalan/Q**2-mp.mpf(1079926784)/(13125*Q**2)
    W10=K-val['Wraw']
    # Independent old-kernel assembly, before the new centralization.
    Wres=wp-4*mp.pi**3/3-mp.mpf(2480)*mp.zeta(5)/(3*mp.pi**2)
    KT=mp.mpf(5)/2*Bd-mp.mpf(5)/4*Bs+mp.mpf(14)/3*mp.pi**3-mp.mpf(9)/10*mp.pi+81920*mp.pi*(mp.catalan-1)/Q**2-mp.mpf(8192)/625*mp.pi/Q**2-mp.mpf(2480)*mp.zeta(5)/(3*mp.pi**2)
    WT=(Wres-KT)/mp.pi
    oldW10=mp.mpf(3753)/896-mp.mpf(4554752)/(13125*Q**2)-WT
    direct_rows=[]
    for NN in [16,64,256,1024]:
        pv=direct(NN);bd=(8+20*mp.pi/3)/(54*(NN-mp.mpf('.75'))**3)
        direct_rows.append({'N':NN,'partial_sum':mp.nstr(pv,25),'observed_remainder':mp.nstr(val2['Wcentral']-pv,12),'exact_truncation_bound_evaluated_floating':mp.nstr(bd,12)})
    out={'working_digits':dps,'N':N,'J':J,'values':{k:mp.nstr(v,dps) for k,v in val.items()},
      'original_kernel_Wpositive':mp.nstr(wp,dps),'Bsum':mp.nstr(Bs,dps),'Bdiff':mp.nstr(Bd,dps),
      'core_harmonic_identity_residual':mp.nstr(val['Csum']-mp.pi**2*val['D6'],25),
      'central_vs_original_integrand_residual':mp.nstr(mp.pi*val['Wraw']-wp,25),
      'accelerator_change':mp.nstr(val2['Wcentral']-val['Wcentral'],25),
      'W10_old':mp.nstr(oldW10,dps),'W10_reduced':mp.nstr(W10,dps),
      'weighted_C6_difference':mp.nstr(393*mp.pi**3*(W10-oldW10)/2187,25),
      'direct_sums':direct_rows,
      'scope':'Fresh floating-point checks, not interval certificates. Asymptotic tail stability is not a proof of the much smaller observed error. The direct-tail inequality is separately proved.',
      'seconds':time.time()-st}
    (ROOT/'results'/f'numerics_{dps}.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2),flush=True)
if __name__=='__main__':main(*map(int,sys.argv[1:]))
