import mpmath as mp
from flint import arb, arb_series, ctx
ctx.prec=300; mp.mp.dps=80
K1=61
X=mp.mpf(300)+mp.mpf(1)/2; Xa=arb(300)+arb(1)/2
def evals(ser,x):
    co=ser.coeffs(); return mp.fsum(mp.mpf(c.mid().str(85,radius=False))*x**(-k) for k,c in enumerate(co))
S=lambda c: arb_series(c,prec=K1)
for c in (mp.mpf(1)/2, mp.mpf(8)+mp.mpf(1)/4, mp.mpf(-1)/4):
    ca=arb(str(c)) if c!=mp.mpf(8.25) else arb(33)/4
    ca=arb(mp.nstr(c,30))
    p0=S([arb(0)]+[-(-1)**k*ca.bernoulli_poly(k)/k for k in range(1,K1)])
    print('psi0',mp.nstr(mp.psi(0,X+c)-mp.log(X)-evals(p0,X),3))
    for j in (1,2,3):
        co=[arb(0)]*K1
        for k in range(0,K1-j):
            co[k+j]=(-1)**(j-1)*(-1)**k*ca.bernoulli_poly(k)*arb.fac_ui(k+j-1)/arb.fac_ui(k)
        print('psi',j,mp.nstr(mp.psi(j,X+c)-evals(S(co),X),3))
    be=c+mp.mpf(3)/4; cb=arb(mp.nstr(be,30))
    lr=S([arb(0)]+[(-1)**(k+1)*(ca.bernoulli_poly(k+1)-cb.bernoulli_poly(k+1))/(k*(k+1)) for k in range(1,K1)])
    print('lr',mp.nstr(mp.loggamma(X+c)-mp.loggamma(X+be)-(c-be)*mp.log(X)-evals(lr,X),3))
