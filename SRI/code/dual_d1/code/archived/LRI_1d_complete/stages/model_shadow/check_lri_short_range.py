#!/usr/bin/env python3
"""Reproduce algebraic checks in the accompanying 1D long-range Ising note.

Run: python check_lri_short_range.py
Dependencies: sympy and mpmath.
These checks validate algebra and asymptotic residues, not the conjectured
strong/weak duality itself and not an uncomputed multi-loop thermal exponent.
"""
from __future__ import annotations
import argparse
from itertools import product

try:
    import sympy as sp
    import mpmath as mp
except ImportError as exc:
    raise SystemExit("Install dependencies with: python -m pip install sympy mpmath") from exc


def shadow_q(d: mp.mpf, di: mp.mpf, dj: mp.mpf) -> mp.mpf:
    """Even-parity shadow factor: c_chi,ij / c_sigma,ij = K q."""
    return (mp.gamma((1-d+di-dj)/2)*mp.gamma((1-d-di+dj)/2)
            / (mp.gamma((d+di-dj)/2)*mp.gamma((d-di+dj)/2)))


def shadow_product(d: mp.mpf, D: mp.mpf) -> mp.mpf:
    """q(d;d,D) q(d;1-d,D), away from its gamma-function poles."""
    return (mp.gamma((1-2*d+D)/2)*mp.gamma((2-2*d-D)/2)
            / (mp.gamma((2*d-D)/2)*mp.gamma((2*d-1+D)/2)))


def check_gaussian_and_walls() -> None:
    """Verify the covariance coefficient and the noncoincident wall kernel."""
    delta, r, a = sp.symbols("delta r a", positive=True)
    A = 4*sp.gamma(1+delta)*sp.sin(sp.pi*delta/2)/delta
    assert sp.limit(A, delta, 0, dir="+") == 2*sp.pi
    U = (r**delta-a**delta)/delta
    # d_x d_y U(x-y) = -U''(r) for r=x-y>0.
    assert sp.simplify(-sp.diff(U, r, 2)-(1-delta)*r**(-2+delta)) == 0
    assert sp.simplify(sp.limit(U, delta, 0, dir="+")-sp.log(r/a)) == 0
    for text in ("0.01", "0.1", "0.5", "0.9"):
        d = mp.mpf(text)
        # Fourier transform of -(2/d)|x|^d, modulo the zero-mode delta.
        power_transform = (mp.power(2, 1+d)*mp.sqrt(mp.pi)
                           * mp.gamma((1+d)/2)/mp.gamma(-d/2))
        expected = 4*mp.gamma(1+d)*mp.sin(mp.pi*d/2)/d
        assert mp.almosteq(-2*power_transform/d, expected)
    # Normal ordering plus charge neutrality gives the cutoff pair kernel.
    q = (1, -1, 1, -1, 1, -1)
    assert sum(q) == 0
    assert sum(q[i]*q[j] for i in range(len(q)) for j in range(i+1, len(q))) == -sum(v*v for v in q)/2
    print("Gaussian Fourier normalization and A_0=2 pi checked.")
    print("Domain-wall kernel: -U''=(1-delta) r^(-2+delta), U_0=log(r/a).")
    print("Neutral vertex self-normalization identity checked.\n")


def check_pauli_alternation() -> None:
    """Exhaust all charge strings of lengths 1 through 8."""
    plus = sp.Matrix([[0, 1], [0, 0]])
    minus = sp.Matrix([[0, 0], [1, 0]])
    sigma3 = sp.diag(1, -1)
    matrices = {1: plus, -1: minus}
    survivors = 0
    for length in range(1, 9):
        for charges in product((1, -1), repeat=length):
            mat = sp.eye(2)
            for charge in charges:
                mat = mat*matrices[charge]
            trace = sp.trace(mat)
            expected = (length % 2 == 0 and all(charges[i] == -charges[i+1]
                                               for i in range(length-1)))
            assert trace == int(expected)
            if expected:
                survivors += 1
                for cut in range(length+1):
                    left = sp.eye(2)
                    right = sp.eye(2)
                    for charge in charges[:cut]:
                        left = left*matrices[charge]
                    for charge in charges[cut:]:
                        right = right*matrices[charge]
                    assert sp.trace(sigma3*left*sigma3*right) == (-1)**cut
    assert survivors == 8
    print("Pauli trace: exactly two alternating strings survive at each even order.")
    print("Two sigma_3 insertions give (-1)^(number of intervening walls).\n")


def check_shadow_convolution() -> None:
    """Check the Fourier convolution identity away from distributional poles."""
    def F(alpha: mp.mpf) -> mp.mpf:
        return mp.power(2, 1-alpha)*mp.sqrt(mp.pi)*mp.gamma((1-alpha)/2)/mp.gamma(alpha/2)
    for ds, dis, djs in (("0.07", "0.31", "1.27"),
                         ("0.13", "0.22", "0.51"),
                         ("0.18", "0.42", "1.61"),
                         ("0.21", "0.37", "0.79")):
        d, di, dj = map(mp.mpf, (ds, dis, djs))
        p = d+di-dj
        convolution = F(2-2*d)*F(p)/F(p+1-2*d)
        common = mp.sqrt(mp.pi)*mp.gamma(d-mp.mpf("0.5"))/mp.gamma(1-d)
        assert mp.almosteq(convolution, common*shadow_q(d, di, dj))
        assert mp.almosteq(shadow_q(d, d, dj)*shadow_q(d, 1-d, dj),
                          shadow_product(d, dj))
    print("Even-parity shadow convolution and double-shadow gamma product checked.\n")


