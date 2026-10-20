"""Evaluate the new unit-slope H through its proved inner transform.
Also recompute the old seventh central sum independently. No interval claims.
"""
import json, math, sys, time
from pathlib import Path
import mpmath as mp

def run(dps=45):
    mp.mp.dps=dps
    pi=mp.pi; half=mp.mpf(1)/2; quarter=mp.mpf(1)/4
    ell=mp.log(2); A=pi+4*ell
    a=259*A-49*pi; b=481*A-539*pi; c=407*A-1127*pi
    rho=mp.sqrt((a-c)**2+b*b); disc=mp.sqrt(b*b-4*a*c)
    etas=[mp.atan((b+disc)/(2*a))/pi,mp.atan((b-disc)/(2*a))/pi]
    beta=mp.atan((13+1j*mp.sqrt(139))/14)/pi
    def base(s, shifts):
        ans=(quarter-s)*mp.gamma(s)**3*mp.gamma(half-s)**7*mp.rgamma(1-s)**4
        for h in shifts: ans*=mp.rgamma(s+h)*mp.rgamma(1-s-h)
        return ans
    def outer_h(s):
        ag=(-s)*base(s,[beta,mp.conj(beta)])
        unit_inner=-(mp.digamma(1-2*s)+mp.euler)/(pi*s)
        return ag*unit_inner
    def outer_g(s): return base(s,etas)
    def barnes(f):
        return mp.quad(lambda u:mp.re(f(quarter+1j*u)),[0,quarter,1,2,4,8,16,32,mp.inf])/pi
    start=time.time()
    Hunit=barnes(outer_h); print('Hunit',mp.nstr(Hunit,dps), 'seconds',time.time()-start,flush=True)
    G7=barnes(outer_g); print('G7',mp.nstr(G7,dps), 'seconds',time.time()-start,flush=True)
    N=max(240,4*dps+100)
    # Independent original central-binomial coefficients. Ordinary rounding,
    # not interval arithmetic. The finite Euler tail theorem is inherited.
    total=mp.mpf(0); ac=mp.mpf(1); H=H2=H3=hn=hn2=mp.mpf(0)
    cumulative=0; denominator=1<<N
    zeta3=mp.zeta(3)
    for n in range(N):
        cumulative+=math.comb(N,n)
        weight=mp.mpf(denominator-cumulative)/denominator
        h=ell+hn-H; delta=pi*pi/3-4*H2+2*hn2; y=n+quarter
        u=1-14*y*h; v=196*y*h*h-28*h+7*y*(delta-pi*pi)
        T=80*pi*pi*y-26*pi*u+11*v; K=28*pi*pi*y-10*pi*u+3*v
        F=(98*H+74*ell-6*pi)*T-98*pi*K-98*(11*u-13*pi*y)*(pi*pi/3+4*H2)-8624*y*(zeta3-H3)
        total+=(-1)**n*weight*ac**7*F
        k=n+1; ac*=mp.mpf(2*n+1)/(2*n+2); hn+=mp.mpf(1)/k; hn2+=mp.mpf(1)/(k*k)
        for j in (2*n+1,2*n+2):
            H+=mp.mpf(1)/j; H2+=mp.mpf(1)/(j*j); H3+=mp.mpf(1)/(j*j*j)
    old=24*pi**3*total
    new=24*pi**mp.mpf('1.5')*(rho*G7+196*pi*mp.sqrt(185)*Hunit)
    print('B7',mp.nstr(new,dps)); print('absolute difference',abs(old-new),flush=True)
    record={'working_decimal_digits':dps,'H7_unit':str(Hunit),'H7_old_via_exact_conversion':str(pi*Hunit/2),
            'G7':str(G7),'B7_new':str(new),'B7_central_Euler':str(old),'absolute_difference':str(abs(old-new)),
            'Euler_N':N,'seconds':time.time()-start,'rigorous_interval':False,
            'H_evaluation':'outer gamma-product Barnes integral with new inner transform evaluated in digamma form; direct independent inner-kernel quadratures recorded separately',
            'G_evaluation':'gamma-product Barnes kernel',
            'all_sector_C6_reevaluated':False,'Wolfram_kernel_executed':False}
    (Path(__file__).parent/'results'/f'numerical_{dps}.json').write_text(json.dumps(record,indent=2))
    return record
if __name__=='__main__': run(int(sys.argv[1]) if len(sys.argv)>1 else 45)
