"""d=1, independent of the reviewed code: spectral W3(1;b) (two spins, direct quadrature) versus the
two-node/zero-mode prediction W3 = 6 pi^2 R(1;b)/sin^2(pi b/2), R(1;b) = sum_m [(b)_m/m!]^3 = Dixon."""
import mpmath as mp
import sys
mp.mp.dps = int(sys.argv[1]) if len(sys.argv) > 1 else 25

def W3_spectral(b, d=1):
    b = mp.mpmathify(b); g = (d - b)/2
    N = mp.gamma(mp.mpf(d)/2)*mp.gamma(g)/mp.gamma(b/2)
    tot = 0
    for l, dl in [(0, 1), (1, 1)]:
        a = mp.mpf(l)/2 + b/4; be = a + g
        f = lambda nu: (mp.gamma(a+1j*nu)*mp.gamma(a-1j*nu)/(mp.gamma(be+1j*nu)*mp.gamma(be-1j*nu)))**3
        pts = [0] + [mp.mpf(4)**k for k in range(-1, 12)] + [mp.inf]
        tot += dl*mp.quad(f, pts)/mp.pi
    return N**3*tot

def R_dixon_closed(b):
    return mp.gamma(1+b/2)*mp.gamma(1-3*b/2)/(mp.gamma(1+b)*mp.gamma(1-b/2)**2*mp.gamma(1-b))

def R_series(b):
    return mp.nsum(lambda m: (mp.rf(b, m)/mp.factorial(m))**3, [0, mp.inf])

def R_from_T(b, d=1):
    # sum_{l=0,1} sum_n T_ln^3 with T_ln = (sigma)_{l+n}(1-g)_n/((2q)_{l+n} n!)
    sig = b/2; g = (d-b)/2; q2 = mp.mpf(d)/2
    T = lambda l, n: mp.rf(sig, l+n)*mp.rf(1-g, n)/(mp.rf(q2, l+n)*mp.factorial(n))
    return mp.nsum(lambda n: T(0, n)**3 + T(1, n)**3, [0, mp.inf])

for b in ['0.5', '0.37', '0.2', '0.6', '0.3+0.1j']:
    bb = mp.mpmathify(b)
    Rc = R_dixon_closed(bb)
    print('b =', b)
    print('   Dixon closed vs sum_m[(b)_m/m!]^3 :', mp.nstr(abs(Rc/R_series(bb) - 1), 3),
          '   vs sum_{l=0,1} T^3 (duplication):', mp.nstr(abs(Rc/R_from_T(bb) - 1), 3))
    pred = 6*mp.pi**2*Rc/mp.sin(mp.pi*bb/2)**2
    spec = W3_spectral(bb)
    print('   W3 spectral =', mp.nstr(spec, 20), '  6pi^2 R/s^2 =', mp.nstr(pred, 20), '  rel dev', mp.nstr(abs(spec/pred-1), 3))

# derivatives at b = 1/2 (Cor. integer (a)): (log R)' = pi, (log R)'' = pi^2 + 24 G; Z1 = Q1 (2pi^2/3 + 8G)
lr = lambda b: mp.log(R_dixon_closed(b))
G = mp.catalan
print("(log R)'(1/2) - pi       =", mp.nstr(mp.diff(lr, mp.mpf(1)/2) - mp.pi, 3))
print("(log R)''(1/2) - pi^2-24G =", mp.nstr(mp.diff(lr, mp.mpf(1)/2, 2) - mp.pi**2 - 24*G, 3))
Q1 = mp.gamma(0.25)**4/mp.pi
Z1 = 4*mp.pi**2/3*mp.diff(R_dixon_closed, mp.mpf(1)/2, 2)
print('Z1 from (4pi^2/3) R\'\' =', mp.nstr(Z1, 22), ' vs Q1(2pi^2/3+8G):', mp.nstr(Z1/(Q1*(2*mp.pi**2/3+8*G)) - 1, 3))
print('R(1/2) - Q1/(4pi^2)  =', mp.nstr(R_dixon_closed(mp.mpf(1)/2) - Q1/(4*mp.pi**2), 3))
# W3'(1/2) = 0 from Dixon (exact) and Z1 directly as W3''/9 of the spectral-confirmed function
W3d = lambda b: 6*mp.pi**2*R_dixon_closed(b)/mp.sin(mp.pi*b/2)**2
print("W3'(1;1/2) from Dixon =", mp.nstr(mp.diff(W3d, mp.mpf(1)/2), 3))