def check_gff_blocks() -> None:
    """Check the d_chi=1 even-primary expansion as a formal power series."""
    for m in range(2, 21):
        reconstructed = sp.S.Zero
        for N in range(2, m+1, 2):
            aN = sp.Rational(2*N*(N-1))*sp.factorial(N-1)**2/sp.factorial(2*N-2)
            j = m-N
            reconstructed += aN*sp.rf(N, j)**2/(sp.rf(2*N, j)*sp.factorial(j))
        # z^2 + z^2/(1-z)^2, after subtracting the identity.
        expected = (m-1)+int(m == 2)
        assert sp.simplify(reconstructed-expected) == 0
    # General even-N pole residue is checked at several different poles.
    delta = mp.mpf("1e-9")
    gamma2 = mp.mpf("1.7")
    for N in (2, 4, 6, 8, 10):
        D = N-delta+gamma2*delta**2
        ratio = (delta*shadow_product(delta/2, D)
                 / (N*(N-1)/(2*gamma2)))
        assert abs(ratio-1) < mp.mpf("1e-7")
    print("Even-primary GFF block coefficients checked through z^20.")
    print("General even-N shadow residue checked at N=2,4,6,8,10.\n")


def check_rg() -> None:
    delta, u, x, A, F, H, B = sp.symbols("delta u x A F H B")
    # u = g^2. This is an illustrative family consistent with published orders,
    # not a claim to give the most general higher-order beta functions.
    bu = 2*u*(x+u+A*x*u+B*u*u)
    bx = (1+x)*(-delta+4*u+F*u*u+H*delta*u)
    u2, x2 = sp.symbols("u2 x2")
    trial = {u: delta/4+u2*delta**2, x: -delta/4+x2*delta**2}
    sol = sp.solve([
        sp.expand((x+u+A*x*u+B*u*u).subs(trial)).coeff(delta, 2),
        sp.expand(bx.subs(trial)).coeff(delta, 2),
    ], [u2, x2])
    fixed = {key: sp.expand(value.subs(sol)) for key, value in trial.items()}
    matrix = sp.Matrix([bu, bx]).jacobian([u, x])
    trace = sp.series(sp.trace(matrix).subs(fixed), delta, 0, 3).removeO()
    det = sp.series(matrix.det().subs(fixed), delta, 0, 3).removeO()
    d2 = sp.expand(det).coeff(delta, 2)
    coefficient = sp.simplify((sp.Rational(1, 16)-d2)/(2*sp.sqrt(2)))
    assert sp.simplify(d2-(sp.Rational(1, 2)-A/2-F/8)) == 0
    assert sp.simplify(coefficient-(8*A+2*F-7)/(32*sp.sqrt(2))) == 0
    print("RG determinant:", det)
    print("Illustrative delta^(3/2) gap coefficient:", coefficient)
    print("This coefficient is NOT evaluated for the physical higher-order RG.\n")


def check_endpoint_logs() -> None:
    g, a = sp.symbols("g a")
    h = -g/sp.sqrt(2)+a*g*g
    bg = -2*sp.sqrt(2)*g*h+2*g*h*h+g**3
    bh = -sp.sqrt(2)*g*g+2*h*g*g
    condition = sp.series(bh-sp.diff(h, g)*bg, g, 0, 4).removeO().expand()
    assert condition == -6*a*g**3
    assert sp.expand(bg.subs(a, 0)) == 2*g*g+2*g**3
    L, C, p = sp.symbols("L C p", positive=True)
    running = 1/(2*L)+(p*sp.log(L)+C)/L**2
    residual = sp.diff(running, L)+2*running**2+2*running**3
    leading = sp.series(residual, L, sp.oo, 4).removeO()
    assert sp.simplify(leading-(p+sp.Rational(1, 4))/L**3) == 0
    # Integral_L^infty -log(v)/v^3 dv.
    tail = -(sp.log(L)/2+sp.Rational(1, 4))/L**2
    assert sp.simplify(sp.diff(tail, L)-sp.log(L)/L**3) == 0
    print("Critical separatrix: h = -g/sqrt(2) + O(g^3)")
    print("Running coupling: g = 1/(2L) - log(L)/(4L^2) + C/L^2 + ...")
    print("G/M^2 = 1 + 1/L - log(L)/(2L^2) + K/L^2 + ...\n")


