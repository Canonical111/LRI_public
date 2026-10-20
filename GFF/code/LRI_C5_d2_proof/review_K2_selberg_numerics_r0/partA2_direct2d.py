"""
Lemma 2, direct check WITHOUT Lemma 1: each cell integral A(R) = int_R U(xi) d^2xi by nested tanh-sinh
quadrature of the raw integrand (inner x-integral numeric), compared with 2 I_j(tau) from partA_data.json.
mpmath dps 40; expected accuracy ~ 1e-18 or better.
"""
import mpmath as mp, json, sys, time
mp.mp.dps = 35
D = json.load(open('partA_data.json'))
inf = mp.inf

def Uoff(E, sgn, d, y, t, oney):
    """U at x = E + sgn*d, distances to 0, 1, y computed as (E-p) + sgn*d (exact when E == p)."""
    dx0 = abs((E - 0) + sgn*d); dx1 = abs((E - 1) + sgn*d); dxy = abs((E - y) + sgn*d)
    return dx0**-0.5 * dx1**-0.5 * abs(y)**-0.5 * abs(oney)**(t-1) * dxy**-0.5

def inner(y, t, lo, hi, oney):
    if lo == -inf:      # x = hi - d, d = (1-z)/z
        return mp.quad(lambda z: Uoff(hi, -1, (1-z)/z, y, t, oney)/z**2, [0, 1])
    if hi == inf:       # x = lo + d
        return mp.quad(lambda z: Uoff(lo, +1, (1-z)/z, y, t, oney)/z**2, [0, 1])
    h = (hi - lo)/2
    return mp.quad(lambda d: Uoff(lo, +1, d, y, t, oney), [0, h]) + mp.quad(lambda d: Uoff(hi, -1, d, y, t, oney), [0, h])

# cell -> (y-range, x-interval as function of y, j)
cells = {
 'R1': ('neg', lambda y: (-inf, y), 6), 'R2': ('neg', lambda y: (y, 0), 5),
 'R5': ('neg', lambda y: (0, 1), 6),    'R9': ('neg', lambda y: (1, inf), 5),
 'R3': ('mid', lambda y: (-inf, 0), 2), 'R6': ('mid', lambda y: (0, y), 1),
 'R7': ('mid', lambda y: (y, 1), 2),    'R10': ('mid', lambda y: (1, inf), 1),
 'R4': ('pos', lambda y: (-inf, 0), 4), 'R8': ('pos', lambda y: (0, 1), 3),
 'R11': ('pos', lambda y: (1, y), 4),   'R12': ('pos', lambda y: (y, inf), 3)}

def near1(sign, d, t, xint):
    """inner integral at y = 1 + sign*d, with working precision raised so that y keeps d to full relative accuracy"""
    extra = max(0, int(-mp.log10(d))) + 5 if d > 0 else 0
    with mp.workdps(mp.mp.dps + extra):
        dd = mp.mpf(d); y = 1 + sign*dd
        val = inner(y, t, *xint(y), -sign*dd)
    return +val

def A(cell, t):
    rng, xint, j = cells[cell]
    g = lambda y: inner(y, t, *xint(y), 1-y)
    if rng == 'mid':     # y in (0,1): y=u^2 near 0 ; 1-y = d = v^(1/t) near 1
        return mp.quad(lambda u: 2*u*g(u*u), [0, 1/mp.sqrt(2)]) + \
               mp.quad(lambda v: (1/t)*v**(1/t-1)*near1(-1, v**(1/t), t, xint) * (v**(1/t))**(t-1) / (v**(1/t))**(t-1), [0, mp.mpf(1)/2**t])
    if rng == 'neg':     # y in (-1,0): y=-u^2 ; y<-1: y=-1/s
        return mp.quad(lambda u: 2*u*g(-u*u), [0, 1]) + mp.quad(lambda s: g(-1/s)/s**2, [0, 1])
    if rng == 'pos':     # y in (1,2): y=1+v^(1/t) ; y>2: y=2/s
        return mp.quad(lambda v: (1/t)*v**(1/t-1)*near1(+1, v**(1/t), t, xint), [0, 1]) + mp.quad(lambda s: g(2/s)*2/s**2, [0, 1])

lines = []
tau = sys.argv[1] if len(sys.argv) > 1 else '0.3'
t = mp.mpf(tau)
for cell in cells:
    T0 = time.time()
    val = A(cell, t)
    ref = 2*mp.mpf(D[tau]['I'][str(cells[cell][2])])
    s = f'L2-direct tau={tau} A({cell}) vs 2 I{cells[cell][2]}: A = {mp.nstr(val, 25)}  rel.res = {mp.nstr(abs(val/ref-1), 3)}  ({time.time()-T0:.0f}s)'
    print(s); sys.stdout.flush(); lines.append(s)
open(f'partA2_direct2d_{tau}.out', 'w').write('\n'.join(lines) + '\n')
