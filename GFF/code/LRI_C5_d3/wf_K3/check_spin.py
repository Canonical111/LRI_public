import mpmath as mp, time
from kres import consts, spin
mp.mp.dps=20
q=mp.mpf(3)/4
c=consts(q)
cs=c['cstar']
def spec(l):
    a=(l+q)/2;b=a+q
    def f(nu):
        s=1j*nu
        t=mp.gamma(2*q)*mp.gamma(a+s)*mp.gamma(a-s)/(mp.gamma(b+s)*mp.gamma(b-s))
        p=mp.re(mp.psi(0,a+s)+mp.psi(0,b+s));h=mp.im(mp.psi(0,a+s)-mp.psi(0,b+s))
        j=mp.re(mp.psi(1,a+s)-mp.psi(1,b+s));k=mp.im(mp.psi(1,a+s)+mp.psi(1,b+s))
        r=mp.re(mp.psi(2,a+s)+mp.psi(2,b+s));E2=-h**2/2-5*j/8
        return mp.re(t**2)*((cs-p)*E2-h*k/2-5*r/32)
    return mp.quad(f,[0,1,5,mp.inf])/(4*mp.pi)
for l in (0,1,4):
    t0=time.time();a=spin(c,l);b=spec(l)
    print(l,mp.nstr(a,18),mp.nstr(b,18),mp.nstr(a-b,3),'%.1fs'%(time.time()-t0))
