# Test 1: Laplace formulas (eq:laplace) for complex g, both half-planes; principal powers.
import mpmath as mp
mp.mp.dps = 25
def f(g,w): return mp.gamma(w)/mp.gamma(w+g)
def lap_up(g,w):   # Im w > 0
    F = lambda v: mp.expj(w*v)*mp.power(1-mp.expj(v), g-1)
    # integrate over [0, inf) with breakpoints at 2 pi k
    pts=[2*mp.pi*k for k in range(0,40)]
    s = mp.quad(F, pts) + mp.quad(F,[pts[-1], mp.inf])
    return -1j/mp.gamma(g)*s
def lap_dn(g,w):   # Im w < 0
    F = lambda v: mp.expj(-w*v)*mp.power(1-mp.expj(-v), g-1)
    pts=[2*mp.pi*k for k in range(0,40)]
    s = mp.quad(F, pts) + mp.quad(F,[pts[-1], mp.inf])
    return 1j/mp.gamma(g)*s
for g in [mp.mpc(0.7,0.4), mp.mpc(1.6,-0.8), mp.mpc(0.35,1.1)]:
    for w in [mp.mpc(-2.3,1.2), mp.mpc(0.4,2.0), mp.mpc(-5.1,1.5)]:
        a=lap_up(g,w); b=f(g,w)
        c=lap_dn(g,mp.conj(w)); e=f(g,mp.conj(w))
        print('g=%s w=%s  up rel %.1e   down rel %.1e' % (mp.nstr(g,3), mp.nstr(w,3), abs(a-b)/abs(b), abs(c-e)/abs(e)))
