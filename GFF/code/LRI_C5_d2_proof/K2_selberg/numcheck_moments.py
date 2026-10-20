"""
Numerical checks (not proof steps) of the ingredients of the d=2 K-master formula:
  (1) inner x-integrals over the four intervals = 2K(m)/sqrt(e3-e1), 2K(1-m)/sqrt(e3-e1)
  (2) the 12 region integrals A(R) = 2 I_j  (direct 2D quadrature at tau = 0.3)
  (3) d=1 moment relations and the Euler/Thomae forms of I_3, I_4
  (4) J(t=1) = 3 Q_2 = Gamma(1/4)^8/(8 pi^4)
"""
import mpmath as mp
mp.mp.dps = 20

K = mp.ellipk            # parameter convention K(m) = int_0^{pi/2} (1 - m sin^2)^{-1/2}

def E(a, b):
    return mp.quad(lambda x: x**(a-1)*(1-x)**(b-1)*K(x), [0, mp.mpf(1)/2, 1])

def Is(tau):
    return {1: E(mp.mpf(1)/2, tau), 2: E(tau, mp.mpf(1)/2), 3: E(1-tau, tau),
            4: E(tau, 1-tau), 5: E(mp.mpf(1)/2, 1-tau), 6: E(1-tau, mp.mpf(1)/2)}

# (1) inner integrals
def inner(lo, hi, y):
    f = lambda x: 1/mp.sqrt(abs(x*(x-1)*(x-y)))
    return mp.quad(f, [lo, hi])
print('(1) inner x-integrals of |x(x-1)(x-y)|^{-1/2}:')
for y in [mp.mpf('0.37'), mp.mpf('-1.7'), mp.mpf('2.6')]:
    e = sorted([mp.mpf(0), mp.mpf(1), y]); e1, e2, e3 = e
    m = (e3-e2)/(e3-e1); r = 1/mp.sqrt(e3-e1)
    pred = [2*K(m)*r, 2*K(1-m)*r, 2*K(m)*r, 2*K(1-m)*r]
    got = [inner(-mp.inf, e1, y), inner(e1, e2, y), inner(e2, e3, y), inner(e3, mp.inf, y)]
    print('  y =', y, ' max rel dev =', mp.nstr(max(abs(g/p-1) for g, p in zip(got, pred)), 3))

# (2) region integrals at tau = 0.3 (iterated quadrature; outer y, inner x)
tau = mp.mpf('0.3')
I = Is(tau)
def U(x, y):
    p = abs(x)*abs(1-x)*abs(y)*abs(y-x)
    if p == 0 or y == 1:
        return mp.mpf(0)          # measure-zero set (tanh-sinh node rounded onto a singular point)
    return p**-0.5*abs(1-y)**(-1+tau)
mp.mp.dps = 12
def reg(xlo, xhi, ylo, yhi):
    # xlo/xhi may be functions of y
    def outer(y):
        a = xlo(y) if callable(xlo) else xlo
        b = xhi(y) if callable(xhi) else xhi
        return mp.quad(lambda x: U(x, y), [a, b])
    return mp.quad(outer, [ylo, yhi])
ninf, pinf = -mp.inf, mp.inf
ident = lambda y: y
regions = [  # (name, xlo, xhi, ylo, yhi, j)
    ('R1 x<y<0', ninf, ident, ninf, 0, 6), ('R2 y<x<0', ident, 0, ninf, 0, 5),
    ('R3 x<0<y<1', ninf, 0, 0, 1, 2), ('R4 x<0,1<y', ninf, 0, 1, pinf, 4),
    ('R5 y<0<x<1', 0, 1, ninf, 0, 6), ('R6 0<x<y<1', 0, ident, 0, 1, 1),
    ('R7 0<y<x<1', ident, 1, 0, 1, 2), ('R8 0<x<1<y', 0, 1, 1, pinf, 3),
    ('R9 y<0,1<x', 1, pinf, ninf, 0, 5), ('R10 0<y<1<x', 1, pinf, 0, 1, 1),
    ('R11 1<x<y', 1, ident, 1, pinf, 4), ('R12 1<y<x', ident, pinf, 1, pinf, 3)]
print('(2) region integrals A(R) vs 2 I_j at tau = 0.3 (12-digit quadrature):')
for name, xlo, xhi, ylo, yhi, j in regions:
    A = reg(xlo, xhi, ylo, yhi)
    print('  %-14s A = %s   2 I_%d = %s   rel dev %s' % (name, mp.nstr(A, 10), j, mp.nstr(2*I[j], 10), mp.nstr(A/(2*I[j])-1, 2)))
mp.mp.dps = 20

# (3) moment relations, Euler/Thomae
print('(3) moment relations and 3F2 forms:')
for tau in [mp.mpf('0.1'), mp.mpf('0.3'), mp.mpf('0.77')]:
    I = Is(tau); s, c = mp.sinpi(tau), mp.cospi(tau)
    F = mp.hyp3f2(0.5, 0.5, tau, 1, 1, 1)
    G = mp.hyp3f2(tau, tau, tau, 0.5+tau, 0.5+tau, 1)
    devs = [I[1]-(c*I[3]+s*I[4]), I[5]-(s*I[3]-c*I[4]), I[2]-s*I[3], I[6]-s*I[4],
            I[3]-mp.pi/2*mp.gamma(tau)**2/mp.gamma(0.5+tau)**2*G, I[4]-mp.pi**2/(2*s)*F]
    print('  tau =', tau, ' residuals:', [mp.nstr(d, 2) for d in devs])

# (4) t = 1 (tau = 1/2): J = (4/pi^2) sin^2 (I3^2 + I4^2) vs 3 Q_2
tau = mp.mpf(1)/2
I = Is(tau)
J = 4/mp.pi**2*(I[3]**2+I[4]**2)
print('(4) J(t=1) =', J, '  3Q_2 =', mp.gamma(0.25)**8/(8*mp.pi**4), ' diff', mp.nstr(J-mp.gamma(0.25)**8/(8*mp.pi**4), 3))