def check_rho_residue() -> None:
    delta, c = sp.symbols("delta c", positive=True)
    eps = c*delta**2
    r = delta-eps/2
    # Gamma recursion removes the poles before taking the limit.
    P_regular = (sp.gamma(sp.Rational(3, 2)-delta+eps/2)
                 / sp.gamma(sp.Rational(1, 2)+eps/2)
                 * sp.gamma(1-eps/2)/sp.gamma(1+r)
                 * (r-1)*r/(-eps/2))
    residue = sp.limit(delta*P_regular, delta, 0, dir="+")
    assert sp.simplify(residue-1/c) == 0
    # q(d;d,D_rho)/delta -> pi.
    q_regular = (sp.gamma(-sp.Rational(1, 2)+delta/2-eps/2)
                 * sp.gamma(sp.Rational(3, 2)-delta+eps/2)
                 * (r-1)*r / (sp.gamma(1+r)*sp.gamma(1-delta/2+eps/2)))
    q_residue = sp.limit(q_regular/delta, delta, 0, dir="+")
    assert sp.simplify(q_residue-sp.pi) == 0
    c_solution = sp.solve(sp.Eq(2*sp.pi**2/c, 2), c)[0]
    assert c_solution == sp.pi**2
    print("rho shadow residue: limit delta*P =", residue)
    print("rho mixed-OPE residue: limit q/delta =", q_residue)
    print("Delta_rho = 2-delta+pi^2 delta^2+O(delta^3)")
    print("c_sigma,chi,rho = pi^2 delta^2+O(delta^3)\n")


def check_heavy_averages() -> None:
    print("Even dimension N | mixed weight A_N | GFF weight a_N | averaged gamma_2")
    for n in (2, 4, 6, 8, 10):
        A = sp.Rational(4*(n-1), n)*sp.factorial(n-2)**2/sp.factorial(2*n-2)
        a = 2*n*(n-1)*sp.factorial(n-1)**2/sp.factorial(2*n-2)
        average = sp.simplify(sp.pi**2*n*(n-1)*A/a)
        assert average == 2*sp.pi**2/(n*(n-1))
        print(f"{n:16} | {str(A):16} | {str(a):14} | {average}")
    print("For N>2 this is a weighted coefficient, not a resolved spectrum.\n")


def check_current_four_point_integral() -> None:
    u, v = sp.symbols("u v")
    points = (-3, -1, 2, 5)
    P = sp.prod(u-x for x in points)
    Pv = P.subs(u, v)
    full = (u-v)**2/(P*Pv)
    factored = u**2/P/Pv - 2*(u/P)*(v/Pv) + v**2/P/Pv
    assert sp.cancel(full-factored) == 0
    for k in (0, 1, 2):
        partial = sp.apart(u**k/P, u)
        reconstructed = sum(
            (sp.Rational(x)**k/sp.diff(P, u).subs(u, x))/(u-x)
            for x in points)
        assert sp.cancel(partial-reconstructed) == 0
    print("Current-four-point integrand factorization checked.")
    print("Each remaining one-variable simple-pole integral has zero symmetric PV.")
    print("This is a formal factorized-PV check only; it does not establish the")
    print("fully renormalized four-point function or composite-operator normalization.\n")


def numerical_checks() -> None:
    print("delta | K_plus/(sqrt(2)pi) | rho ratio test | rho mixed test")
    for text in ("1e-2", "1e-3", "1e-4", "1e-5", "1e-6"):
        delta = mp.mpf(text)
        d = delta/2
        t = mp.sqrt(delta)
        Dp = 1+mp.sqrt(2)*t+delta/4
        ss = t/mp.sqrt(2)-mp.mpf(15)*delta/16+(mp.mpf(543)/256-mp.pi**2/6)*t**3/mp.sqrt(2)
        sc = 1/mp.sqrt(2)-t/16-delta/(256*mp.sqrt(2))
        K = (sc/ss)/shadow_q(d, d, Dp)
        Dr = 2-delta+mp.pi**2*delta**2
        ratio = 2*mp.pi**2*shadow_product(d, Dr)/(2/delta)
        mixed = (mp.sqrt(2)*mp.pi*shadow_q(d, d, Dr)*(delta/mp.sqrt(2))
                 / (mp.pi**2*delta**2))
        values = (K/(mp.sqrt(2)*mp.pi), ratio, mixed)
        print(text, " | ", " | ".join(mp.nstr(value, 13) for value in values))
    assert all(abs(value-1) < mp.mpf("1e-4") for value in values)
    print("All three ratios approach one; errors include intentionally omitted orders.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dps", type=int, default=60, help="mpmath decimal precision (>=30)")
    args = parser.parse_args()
    if args.dps < 30:
        parser.error("--dps must be at least 30 to resolve the near-pole tests")
    mp.mp.dps = args.dps
    check_gaussian_and_walls()
    check_pauli_alternation()
    check_shadow_convolution()
    check_gff_blocks()
    check_rg()
    check_endpoint_logs()
    check_rho_residue()
    check_heavy_averages()
    check_current_four_point_integral()
    numerical_checks()
    print("\nAll algebraic and asymptotic checks passed.")


if __name__ == "__main__":
    main()
