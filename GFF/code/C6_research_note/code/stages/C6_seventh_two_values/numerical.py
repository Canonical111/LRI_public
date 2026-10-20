import mpmath as mp, math, json, sys, time
from pathlib import Path
DPS=int(sys.argv[1]) if len(sys.argv)>1 else 40
mp.mp.dps=DPS
pi=mp.pi;l=mp.log(2);A=pi+4*l;half=mp.mpf('.5');c=mp.mpf('.25')
a=259*A-49*pi;bA=481*A-539*pi;cA=407*A-1127*pi
qdisc=mp.sqrt(bA*bA-4*a*cA)
etas=[mp.atan((bA+qdisc)/(2*a))/pi,mp.atan((bA-qdisc)/(2*a))/pi]
beta=mp.atan((13+1j*mp.sqrt(139))/14)/pi
rho=mp.sqrt((a-cA)**2+bA*bA)
print('real shifts',list(map(str,etas)),flush=True)
print('complex shift',beta,'rho',rho,flush=True)

def barnes(f):
    return mp.quad(lambda v: mp.re(f(c+1j*v)),[0,mp.mpf('.25'),1,2,4,8,16,32,mp.inf])/pi

def rp(s):
    z=mp.tan(pi*s)
    return (mp.gamma(s)/mp.gamma(s+half))**7/mp.cos(pi*s)*z**4*(c-s)

def hg(s):
    den=mp.gamma(1-s)**3*mp.gamma(-s)*mp.gamma(c-s)
    for b in (beta,mp.conj(beta)): den*=mp.gamma(s+b)*mp.gamma(1-s-b)
    ag=mp.gamma(s)**3*mp.gamma(half-s)**7*mp.gamma(1+c-s)/den
    return ag*(mp.digamma(1-2*s)+mp.euler)/(-2*s)

def gg(s):
    den=mp.gamma(1-s)**4*mp.gamma(c-s)
    for b in etas: den*=mp.gamma(s+b)*mp.gamma(1-s-b)
    return mp.gamma(s)**3*mp.gamma(half-s)**7*mp.gamma(1+c-s)/den

def euler_m7(N):
    total=mp.mpf(0); ac=mp.mpf(1); H=mp.mpf(0);H2=mp.mpf(0);H3=mp.mpf(0)
    hn=mp.mpf(0);hn2=mp.mpf(0)
    d2=1<<N; cumulative=0
    for n in range(N):
        cumulative+=math.comb(N,n); w=mp.mpf(d2-cumulative)/d2
        h=l+hn-H;delta=pi*pi/3-4*H2+2*hn2;y=n+c
        u=1-14*y*h;v=196*y*h*h-28*h+7*y*(delta-pi*pi)
        T=80*pi*pi*y-26*pi*u+11*v;K=28*pi*pi*y-10*pi*u+3*v
        F=(98*H+74*l-6*pi)*T-98*pi*K-98*(11*u-13*pi*y)*(pi*pi/3+4*H2)-8624*y*(mp.zeta(3)-H3)
        total+=(-1)**n*w*ac**7*F
        k=n+1;ac*=mp.mpf(2*n+1)/(2*n+2);hn+=mp.mpf(1)/k;hn2+=mp.mpf(1)/(k*k)
        for j in [2*n+1,2*n+2]:
            H+=mp.mpf(1)/j;H2+=mp.mpf(1)/(j*j);H3+=mp.mpf(1)/(j*j*j)
    return total

if __name__=='__main__':
    start=time.time();Hv=barnes(hg); print('H',mp.nstr(Hv,DPS),'sec',time.time()-start,flush=True)
    start=time.time();Gv=barnes(gg); print('G',mp.nstr(Gv,DPS),'sec',time.time()-start,flush=True)
    N=max(240,4*DPS+100)
    old=24*pi**3*euler_m7(N)
    new=24*pi**mp.mpf('1.5')*(392*mp.sqrt(185)*Hv+rho*Gv)
    print('old',mp.nstr(old,DPS));print('new',mp.nstr(new,DPS));print('err',new-old,flush=True)
    points=[c+mp.mpf('.17')*1j,c+mp.mpf('.81')*1j,c+2*1j]
    errs=[]
    for s in points:
        z=mp.tan(pi*s)
        errs.append(abs(gg(s)-pi/rho*rp(s)*(a*z*z+bA*z+cA)))
        errs.append(abs(hg(s)-pi/(2*mp.sqrt(185))*rp(s)*(7*z*z+13*z+11)*(mp.digamma(1-2*s)+mp.euler)))
    print('point kernels max',max(errs),flush=True)
    record={'working_decimal_digits':DPS,'H7':str(Hv),'G7':str(Gv),'rho7':str(rho),'eta':[str(a) for a in etas],'beta7':str(beta),'B7_original_central':str(old),'B7_new':str(new),'absolute_difference':str(abs(old-new)),'kernel_point_max_difference':str(max(errs)),'Euler_N':N,'rigorous_interval':False,'H_evaluation':'gamma outer kernel; inner Barnes transform evaluated analytically as digamma difference','G_evaluation':'its own gamma-product Barnes kernel'}
    (Path(__file__).resolve().parent/'results'/f'numerical_{DPS}.json').write_text(json.dumps(record,indent=2))
