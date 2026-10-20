"""Independent spectral W3(3;b) = N^3 (1/pi) sum_l (2l+1) int_0^inf |G(a+i nu)/G(b_l+i nu)|^6 d nu,
spin sum by Richardson with tail exponents 3-6g-k (single integer-spaced family)."""
import sys, time
import mpmath as mp
mp.mp.dps = int(sys.argv[2]) if len(sys.argv) > 2 else 25; b = mp.mpmathify(sys.argv[1])
L0 = int(sys.argv[3]) if len(sys.argv) > 3 else 8; K = int(sys.argv[4]) if len(sys.argv) > 4 else 5
d = 3; sig = b/2; g = (mp.mpf(d) - b)/2; N = mp.gamma(mp.mpf(d)/2)*mp.gamma(g)/mp.gamma(sig)
def I(l):
    a = mp.mpf(l)/2 + b/4; be = a + g
    f = lambda nu: (mp.gamma(a+1j*nu)*mp.gamma(a-1j*nu)/(mp.gamma(be+1j*nu)*mp.gamma(be-1j*nu)))**3
    sc = max(1, l)
    return mp.quad(f, [0, sc/4, sc, 4*sc, 16*sc, mp.inf])/mp.pi
t0 = time.time(); parts = []; acc = 0; l = 0
for i in range(K+1):
    Li = L0*2**i
    while l < Li:
        acc += (2*l+1)*I(l); l += 1
    parts.append(acc)
e0 = 3 - 6*g
def rich(parts):
    n = len(parts); Ls = [mp.mpf(L0)*2**i for i in range(n)]
    A = mp.matrix(n, n); y = mp.matrix(n, 1)
    for i in range(n):
        A[i, 0] = 1
        for k in range(n-1): A[i, k+1] = Ls[i]**(e0-k)
        y[i] = parts[i]
    return mp.lu_solve(A, y)[0]
v1 = N**3*rich(parts); v2 = N**3*rich(parts[1:])
print('b=%s  W3 spectral = %s   (order diff %s, %.0fs)' % (b, mp.nstr(v1, 22), mp.nstr(abs(v1-v2), 3), time.time()-t0))
