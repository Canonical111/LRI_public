"""Independent check (verifier V_L3_b4) of: b4(b) = sin^3(2 pi al) al Gamma(2al)^4 Gamma(1-4al)/(Gamma(1+2al)Gamma(1-2al)^3),
al = b/4 - 1/4, and (N^{1/2} b4)' = (pi/2 - log2) b4 at b = 3/2, N = [Gamma(3/2-b/2)/Gamma(b/2)]^4.
Method (different from the author's Stirling-Bernoulli + Hurwitz-zeta tails):
  direct partial sum to n<Ncut, tail = Euler-Maclaurin with integral by tanh-sinh quadrature (x = Ncut/s)
  and odd derivatives by mpmath numerical differentiation of the loggamma-built summand.
Finite-mode check: Psi_1(u) = sin^4(pi(u+al)) U_1(u) - sin^4(pi(al-u)) U_1(1-u) must equal b sin(2 pi u) for any u."""
import mpmath as mp, sys

mp.mp.dps = int(sys.argv[1]) if len(sys.argv) > 1 else 50
NC = 60
KEM = 14


def U(m, v, al):
    def f(x):
        ex = int(mp.log10(abs(x) + 10)) + 10
        with mp.extradps(ex):
            r = (x + v) ** m * mp.exp(4 * (mp.loggamma(x + v + al) - mp.loggamma(x + v + 1 - al)))
        return +r
    s = mp.fsum(f(n) for n in range(NC))
    a = mp.mpf(NC)
    dec = 2 - 8 * al - m + 1                       # f(a e^y) a e^y ~ e^{-dec y}
    Y = (mp.mp.dps + 8) * mp.log(10) / dec
    pts = [0, 2, 8] + [8 * 2 ** k for k in range(1, 12) if 8 * 2 ** k < Y] + [Y]
    integ = mp.quad(lambda y: f(a * mp.exp(y)) * a * mp.exp(y), pts)
    # neglected piece beyond Y: leading power law  ~ C e^{-dec Y}/dec
    em = integ + f(a * mp.exp(Y)) * a * mp.exp(Y) / dec + f(a) / 2
    tay = mp.taylor(f, a, 2 * KEM)
    for k in range(1, KEM + 1):
        em -= mp.bernoulli(2 * k) / mp.factorial(2 * k) * tay[2 * k - 1] * mp.factorial(2 * k - 1)
    return s + em


def closed(b):
    al = mp.mpf(b) / 4 - mp.mpf(1) / 4
    return mp.sin(2 * mp.pi * al) ** 3 * al * mp.gamma(2 * al) ** 4 * mp.gamma(1 - 4 * al) / (
        mp.gamma(1 + 2 * al) * mp.gamma(1 - 2 * al) ** 3)


def Psi1(u, al):
    u = mp.mpf(u)
    return mp.sin(mp.pi * (u + al)) ** 4 * U(1, u, al) - mp.sin(mp.pi * (al - u)) ** 4 * U(1, 1 - u, al)


print('dps', mp.mp.dps)
for b in ['1.3', '1.5', '1.6', '1.7', '1.8']:
    b = mp.mpf(b)
    al = b / 4 - mp.mpf(1) / 4
    bnum = mp.sin(2 * mp.pi * al) ** 3 * U(1, al, al)        # Psi_1(al)/sin(2 pi al)
    cf = closed(b)
    # finite-mode: sine amplitude read at two generic u
    r1 = Psi1('0.3', al) / mp.sin(2 * mp.pi * mp.mpf('0.3')) - cf
    r2 = Psi1('0.62', al) / mp.sin(2 * mp.pi * mp.mpf('0.62')) - cf
    print('b=%s  b4num=%s  rel(num-closed)=%s  finite-mode u=.3: %s  u=.62: %s' % (
        b, mp.nstr(bnum, 25), mp.nstr((bnum - cf) / cf, 3), mp.nstr(r1 / cf, 3), mp.nstr(r2 / cf, 3)))

# b = 3/2 value vs td:gammaAmplitudes
b0 = mp.mpf(3) / 2
print('closed(3/2) - Gamma(1/4)^6/(16 pi^(5/2)) =', mp.nstr(closed(b0) - mp.gamma(0.25) ** 6 / (16 * mp.pi ** 2.5), 3))
# derivative identity, closed form, numerical differentiation
F = lambda b: (mp.gamma(mp.mpf(3) / 2 - b / 2) / mp.gamma(b / 2)) ** 2 * closed(b)
dF = mp.diff(F, b0)
print('dF/db / b4 - (pi/2 - log2) =', mp.nstr(dF / closed(b0) - (mp.pi / 2 - mp.log(2)), 3))
# derivative identity from the numerical series (central differences, Richardson in step)
Fn = lambda b: (mp.gamma(mp.mpf(3) / 2 - b / 2) / mp.gamma(b / 2)) ** 2 * mp.sin(2 * mp.pi * (b / 4 - mp.mpf(1) / 4)) ** 3 * U(1, b / 4 - mp.mpf(1) / 4, b / 4 - mp.mpf(1) / 4)
hs = [mp.mpf(10) ** -7, mp.mpf(10) ** -7 / 2]
ds = [(Fn(b0 + h) - Fn(b0 - h)) / (2 * h) for h in hs]
dr = (4 * ds[1] - ds[0]) / 3
print('series-based dF/db / b4 - (pi/2-log2) =', mp.nstr(dr / closed(b0) - (mp.pi / 2 - mp.log(2)), 3), '(O(h^4)~1e-28 expected)')
