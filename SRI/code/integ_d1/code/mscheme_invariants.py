"""Magnetization scheme: from F(u,X,delta) = sum f[m,n,k] u^m X^n delta^k to the C_n.
beta_X = (1+X)(4u - delta) exact; fixed point u* = delta/4, F(u*, X*, delta) = 0;
T_h = 2u* F_u, D_h = -8u*(1+X*) F_X; T = (1-delta/2) T_h, D = (1-delta/2)^2 D_h;
Delta_eps = 1 + T/2 - sqrt(T^2/4 - D), delta = 2 t^2, C_n = [t^n] Delta_eps."""
import sympy as sp
u, X, d, t = sp.symbols('u X delta t')
def fsym(m, n, k):
    return sp.Symbol(f'f_{m}_{n}_{k}')
def general_F(order):
    """F = X + sum over (m,n,k), m+n+k <= order, excluding the exact X term; f_0_n_0 = 0 for n >= 2 (F(0,X,0) = X)."""
    F = X
    for m in range(0, order + 1):
        for n in range(0, order + 1 - m):
            for k in range(0, order + 1 - m - n):
                if (m, n, k) == (0, 1, 0) or (m, k) == (0, 0): continue
                F += fsym(m, n, k) * u**m * X**n * d**k
    return F
def C_list(order):
    """Symbolic C_1..C_{2 order} in terms of the f's (F truncated at total degree `order`)."""
    F = general_F(order)
    us = d/4
    # fixed point X* = sum a_i d^i
    a = sp.symbols(f'a1:{order+1}')
    Xs = sum(a[i]*d**(i+1) for i in range(order))
    eq = sp.expand(sp.series(F.subs({u: us, X: Xs}), d, 0, order + 1).removeO())
    sol = {}
    for i in range(order):
        ci = sp.expand(eq.coeff(d, i + 1).subs(sol))
        s = sp.solve(ci, a[i])[0]; sol[a[i]] = sp.expand(s)
    Xs = sp.expand(Xs.subs(sol))
    Fu, FX = sp.diff(F, u), sp.diff(F, X)
    Th = sp.series(2*us*Fu.subs({u: us, X: Xs}), d, 0, order + 1).removeO()
    Dh = sp.series(-8*us*(1 + Xs)*FX.subs({u: us, X: Xs}), d, 0, order + 1).removeO()
    T = sp.expand((1 - d/2)*Th); D = sp.expand((1 - d/2)**2*Dh)
    Tt = sp.expand(T.subs(d, 2*t**2)); Dt = sp.expand(D.subs(d, 2*t**2))
    disc = sp.expand(Tt**2/4 - Dt)          # = 4 t^2 (1 + ...)
    q = sp.expand(sp.series(disc/(4*t**2), t, 0, 2*order).removeO())
    root = 2*t*sp.series(sp.sqrt(q), t, 0, 2*order).removeO()
    De = sp.expand(sp.series(1 + Tt/2 - root, t, 0, 2*order + 1).removeO())
    return [sp.expand(De.coeff(t, n)) for n in range(1, 2*order + 1)]
if __name__ == '__main__':
    import time; t0 = time.time()
    Cs = C_list(3)
    print('built in %.1fs' % (time.time() - t0))
    for n, c in enumerate(Cs, 1):
        print(f'C{n} =', c)
