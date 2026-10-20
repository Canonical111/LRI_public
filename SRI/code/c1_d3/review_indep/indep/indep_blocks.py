"""Independent conformal-block engine (does NOT import the package).

Derives, with sympy, the Dolan-Osborn quadratic Casimir equation in a chosen
coordinate (z itself or the radial rho, z = 4 rho/(1+rho)^2), acting on monomials
x^p y^q (x = coordinate of z, y = coordinate of zbar), and solves the resulting
recursion for a symmetric double power series
    g(x, y) = sum_{m,n} c_{mn} x^{alpha+m} y^{alpha+n},   alpha = (Delta-ell)/2,
order by order in the total degree m+n (least squares over the overdetermined
per-degree system).  Normalisation: g ~ |z|^Delta P_ell(cos theta_z) (d=3) as z->0,
equivalently (4|rho|)^Delta P_ell(cos phi_rho).

Casimir (Dolan-Osborn): L = 2(D_z + D_zb) + 2(d-2) z zb/(z-zb) [(1-z)d_z - (1-zb)d_zb],
D_z = z^2(1-z)d_z^2 - (a+b+1) z^2 d_z - a b z,  L g = C g,
C = Delta(Delta-d) + ell(ell+d-2), a = -Delta12/2, b = Delta34/2.
"""
import functools
import numpy as np
import sympy as sp
from scipy.special import eval_legendre, eval_chebyt

X, Y, P, Q, A, B, D, CC = sp.symbols('x y p q a b d C')


@functools.lru_cache(None)
def recursion(coord):
    if coord == 'z':
        phi = lambda t: t
    elif coord == 'rho':
        phi = lambda t: 4 * t / (1 + t) ** 2
    else:
        raise ValueError(coord)
    z, zb = phi(X), phi(Y)
    hx = 1 / sp.diff(z, X)   # d/dz = hx d/dx
    hy = 1 / sp.diff(zb, Y)
    # f = x^p y^q ; derivatives divided by f
    fx = P / X; fxx = P * (P - 1) / X ** 2
    fy = Q / Y; fyy = Q * (Q - 1) / Y ** 2
    dz = hx * fx
    dzz = hx ** 2 * fxx + hx * sp.diff(hx, X) * fx
    dzb = hy * fy
    dzbzb = hy ** 2 * fyy + hy * sp.diff(hy, Y) * fy
    Dz = z ** 2 * (1 - z) * dzz - (A + B + 1) * z ** 2 * dz - A * B * z
    Dzb = zb ** 2 * (1 - zb) * dzbzb - (A + B + 1) * zb ** 2 * dzb - A * B * zb
    cross = z * zb / (z - zb) * ((1 - z) * dz - (1 - zb) * dzb)
    R = 2 * (Dz + Dzb) + 2 * (D - 2) * cross - CC
    num, den = sp.fraction(sp.cancel(sp.together(R)))
    assert not (den.free_symbols & {P, Q, A, B, D, CC}), den
    poly = sp.Poly(sp.expand(num), X, Y)
    shifts = []
    for (s, t), coef in poly.terms():
        f = sp.lambdify((P, Q, A, B, D, CC), coef, 'numpy')
        shifts.append((s, t, f))
    sig0 = min(s + t for s, t, _ in shifts)
    return shifts, sig0


def leading(ell, d, Delta, coord):
    """Degree-ell homogeneous coefficients c_{m,ell-m} of the leading term."""
    # |w|^ell * angular(cos th), w = x (complex), with cos th = (x+y)/(2 sqrt(xy))
    # angular = P_ell (d=3), cos(ell th) (d=2); built by sampling on the unit circle.
    th = np.linspace(0.1, 3.0, ell + 3)
    if d == 3:
        ang = eval_legendre(ell, np.cos(th))
    elif d == 2:
        ang = eval_chebyt(ell, np.cos(th)) * (1.0 if ell == 0 else 1.0)
    elif d == 4:
        from scipy.special import eval_gegenbauer
        ang = eval_gegenbauer(ell, 1.0, np.cos(th)) / (ell + 1)  # normalised to 1 at th=0
    # solve sum_m c_m e^{i(2m-ell) th} = ang  (real symmetric => cosines)
    M = np.array([[np.cos((2 * m - ell) * t) for m in range(ell + 1)] for t in th])
    c = np.linalg.lstsq(M, ang, rcond=None)[0]
    scale = 4.0 ** Delta if coord == 'rho' else 1.0
    return c * scale


