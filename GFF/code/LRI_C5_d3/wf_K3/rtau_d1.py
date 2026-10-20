import mpmath as mp, sys
mp.mp.dps=40
q=mp.mpf(1)/4
def R(tau,spins=(0,1),mult=lambda l:1):
    tot=0
    for l in spins:
        a=(l+q)/2;b=a+q
        def f(nu):
            s=1j*nu
            g=mp.gamma(a+s)*mp.gamma(a-s)/(mp.gamma(b+s)*mp.gamma(b-s))
            Rt=mp.gamma(a+s)*mp.gamma(b-tau-s)/(mp.gamma(a+tau+s)*mp.gamma(b-s))
            return mp.re(mp.gamma(2*q)**2*g**2*Rt)
        tot+=mult(l)*mp.quad(f,[0,1,4,16,mp.inf])/mp.pi
    return tot
for tau in (mp.mpf(1),mp.mpf(1)/2,mp.mpf(3)/2):
    v=R(tau)
    print('d=1 tau',tau,'R =',mp.nstr(v,35))
    # test log-linear in log Gamma(k/8), log pi, log 2, log(1+sqrt2), log 3
    bas=[mp.log(abs(v)),mp.log(mp.pi),mp.log(2),mp.log(3),mp.log(1+mp.sqrt(2))]+[mp.loggamma(mp.mpf(k)/8) for k in (1,2,3)]
    print('   loglin:',mp.pslq(bas,maxcoeff=200,maxsteps=10**6))
    print('   identify:',mp.identify(v,['pi','log(2)','catalan','zeta(3)','pi**2'],tol=mp.mpf(10)**-30))
