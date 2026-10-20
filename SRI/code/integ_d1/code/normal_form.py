"""delta=0 flow of the compendium (hard-core scheme) -> exact-H gauge -> normal form under residual z-shifts."""
import sys, time, itertools
import sympy as sp
from series_tools import u, z, trunc, compose, inverse, series_div

D = 5  # working truncation (total degree in u,z)
# compendium delta=0 jets (eq:C8F, eq:C8H) + unknown higher terms as symbols
a, A, alpha, b, G, Phi, J, Omega, J9 = sp.symbols('a A alpha b G Phi J Omega J9')
c, f, L, L3, k, N, N2, K, Kv, h50 = sp.symbols('c f L L3 k N N2 K Kv h50')
f14, f23, f32, f41, f50 = sp.symbols('f14 f23 f32 f41 f50')  # unknown degree-5 F terms
F_hc = z + u*(1 + a*z + A*z**2 + alpha*z**3 + f14*z**4) + u**2*(b + G*z + Phi*z**2 + f23*z**3) \
       + u**3*(J + Omega*z + f32*z**2) + u**4*(J9 + f41*z) + f50*u**5
H_hc = 4*u + u**2*(c + f*z + L*z**2 + L3*z**3) + u**3*(k + N*z + N2*z**2) + u**4*(K + Kv*z) + h50*u**5

def to_exact_H_gauge(F, H, D):
    h = sp.expand(H / (4*u))
    hu, hz = sp.diff(h, u), sp.diff(h, z)
    FA_old = trunc(F * (1 + series_div(u*hu, h, D)) + 2*(1+z)*u*h*hz, D)
    u1 = trunc(u*h, D + 1)
    ui, zi = inverse(u1, z, D)
    return trunc(compose(FA_old, ui, zi, D), D)

def shift(FA, chi, D):
    """residual z-shift z' = z + u*chi; u' fixed by beta_z' = 4u'(1+z'). Returns F'(u',z')."""
    bu, bz = 2*u*FA, 4*u*(1+z)
    zp = z + u*chi
    up = series_div(trunc(u*(FA*(chi + u*sp.diff(chi, u))/2 + (1+z)*(1 + u*sp.diff(chi, z))), D+1), 1 + z + u*chi, D+1)
    bup = trunc(sp.diff(up, u)*bu + sp.diff(up, z)*bz, D+2)
    # F' = bup/(2up) ; up = u*(1+...) so divide by u first
    q = sp.expand(up / u)
    Fp_old = series_div(sp.expand(sp.cancel(bup / (2*u))), q, D)
    ui, zi = inverse(trunc(up, D+1), trunc(zp, D+1), D)
    return trunc(compose(Fp_old, ui, zi, D), D)

if __name__ == '__main__':
    t0 = time.time()
    FA = to_exact_H_gauge(F_hc, H_hc, 4)
    P = sp.Poly(FA, u, z)
    print('exact-H gauge F_A (degree<=4) built in %.1fs' % (time.time()-t0))
    for (i, j), cc in sorted(P.terms(), key=lambda t: (sum(t[0]), t[0])):
        print(f'  u^{i} z^{j}:', sp.factor(cc) if sum((i,j)) <= 2 else sp.expand(cc))
