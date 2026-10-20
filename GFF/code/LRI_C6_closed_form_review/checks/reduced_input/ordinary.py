"""Ordinary hypergeometric inputs U4,U6,U8,H-,H0,H+,Y1,Y7 and the coefficient
series eq:Pbseries, eq:B8series.  Two methods each:
 (EM) partial sum n<N + Euler-Maclaurin tail with analytic continuation in n;
 (R)  exact-recurrence partial sums S_{k n0}, Richardson in 1/N.
"""
import mpmath as mp, json, time, sys
from tools import em_tail, richardson

mp.mp.dps = 80
pi = mp.pi; ell = mp.log(2); z3 = mp.zeta(3)
t0 = time.time()

# analytic continuations in n
def a(x):
    return mp.gamma(x + mp.mpf(1)/2) / (mp.sqrt(pi) * mp.gamma(x + 1))
def hh(x):
    return ell + mp.digamma(x + 1) - mp.digamma(2*x + 1)
def dd(x):
    return 4*mp.psi(1, 2*x + 1) - 2*mp.psi(1, x + 1)
def gr(x, p, q):
    return mp.gamma(x + p) / mp.gamma(x + q)

quarter = mp.mpf(1)/4
def tY(r):
    return mp.mpf(r)/8

cont = {
 'U4': lambda x: a(x)**4,
 'U6': lambda x: (4*x+1)*a(x)**6,
 'U8': lambda x: (4*x+1)*a(x)**8,
 'Hm': lambda x: (gr(x, quarter, 3*quarter)*mp.gamma(3*quarter)/mp.gamma(quarter))**6,
 'H0': lambda x: a(x)**6,
 'Hp': lambda x: (gr(x, 3*quarter, 5*quarter)*mp.gamma(5*quarter)/mp.gamma(3*quarter))**6,
 'Y1': lambda x: (x + tY(1)) * gr(x, tY(1)+quarter, tY(1)+3*quarter)**8,
 'Y7': lambda x: (x + tY(7)) * gr(x, tY(7)+quarter, tY(7)+3*quarter)**8,
 'PbS': lambda x: a(x)**6 * (312*hh(x)**2 + 13*dd(x) + 88*pi*hh(x)),
 'B8S': lambda x: a(x)**8 * ((2466 - 834*mp.sqrt(2))*pi**2*(x+quarter)
                            - 1112*pi*(1 - 16*(x+quarter)*hh(x))
                            + 139*mp.sqrt(2)*(256*(x+quarter)*hh(x)**2 - 32*hh(x)
                                              + 8*(x+quarter)*dd(x))),
}

# recurrence-based terms (definition-based harmonic numbers)
def rec_partials(name, nmax, n0):
    out = []; Ns = []
    s = mp.mpf(0)
    an = mp.mpf(1)
    H = mp.mpf(0); H2n = mp.mpf(0); H2_n = mp.mpf(0); H2_2n = mp.mpf(0)
    rm = mp.mpf(1); rp = mp.mpf(1)
    g1 = mp.gamma(tY(1)+quarter)/mp.gamma(tY(1)+3*quarter)
    g7 = mp.gamma(tY(7)+quarter)/mp.gamma(tY(7)+3*quarter)
    for n in range(nmax):
        if n > 0:
            an *= mp.mpf(2*n-1)/(2*n)
            H += mp.mpf(1)/n
            H2n += mp.mpf(1)/(2*n-1) + mp.mpf(1)/(2*n)
            H2_n += mp.mpf(1)/n**2
            H2_2n += mp.mpf(1)/(2*n-1)**2 + mp.mpf(1)/(2*n)**2
            rm *= (n-1+quarter)/(n-1+3*quarter)
            rp *= (n-1+3*quarter)/(n-1+5*quarter)
            g1 *= (n-1+tY(1)+quarter)/(n-1+tY(1)+3*quarter)
            g7 *= (n-1+tY(7)+quarter)/(n-1+tY(7)+3*quarter)
        hn = ell + H - H2n
        dn = pi**2/3 - 4*H2_2n + 2*H2_n
        yn = n + quarter
        if name == 'U4': term = an**4
        elif name == 'U6': term = (4*n+1)*an**6
        elif name == 'U8': term = (4*n+1)*an**8
        elif name == 'Hm': term = rm**6
        elif name == 'H0': term = an**6
        elif name == 'Hp': term = rp**6
        elif name == 'Y1': term = (n+tY(1))*g1**8
        elif name == 'Y7': term = (n+tY(7))*g7**8
        elif name == 'PbS': term = an**6*(312*hn**2 + 13*dn + 88*pi*hn)
        elif name == 'B8S':
            term = an**8*((2466 - 834*mp.sqrt(2))*pi**2*yn - 1112*pi*(1 - 16*yn*hn)
                          + 139*mp.sqrt(2)*(256*yn*hn**2 - 32*hn + 8*yn*dn))
        s += term
        if (n+1) % n0 == 0:
            Ns.append(n+1); out.append(+s)
    return Ns, out

res = {}
N_EM = 100; K_EM = 25
for name, f in cont.items():
    # check recurrence term vs continuation at n=0..3 and 37
    S = mp.fsum(f(mp.mpf(n)) for n in range(N_EM))
    tail, _ = em_tail(f, N_EM, K=K_EM)
    vEM = S + tail
    S2 = mp.fsum(f(mp.mpf(n)) for n in range(2*N_EM))
    tail2, _ = em_tail(f, 2*N_EM, K=K_EM)
    vEM2 = S2 + tail2
    n0 = 50; J = 36
    Ns, Ps = rec_partials(name, n0*J, n0)
    vR = richardson(Ps, Ns)
    vR2 = richardson(Ps[4:], Ns[4:])
    res[name] = dict(EM=mp.nstr(vEM, 70), EM_N200_minus_EM=mp.nstr(vEM2-vEM, 5),
                     R_minus_EM=mp.nstr(vR-vEM, 5), R2_minus_R=mp.nstr(vR2-vR, 5),
                     rec_partial_N100_minus_cont=mp.nstr(Ps[1]-S, 5))
    print(name, mp.nstr(vEM, 60), '| EM200-EM100', mp.nstr(vEM2-vEM, 3),
          '| R-EM', mp.nstr(vR-vEM, 3), '| R2-R', mp.nstr(vR2-vR, 3),
          '| recS100-contS100', mp.nstr(Ps[1]-S, 3), ' t=%.1f' % (time.time()-t0))
    sys.stdout.flush()

json.dump(res, open('ordinary.json', 'w'), indent=1)
