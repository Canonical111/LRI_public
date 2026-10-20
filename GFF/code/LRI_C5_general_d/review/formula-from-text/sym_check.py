#!/usr/bin/env python3
"""Independent symbolic checks of the printed formulas of general_d.tex (review key formula-from-text).

Everything is re-derived from first principles:
  * W_r(d;b) = -N_b^r Res_{t=0} Xi_r(t;b)/D(t)^r   (closing the Barnes contour to the right, clockwise)
  * Xi_r(t;b) = sum_{k=0}^{r-2} c_{r,k} cos 2 pi k (t+b/4)  (finite Fourier theorem with top mode zero)
  * samples: t=0 (residue sum), t=-b/4, t=1/2-b/4
  * local expansion at the pole node: N g = -(T/u) exp(sum lambda_m u^m/m!)
and compared with the printed boxed formulas.  s = sin(pi b/2), c = cos(pi b/2); at b=d/2: s=S, c=C.
"""
import sympy as sp

t, u = sp.symbols('t u')
s, c = sp.symbols('s c', positive=True)   # s = sin(pi b/2), c = cos(pi b/2)
pi = sp.pi


def cheb_T(k, x):
    return sp.chebyshevt(k, x)


def cheb_U(k, x):
    return sp.chebyshevu(k, x) if k >= 0 else sp.Integer(0)


