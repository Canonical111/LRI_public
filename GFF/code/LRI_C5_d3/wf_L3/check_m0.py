"""Semi-independent check: mu_1-weighted Horn sum m0 = sum_{l,n} (2l+1) T_ln^4 mu_1 at q=3/4 by real-axis finite
differences of h4(0;b) = sum (2l+1) T_ln(b)^4 (T_ln(b) = (b/2)_{l+n} (b/2-1/2)_n / ((3/2)_{l+n} n!)), compared with the
Cauchy-circle value via (N X0)' = -2 pi X0 + 16 pi^2 m0."""
import mpmath as mp, json
import gen3 as G
mp.mp.dps = 60
def h4(b):
    s = b / 2
    A, B, C, D = s, mp.mpf(3) / 2, s - mp.mpf(1) / 2, mp.mpf(1)
    # sum_{k>=j>=0} (2(k-j)+1) [G(k+A)/G(k+B)]^4 [G(j+C)/G(j+D)]^4, normalized by the (0,0) term
    o10 = G.ordered(A, B, 0, 1, C, D, 0, 0, 4, 120, 50)
    o01 = G.ordered(A, B, 0, 0, C, D, 0, 1, 4, 120, 50)
    norm = (mp.gamma(A) / mp.gamma(B) * mp.gamma(C) / mp.gamma(D)) ** 4
    return mp.re(2 * o10 - 2 * o01 + (o10 * 0) + G.ordered(A, B, 0, 0, C, D, 0, 0, 4, 120, 50)) / norm
h = mp.mpf('1e-7'); b0 = mp.mpf(3) / 2
f = {k: h4(b0 + k * h) for k in (-2, -1, 1, 2)}
der = (f[-2] - 8 * f[-1] + 8 * f[1] - f[2]) / (12 * h)
m0 = der / 4
v = json.load(open('L3_final_values.json'))['values']
X0 = mp.mpf(v['X0']); NX0dot = mp.mpf(v['NX0dot'])
h40 = h4(b0)
print('h4(0)   ', mp.nstr(h40, 40), '  X0/(4 pi^2) =', mp.nstr(X0 / (4 * mp.pi ** 2), 40))
m0_cauchy = (NX0dot + 2 * mp.pi * X0) / (16 * mp.pi ** 2)
print('m0 (finite diff, real axis)', mp.nstr(m0, 30))
print('m0 (Cauchy circle)         ', mp.nstr(m0_cauchy, 30), '  diff', mp.nstr(m0 - m0_cauchy, 3))
