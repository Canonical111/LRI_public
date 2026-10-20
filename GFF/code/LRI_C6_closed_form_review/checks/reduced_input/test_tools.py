import mpmath as mp, time
from tools import *
mp.mp.dps = 70
t=time.time()
# zeta(2)
f = lambda x: 1/(x+1)**2
N=60
S = mp.fsum(f(n) for n in range(N))
tail,I = em_tail(f, N, K=20)
print('zeta2 err', mp.nstr(S+tail-mp.zeta(2),5), time.time()-t)
# zeta''(2) : sum log^2 n / n^2 from n=1 : f(x)=log(x+1)^2/(x+1)^2
f = lambda x: mp.log(x+1)**2/(x+1)**2
S = mp.fsum(f(n) for n in range(N))
tail,I = em_tail(f, N, K=20)
print('zeta2pp err', mp.nstr(S+tail-mp.zeta(2,derivative=2),5), time.time()-t)
# gamma ratio accuracy at large x
for x in [mp.mpf(10)**20, mp.mpf(10)**60, mp.mpf(10)**100]:
    r1 = mp.gamma(x+0.5)/mp.gamma(x+1)
    with mp.workdps(300):
        r2 = mp.gamma(x+0.5)/mp.gamma(x+1)
    print('ratio rel err', mp.nstr((r1-r2)/r2,5))
# U4 by EM and richardson
a4 = lambda x: (mp.gamma(x+0.5)/(mp.sqrt(mp.pi)*mp.gamma(x+1)))**4
S = mp.fsum(a4(n) for n in range(N)); tail,I = em_tail(a4,N,K=20)
U4em = S+tail
print('U4 EM', mp.nstr(U4em,60), time.time()-t)
# richardson
a=mp.mpf(1); part=[]; s=mp.mpf(0); Ns=[]; vals=[]
n0=40; J=30
for n in range(n0*J+1):
    if n>0: a*= mp.mpf(2*n-1)/(2*n)
    s+=a**4
    if (n+1)%n0==0: Ns.append(n+1); vals.append(s)
for J2 in [20,25,30]:
    print('U4 rich J',J2, mp.nstr(richardson(vals[:J2],Ns[:J2])-U4em,5))
print(time.time()-t)
