"""Numerical check (not a proof step) of the residue calculus at d=2, q=1/2.
For fixed spin l: (1/pi) int_0^inf Re[g(i nu)^2 R_tau(i nu)] dnu  ==  - sum_n [Res1(l+n,n) + Res2(l+n,n)].
Also checks H1 = sum_m h'(m) = -(2 pi/Gamma(tau)) E(tau,1/2), E via its 3F2 Euler form."""
import mpmath as mp
mp.mp.dps = 30

def lg(z): return mp.loggamma(z)

def barnes(l, tau):
    a = mp.mpf(l)/2 + mp.mpf(1)/4; b = a + mp.mpf(1)/2
    def f(nu):
        s = 1j*nu
        logg = lg(a+s) + lg(a-s) - lg(b+s) - lg(b-s)
        logR = lg(a+s) + lg(b-tau-s) - lg(a+tau+s) - lg(b-s)
        return mp.re(mp.exp(2*logg + logR))
    return mp.quad(f, [0, 0.5, 2, 8, 32, 128, mp.inf]) / mp.pi

def make(tau):
    S, C = mp.sin(mp.pi*tau), mp.cos(mp.pi*tau)
    h  = lambda z: mp.exp(3*lg(z+0.5) - 2*lg(z+1) - lg(z+0.5+tau))
    hp = lambda z: h(z)*(3*mp.digamma(z+0.5) - 2*mp.digamma(z+1) - mp.digamma(z+0.5+tau))
    k  = lambda z: mp.exp(3*lg(z+1-tau) - 2*lg(z+1.5-tau) - lg(z+1))
    r1 = lambda m, n: (S/(mp.pi*C**2))*h(m)*h(n) + (hp(m)*h(n) + h(m)*hp(n))/(mp.pi**2*C)
    r2 = lambda m, n: -(S**3/(mp.pi*C**2))*k(m)*k(n)
    return h, hp, k, r1, r2

for tau in [mp.mpf(3)/10, mp.mpf(3)/5]:
    h, hp, k, r1, r2 = make(tau)
    print("tau =", tau)
    for l in [0, 1, 4]:
        B = barnes(l, tau)
        Rs = -mp.nsum(lambda n: r1(l+n, n) + r2(l+n, n), [0, mp.inf], method='e')
        print("  l=%d  Barnes=%s  -SumRes=%s  diff=%s" % (l, mp.nstr(B, 20), mp.nstr(Rs, 20), mp.nstr(B-Rs, 3)))
    H1 = mp.nsum(hp, [0, mp.inf], method='e')
    E = (mp.pi/2)*mp.beta(tau, 0.5)*mp.hyp3f2(0.5, 0.5, tau, 1, tau+0.5, 1)
    print("  H1 = %s   -(2pi/Gamma)E(tau,1/2) = %s   diff=%s" % (mp.nstr(H1, 20), mp.nstr(-2*mp.pi*E/mp.gamma(tau), 20),
          mp.nstr(H1 + 2*mp.pi*E/mp.gamma(tau), 3)))
    F = lambda t: mp.hyp3f2(0.5, 0.5, t, 1, 1, 1)
    print("  H1 + pi^3 F(1-tau)/Gamma(tau) = %s" % mp.nstr(H1 + mp.pi**3*F(1-tau)/mp.gamma(tau), 3))