@functools.lru_cache(None)
def coefficients(Delta, ell, da=0.0, db=0.0, d=3, coord='rho', K=36):
    shifts, sig0 = recursion(coord)
    a = -da / 2; b = db / 2
    Cas = Delta * (Delta - d) + ell * (ell + d - 2)
    al = (Delta - ell) / 2
    c = np.zeros((K + 1, K + 1))
    lead = leading(ell, d, Delta, coord)
    for m in range(ell + 1):
        c[m, ell - m] = lead[m]
    maxres = 0.0
    for deg in range(ell, K + 1):
        T = deg + sig0
        targets = [(M, T - M) for M in range(T + 1)]
        tindex = {t: i for i, t in enumerate(targets)}
        Amat = np.zeros((len(targets), deg + 1))
        rhs = np.zeros(len(targets))
        for s, t, f in shifts:
            # unknown/known source monomial (m,n) = (M-s, N-t)
            for (M, N), i in tindex.items():
                m, n = M - s, N - t
                if m < 0 or n < 0 or m + n > deg:
                    continue
                k = f(al + m, al + n, a, b, d, Cas)
                if m + n == deg:
                    Amat[i, m] += k
                else:
                    rhs[i] -= k * c[m, n]
        if deg == ell:
            cl = np.array([c[m, deg - m] for m in range(deg + 1)])
            res = Amat @ cl - rhs
            maxres = max(maxres, np.max(np.abs(res)) / (np.max(np.abs(Amat)) * np.max(np.abs(cl))))
            continue
        sol, _, rank, sv = np.linalg.lstsq(Amat, rhs, rcond=None)
        res = Amat @ sol - rhs
        maxres = max(maxres, np.max(np.abs(res)) / (np.max(np.abs(Amat)) * np.max(np.abs(sol)) + np.max(np.abs(rhs)) + 1e-300))
        if sv[-1] < 1e-10 * sv[0]:
            raise ValueError(f'degenerate Casimir recursion at degree {deg} (Delta={Delta}, ell={ell})')
        for m in range(deg + 1):
            c[m, deg - m] = sol[m]
    return c, maxres


def evaluate(Delta, ell, zz, da=0.0, db=0.0, d=3, coord='rho', K=36):
    """Evaluate the block at complex z (array)."""
    zz = np.asarray(zz, dtype=complex)
    c, _ = coefficients(float(Delta), int(ell), float(da), float(db), d, coord, K)
    if coord == 'rho':
        w = zz / (1 + np.sqrt(1 - zz)) ** 2
    else:
        w = zz
    al = (Delta - ell) / 2
    pw = w[..., None] ** np.arange(K + 1)
    pwb = np.conj(w)[..., None] ** np.arange(K + 1)
    val = np.einsum('...m,mn,...n->...', pw, c, pwb)
    return (np.abs(w) ** (2 * al) * val).real


def evaluate_safe(Delta, ell, zz, da=0.0, db=0.0, d=3, coord='rho', K=36, h=1e-5):
    """Evaluate; at a degenerate (null-state) dimension use the symmetric average of Delta+-h
    (valid when the block is regular there, error O(h^2))."""
    try:
        return evaluate(Delta, ell, zz, da, db, d, coord, K)
    except ValueError:
        return 0.5 * (evaluate(Delta + h, ell, zz, da, db, d, coord, K) + evaluate(Delta - h, ell, zz, da, db, d, coord, K))