def simp(e):
    e = sp.expand(e)
    e = e.subs(s**2, 1 - c**2) if False else e
    # reduce powers of s using s^2 = 1-c^2
    e = sp.expand(e)
    p = sp.Poly(e, s) if e.has(s) else None
    if p is None:
        return sp.simplify(e)
    out = 0
    for (k,), coeff in p.terms():
        out += coeff * (1 - c**2)**(k // 2) * s**(k % 2)
    return sp.simplify(sp.expand(out))


def mode_cos(k, tt):
    # cos(2 pi k (t + b/4)) = cos(2 pi k t) cos(pi k b/2) - sin(2 pi k t) sin(pi k b/2)
    return sp.cos(2 * pi * k * tt) * cheb_T(k, c) - sp.sin(2 * pi * k * tt) * s * cheb_U(k - 1, c)


def residue_weights(r, order_extra=0):
    """Res_{t=0} cos 2pi k(t+b/4) / (sin(pi t) sin(pi(t+sigma)))^r for k=0..r-2."""
    D = sp.sin(pi * t) * (s * sp.cos(pi * t) + c * sp.sin(pi * t))
    res = []
    for k in range(r - 1):
        expr = mode_cos(k, t) / D**r
        ser = sp.series(expr, t, 0, 1).removeO()
        res.append(sp.simplify(ser.coeff(t, -1)))
    return res


print("=== S1: W_r from the modes (residue functional) ===")
C4 = sp.symbols('C0:3')   # C_k = N^4 c_{4,k}
R4 = residue_weights(4)
W4_mine = -sum(C4[k] * R4[k] for k in range(3))
W4_print = 4 / (pi * s**7) * (c * (3 + 2 * c**2) * C4[0] + (1 + 4 * c**2) * C4[1] + 5 * c * C4[2])
d4 = simp(sp.together(W4_mine - W4_print) * s**7)
print("W4 (mine - printed) * s^7 =", d4)
C3 = sp.symbols('D0:2')
R3 = residue_weights(3)
W3_mine = -sum(C3[k] * R3[k] for k in range(2))
W3_print = -2 / (pi * s**5) * ((1 + 2 * c**2) * C3[0] + 3 * c * C3[1])
d3 = simp(sp.together(W3_mine - W3_print) * s**5)
print("W3 (mine - printed) * s^5 =", d3)

print("\n=== S2: P4 and L_d from the three samples ===")
XT, X0, Xh = sp.symbols('X_T X_0 X_h')
# samples in terms of normalized modes: t=-b/4 -> all cos = 1; t=1/2-b/4 -> (-1)^k; t=0 -> cos(pi k b/2) = T_k(c)
sol = sp.solve([sp.Eq(X0, C4[0] + C4[1] + C4[2]),
                sp.Eq(Xh, C4[0] - C4[1] + C4[2]),
                sp.Eq(XT, C4[0] + c * C4[1] + (2 * c**2 - 1) * C4[2])], C4, dict=True)[0]
W4_samples = sp.simplify(W4_mine.subs(sol))
P4_print = 2 / (pi * s**7) * ((1 + c)**2 * (1 + 2 * c) * X0 - (1 - c)**2 * (1 - 2 * c) * Xh - 2 * c * XT)
print("P4: W4(samples) - printed =", simp(sp.together(W4_samples - P4_print) * s**7))
# L = d/db W4 ; coefficients depend on b through s, c: ds/db = (pi/2) c, dc/db = -(pi/2) s
coef = {Xv: sp.diff(W4_samples, Xv) for Xv in (X0, Xh, XT)}
dcoef = {Xv: sp.diff(coef[Xv], s) * (pi / 2) * c + sp.diff(coef[Xv], c) * (-(pi / 2) * s) for Xv in coef}
L_motion = sum(dcoef[Xv] * Xv for Xv in coef)
L_motion_print = -1 / s**8 * ((1 + c)**2 * (4 + 9 * c + 8 * c**2) * X0 + (1 - c)**2 * (4 - 9 * c + 8 * c**2) * Xh
                              - 2 * (1 + 6 * c**2) * XT)
print("L (weight motion part) - printed =", simp(sp.together(L_motion - L_motion_print) * s**8))
X0p, Xhp, XTp = sp.symbols("X_0' X_h' X_T'")
L_frozen = coef[X0] * X0p + coef[Xh] * Xhp + coef[XT] * XTp
DL_print = (1 + c)**2 * (1 + 2 * c) * X0p - (1 - c)**2 * (1 - 2 * c) * Xhp - 2 * c * XTp
print("L (frozen part) - 2/(pi s^7) D_L =", simp(sp.together(L_frozen - 2 / (pi * s**7) * DL_print) * s**7))

print("\n=== S3: 3Q and Z_d from T3, M3 ===")
T3, M3 = sp.symbols('T3 M3')
# N^3 Xi_3(0) = -pi^3 s^3 T3 = C0 + c C1 ; N^3 Xi_3(1/2-b/4) = cos^6(pi b/4) M3 = (1+c)^3/8 M3 = C0 - C1
sol3 = sp.solve([sp.Eq(-pi**3 * s**3 * T3, C3[0] + c * C3[1]), sp.Eq((1 + c)**3 / 8 * M3, C3[0] - C3[1])], C3,
                dict=True)[0]
c0hat_print = c * (1 + c)**2 / 8 * M3 - pi**3 * s**3 * T3 / (1 + c)
print("c0hat (mine - printed) =", simp(sp.together(sol3[C3[0]] - c0hat_print) * (1 + c)))
W3_samples = sp.simplify(W3_mine.subs(sol3))
W3_inT3c0 = 6 * pi**2 / s**2 * T3 + 4 / (pi * s**3) * sp.Symbol('c0')
print("W3(samples) - [6pi^2/s^2 T3 + 4/(pi s^3) c0hat] =",
      simp(sp.together(W3_samples - W3_inT3c0.subs(sp.Symbol('c0'), c0hat_print)) * s**5 * (1 + c)))

# Z = (1/9) d^2W3/db^2 using W3 = 6pi^2 s^-2 T3 + (4/pi) s^-3 c0 with b-dependent T3(b), c0(b)
bb = sp.Symbol('b')
Tf = sp.Function('T')(bb)
cf = sp.Function('c0')(bb)
sf = sp.sin(pi * bb / 2)
W3b = 6 * pi**2 / sf**2 * Tf + 4 / (pi * sf**3) * cf
dW3 = sp.diff(W3b, bb)
d2W3 = sp.diff(W3b, bb, 2)
T1, T2, c00, c01, c02 = sp.symbols('T1 T2 c00 c01 c02')
rep = {sp.Derivative(Tf, (bb, 2)): T2, sp.Derivative(Tf, bb): T1, sp.Derivative(cf, (bb, 2)): c02,
       sp.Derivative(cf, bb): c01}


def tosc(e):
    e = e.subs(rep).subs({Tf: T3, cf: c00})
    e = e.subs({sp.sin(pi * bb / 2): s, sp.cos(pi * bb / 2): c})
    return e


dW3s = tosc(dW3)
d2W3s = tosc(d2W3)
T1sol = sp.solve(sp.Eq(dW3s, 0), T1)[0]           # dW3/db = 0 at b = d/2
Z_mine = sp.simplify(d2W3s.subs(T1, T1sol) / 9)
# printed: Z = 2pi^2/(3S^2) T3'' - pi^2 cos(pi d/2) Q/(6 S^2) + 1/9 [ pi(1+C^2) c0/S^5 - 4C c0'/S^4 + 4 c0''/(pi S^3) ]
cos_pid2 = 2 * c**2 - 1      # cos(pi d/2) = cos(2 pi q) with C = cos(pi q)
Qd = (6 * pi**2 / s**2 * T3 + 4 / (pi * s**3) * c00) / 3
Z_print = 2 * pi**2 / (3 * s**2) * T2 - pi**2 * cos_pid2 * Qd / (6 * s**2) + sp.Rational(1, 9) * (
    pi * (1 + c**2) * c00 / s**5 - 4 * c * c01 / s**4 + 4 * c02 / (pi * s**3))
print("Z (mine, dW3/db=0 used) - printed =", simp(sp.together(Z_mine - Z_print) * s**6))
# u,v statement: second derivatives only through (u T3'' + v M3'')/9
M2 = sp.Symbol('M2')
c02_expr = c * (1 + c)**2 / 8 * M2 - pi**3 * s**3 * T2 / (1 + c)   # c0hat'' : only the 2nd-derivative part
Zsec = sp.expand(2 * pi**2 / (3 * s**2) * T2 + sp.Rational(1, 9) * 4 * c02_expr / (pi * s**3))
u_print = 2 * pi**2 * (1 + 2 * c) / s**2
v_print = c * (1 + c)**2 / (2 * pi * s**3)
print("second-derivative part - (u T3''+v M3'')/9 =",
      simp(sp.together(Zsec - (u_print * T2 + v_print * M2) / 9) * s**3 * (1 + c)))

print("\n=== S4: pole-node forms gdr:taylorW ===")
# N^r Xi_r(u) = (-1)^r (D(u)/u)^r sum_k mu_k u^k + O(u^r), with sum dT^r exp(r sum lambda_m u^m/m!) = sum mu_k u^k
l1, l2, l3 = sp.symbols('l1 l2 l3')   # stand for linear functionals; products l1^2 -> separate symbol
S0, S1, S11, S2 = sp.symbols('S0 S1 S11 S2')  # sum dT^r, sum dT^r l1, sum dT^r l1^2, sum dT^r l2


def poleform(r):
    Dser = sp.sin(pi * u) * (s * sp.cos(pi * u) + c * sp.sin(pi * u))
    expo = sp.exp(r * (l1 * u + l2 * u**2 / 2 + l3 * u**3 / 6))
    lhs_local = sp.series((-1)**r * (Dser / u)**r * expo, u, 0, r - 1).removeO()
    Cs = sp.symbols('K0:%d' % (r - 1))
    rhs = sum(Cs[k] * mode_cos(k, u) for k in range(r - 1))
    rhs = sp.series(rhs, u, 0, r - 1).removeO()
    eqs = [sp.Eq(sp.expand(lhs_local).coeff(u, j), sp.expand(rhs).coeff(u, j)) for j in range(r - 1)]
    sol = sp.solve(eqs, Cs, dict=True)[0]
    Rr = residue_weights(r)
    W = -sum(sol[Cs[k]] * Rr[k] for k in range(r - 1))
    W = sp.expand(W)
    # linearize: monomials in l1,l2 -> functionals
    W = W.subs({l1**2: S11}).subs({l1: S1, l2: S2})
    return sp.expand(W)


kap = pi * c / s
W3pole = poleform(3)
W3pole_print = 2 * pi**2 * S0 - 6 * kap * S1


# compare by treating the free term (no S symbol) as multiplying S0 = sum d T^r
def lin_compare(Wsym, Wprint):
    Wsym = sp.expand(Wsym)
    free = Wsym.subs({S1: 0, S11: 0, S2: 0})
    rest = sp.expand(Wsym - free)
    Wsym2 = free * S0 + rest
    return simp(sp.together(sp.expand(Wsym2 - Wprint)) * s**8)


print("W3 pole-node (mine - printed) =", lin_compare(W3pole, W3pole_print))
W4pole = poleform(4)
W4pole_print = 4 * kap * (4 * S11 + S2 - pi**2 / 3 * S0) - 8 * pi**2 * S1
print("W4 pole-node (mine - printed) =", lin_compare(W4pole, W4pole_print))

print("\n=== S5: C5(d) assembly vs gs:C5 ===")
A, R, U, V, Xp, P5, K, Ld, Zd, Q, P4 = sp.symbols('A R U V X P5 K L Z Q P4')
Sd, Cd = sp.symbols('S C', positive=True)
DLs, T3pp, c0, c0p, c0pp = sp.symbols('D_L T3pp c0 c0p c0pp')
gsC5 = (-1536 * (P5 + K) + 384 * A * P4 - 576 * Ld - 1728 * Q**2 + 720 * A**2 * Q + 1008 * Q * R + 7152 * Zd
        - 15 * A**4 - 90 * A**2 * R + 414 * A * U - 108 * A * V - 117 * R**2 - 75 * Xp)
P4e = 2 / (pi * Sd**7) * ((1 + Cd)**2 * (1 + 2 * Cd) * X0 - (1 - Cd)**2 * (1 - 2 * Cd) * Xh - 2 * Cd * XT)
Le = (-1 / Sd**8 * ((1 + Cd)**2 * (4 + 9 * Cd + 8 * Cd**2) * X0 + (1 - Cd)**2 * (4 - 9 * Cd + 8 * Cd**2) * Xh
                    - 2 * (1 + 6 * Cd**2) * XT) + 2 / (pi * Sd**7) * DLs)
cospd2 = 2 * Cd**2 - 1
Qe = 2 * pi**2 / Sd**2 * T3 + 4 / (3 * pi * Sd**3) * c0
Ze = (2 * pi**2 / (3 * Sd**2) * T3pp - pi**2 * cospd2 * Q / (6 * Sd**2)
      + sp.Rational(1, 9) * (pi * (1 + Cd**2) * c0 / Sd**5 - 4 * Cd * c0p / Sd**4 + 4 * c0pp / (pi * Sd**3)))
lhs = gsC5.subs({P4: P4e, Ld: Le, Zd: Ze})
k0 = (1 + Cd)**2 * (768 * A * (1 + 2 * Cd) / (pi * Sd**7) + 576 * (4 + 9 * Cd + 8 * Cd**2) / Sd**8)
kh = (1 - Cd)**2 * (-768 * A * (1 - 2 * Cd) / (pi * Sd**7) + 576 * (4 - 9 * Cd + 8 * Cd**2) / Sd**8)
kT = -1536 * A * Cd / (pi * Sd**7) - 1152 * (1 + 6 * Cd**2) / Sd**8
rhs = (-1536 * (P5 + K) - 1728 * Q**2 + (720 * A**2 + 1008 * R - 1192 * pi**2 * cospd2 / Sd**2) * Q
       + k0 * X0 + kh * Xh + kT * XT - 1152 / (pi * Sd**7) * DLs + 4768 * pi**2 / Sd**2 * T3pp
       + sp.Rational(2384, 3) * (pi * (1 + Cd**2) * c0 / Sd**5 - 4 * Cd * c0p / Sd**4 + 4 * c0pp / (pi * Sd**3))
       - 15 * A**4 - 90 * A**2 * R + 414 * A * U - 108 * A * V - 117 * R**2 - 75 * Xp)
print("gs:C5 with substitutions - gdr:C5reduced =", sp.simplify(sp.expand(lhs - rhs)))
# and Q itself: Q from the 3Q formula
print("Q_d printed in gdr:C5 vs gdr:Q/3:", sp.simplify(Qe - (6 * pi**2 / Sd**2 * T3 + 4 / (pi * Sd**3) * c0) / 3))

print("\n=== negative controls (must be nonzero) ===")
P4_bad = 2 / (pi * s**7) * ((1 + c)**2 * (1 + 2 * c) * X0 - (1 - c)**2 * (1 - 2 * c) * Xh - 3 * c * XT)
print("P4 with 2C->3C:", simp(sp.together(W4_samples - P4_bad) * s**7))
Z_bad = Z_print + sp.Rational(1, 9) * c * c01 / s**4
print("Z with -4C c0' -> -3C c0':", simp(sp.together(Z_mine - Z_bad) * s**6))
print("W4 pole with lambda2 coefficient 2:", lin_compare(W4pole, W4pole_print + 4 * kap * S2))
rhs_bad = rhs + 1 / Sd**8 * X0
print("C5 with k_0 perturbed:", sp.simplify(sp.expand(lhs - rhs_bad)))
