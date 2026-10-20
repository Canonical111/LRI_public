"""Drafter's independent exact checks (sympy, polynomial algebra only) for note_insert.tex.
The analytic series (Gamma expansions, residues rho_p, C_j) are checked in check_series.wl (Mathematica).

  A. C5(2): substitution of the two closed forms into gc:d2coefficients.
  B. L2: reduction W'(1/2)/2 from the residue functional (rho data taken from check_series.wl),
     collapse with (R1),(R2), and the elliptic evaluation of the single sums.
  C. L2: Bell polynomial F4 and F_{4,1} (gs:Fpolys).
  D. K2: twelve cells (found from a grid), KLT phase sum, reduction with the moment relations.
  E. K2: Laurent extraction of [t^2](J_t - J_t^Gamma) with symbolic Taylor data
     (Gamma series taken from check_series.wl).
Every reported residual must be 0.
"""
import itertools
import sympy as sp

ok = True
def report(name, expr):
    global ok
    e = sp.expand(expr)
    print(f"{name}: {e}", flush=True)
    if e != 0:
        ok = False

pi = sp.pi
half = sp.Rational(1, 2)

# ---------------------------------------------------------------- A. C5(2)
P5, P4, Q2, G, z3, a = sp.symbols('P5 P4 Q2 G z3 a')   # a = log 2
L2 = -2*a*P4
K2 = 32*G**2 - 28*z3*a
lhs = -1536*(P5 + K2) + 1536*a*P4 - 576*L2 - 1728*Q2**2 + (11520*a**2 + 28608*G)*Q2 - 3840*a**4 - 21456*a*z3
rhs972 = -32*P5 + 56*a*P4 - 36*Q2**2 + (240*a**2 + 596*G)*Q2 - 1024*G**2 + 449*z3*a - 80*a**4
report("A  46656 C5(2)/48 - (972 C5(2) formula)", lhs/48 - rhs972)
L2s = sp.symbols('L2s')
lhsK = (-1536*(P5 + K2) + 1536*a*P4 - 576*L2s - 1728*Q2**2 + (11520*a**2 + 28608*G)*Q2
        - 3840*a**4 - 21456*a*z3)/48
rhsK = -32*P5 + 32*a*P4 - 12*L2s - 36*Q2**2 + (240*a**2 + 596*G)*Q2 - 80*a**4 - 1024*G**2 + 449*a*z3
report("A' K2 inserted, L2 symbolic", lhsK - rhsK)
A_ = 4*a
report("A'' general-d form 384 A P4 - 576 L2 = 672 A P4 at L2=-(A/2)P4", 384*A_*P4 - 576*(-(A_/2)*P4) - 672*A_*P4)

# ---------------------------------------------------------------- B. L2 reduction
x = sp.symbols('x')
# rho_p(x) closed forms (verified against the residue definition in check_series.wl)
rho = {
    0: -4*(sp.cos(2*pi*x) + 4)*sp.cos(pi*x)/(pi*sp.sin(pi*x)**7),
    1: 4*(4*sp.sin(pi*x)**2 - 5)/(pi*sp.sin(pi*x)**7),
    2: 4*(sp.sin(pi*x)**2 - 5)*sp.cos(pi*x)/(pi*sp.sin(pi*x)**7),
}
vals = [sp.nsimplify(rho[p].subs(x, half)) for p in (0, 1, 2)]
ders = [sp.nsimplify(sp.diff(rho[p], x).subs(x, half)) for p in (0, 1, 2)]
print("   rho_p(1/2) =", vals, "  rho_p'(1/2) =", ders, flush=True)
report("B  rho_0(1/2)", vals[0]); report("B  rho_2(1/2)", vals[2]); report("B  rho_1(1/2)+4/pi", vals[1] + 4/pi)
report("B  rho_0'(1/2)-12", ders[0] - 12); report("B  rho_1'(1/2)", ders[1]); report("B  rho_2'(1/2)-16", ders[2] - 16)
a_, b_, Ap, Bp, S1, S2, lg = sp.symbols('a_ b_ Ap Bp S1 S2 lg')   # lg = log 2
# W = -[rho0 A^2 + 2 rho1 A B + rho2 B^2]; at 1/2: W = -(2 rho1 a b), W' = -(rho0' a^2 + 2 rho1 (A'b + aB') + rho2' b^2)
W0 = -(vals[0]*a_**2 + 2*vals[1]*a_*b_ + vals[2]*b_**2)
W1 = -(ders[0]*a_**2 + 2*ders[1]*a_*b_ + ders[2]*b_**2 + 2*vals[0]*a_*Ap + 2*vals[1]*(Ap*b_ + a_*Bp) + 2*vals[2]*b_*Bp)
report("B  W(1/2) - 8ab/pi", W0 - 8*a_*b_/pi)
report("B  W'(1/2)/2 - [-6a^2-8b^2+(4/pi)(A'b+aB')]", W1/2 - (-6*a_**2 - 8*b_**2 + 4/pi*(Ap*b_ + a_*Bp)))
L2red = sp.expand((W1/2).subs({Ap: pi*b_ + 4*pi**2*S1, Bp: 2*pi*a_ - 2*pi*S2}))
report("B  L2 - (2a^2-4b^2+16 pi b S1 - 8 a S2)", L2red - (2*a_**2 - 4*b_**2 + 16*pi*b_*S1 - 8*a_*S2))
L2fin = L2red.subs({S1: (pi*b_ - 2*a_*lg)/(4*pi**2), S2: a_/4 + b_*lg/pi})
report("B  L2 + 2 log2 W(1/2)", L2fin + 2*lg*W0)
report("B  A'(1/2) = 2 pi b - 2 log2 a", (pi*b_ + 4*pi**2*(pi*b_ - 2*a_*lg)/(4*pi**2)) - (2*pi*b_ - 2*lg*a_))
report("B  B'(1/2) = (3pi/2) a - 2 log2 b", (2*pi*a_ - 2*pi*(a_/4 + b_*lg/pi)) - (sp.Rational(3, 2)*pi*a_ - 2*lg*b_))
# Taylor data from (4.1),(4.2):  h = pi^2 Sc4,  h_u = 4 pi^2 Sc4a,  h_x = 4 pi^2 (S1 + psi_h Sc4),
#   h_ux = pi^2 (16 Sc4psia + 4 Sc4z) with psi(k+1/2) = beta_k + psi_h, S2 = 4 Sc4ab + Sc4z
Sc4, Sc4a, Sc4ab, Sc4z, psih = sp.symbols('Sc4 Sc4a Sc4ab Sc4z psih')
h = pi**2*Sc4; hu = 4*pi**2*Sc4a; hx = 4*pi**2*(S1 + psih*Sc4)
hux = pi**2*(16*(Sc4ab + psih*Sc4a) + 4*Sc4z)
N2p = -4*psih                         # (N_x^2)'(1/2)
B0 = -hu/(2*pi)                       # from (4.2) at 1/2
A0 = h                                # from (4.1) at 1/2
Aprime = N2p*h + hx + pi*B0           # derivative of (4.1)
Bprime = -(N2p*hu - 4*pi**2*h + hux)/(2*pi)   # derivative of (4.2)
aN, bN = pi**2*Sc4, -2*pi*Sc4a       # note normalization a, b
S2expr = 4*Sc4ab + Sc4z
report("B  A(1/2) = a", A0 - aN); report("B  B(1/2) = b", B0 - bN)
report("B  A'(1/2) = pi b + 4 pi^2 S1", Aprime - (pi*bN + 4*pi**2*S1))
report("B  B'(1/2) = 2 pi a - 2 pi S2", Bprime - (2*pi*aN - 2*pi*S2expr))
# elliptic evaluation (C62d normalization of the sums, note normalization a,b)
M, N = sp.symbols('M N')
FGlogk, FGw, G2one, G2logk = -pi*M/2, -lg*N, 2*M, -pi*N
Rr = pi*N/4 - lg*M
G2w = -2*Rr - 4*lg*M
FGlogkp = (FGlogk - FGw)/2
G2logkp = (G2logk - G2w)/2
report("B  FG[log k'] = -pi M/4 + log2 N/2", FGlogkp - (-pi*M/4 + lg*N/2))
report("B  G2[log k'] = log2 M - pi N/4", G2logkp - (lg*M - pi*N/4))
Sc4_e = 4/pi**2*(2/pi)*N
Sc4a_e = 4/pi**2*(-G2one - 2/pi*FGlogk)
S1_e = 4/pi**2*(-(2/pi))*FGlogkp
S2_e = sp.Rational(1, 2)*(4/pi**2*(4*G2logkp + 2*pi*N) + 0)      # the two FG[log k log k'] terms cancel
report("B  a = 8N/pi", pi**2*Sc4_e - 8*N/pi)
report("B  b = 8M/pi", -2*pi*Sc4a_e - 8*M/pi)
report("B  (R1)", S1_e - (pi*(8*M/pi) - 2*(8*N/pi)*lg)/(4*pi**2))
report("B  (R2)", S2_e - ((8*N/pi)/4 + (8*M/pi)*lg/pi))
# the cross-term cancellation inside S2: (1/2)[(4/pi^2) int g*(G3) + (8/pi^2) int log k g (G2 doubled)]
X = sp.symbols('X')   # X = FG[log k log k']
first = 4/pi**2*(4*G2logkp + 2*pi*N + 8/pi*X)
second = 8/pi**2*(-(4/pi)*X)
report("B  S2 cross terms cancel", sp.Rational(1, 2)*(first + second) - S2_e)

# ---------------------------------------------------------------- C. Bell polynomials
u = sp.symbols('u')
l1, l2, l3, e1, e2, e3 = sp.symbols('l1 l2 l3 e1 e2 e3')
F4 = sp.Rational(32, 3)*l1**3 + 8*l1*l2 + sp.Rational(2, 3)*l3
F41 = 32*l1**2*e1 + 8*e1*l2 + 8*l1*e2 + sp.Rational(2, 3)*e3
report("C  F41 - sum dF4/dl_j eta_j", sp.diff(F4, l1)*e1 + sp.diff(F4, l2)*e2 + sp.diff(F4, l3)*e3 - F41)
expo = sp.series(sp.exp(4*(l1*u + l2*u**2/2 + l3*u**3/6)), u, 0, 4).removeO()
report("C  F4 - [u^3] exp(4 sum l_j u^j/j!)", expo.coeff(u, 3) - F4)
# Lseries summand = (1/2) d/dx [T^4 F4] with (1/2) dlogT/dx = mu1, (1/2) dlambda_j/dx = eta_j
mu1, T = sp.symbols('mu1 T')
lhs_d = sp.Rational(1, 2)*(4*T**4*(2*mu1)*F4 + T**4*(sp.diff(F4, l1)*2*e1 + sp.diff(F4, l2)*2*e2 + sp.diff(F4, l3)*2*e3))
report("C  (1/2) d[T^4 F4] - T^4(4 mu1 F4 + F41)", lhs_d - T**4*(4*mu1*F4 + F41))

# ---------------------------------------------------------------- D. K2: twelve cells and KLT phase sum
forms = [lambda X, Y: X, lambda X, Y: 1 - X, lambda X, Y: Y, lambda X, Y: 1 - Y, lambda X, Y: Y - X]

def jmap(X, Y):
    """I_j with int_R U = 2 I_j, from the inner elliptic integrals (e1<e2<e3: (-inf,e1),(e2,e3) give K(m),
    (e1,e2),(e3,inf) give K(1-m), m=(e3-e2)/(e3-e1)) and the outer Euler moments."""
    e = sorted([0, 1, Y])
    kind = 'm' if (X < e[0] or e[1] < X < e[2]) else '1-m'
    if 0 < Y < 1:     # m = 1-y : K(1-y) -> I2 ; K(y) -> I1
        return 2 if kind == 'm' else 1
    if Y > 1:         # m = (y-1)/y : K((y-1)/y) -> I4 ; K(1/y) -> I3
        return 4 if kind == 'm' else 3
    return 6 if kind == 'm' else 5   # Y<0: m = 1/(1-y) : K(1/(1-y)) -> I6 ; K(-y/(1-y)) -> I5

grid = [sp.Rational(k, 7) for k in range(-20, 30)]
cells = {}
for Xv in grid:
    for Yv in grid:
        vv = [f(Xv, Yv) for f in forms]
        if any(v == 0 for v in vv):
            continue
        sig = tuple(1 if v > 0 else -1 for v in vv)
        j = jmap(Xv, Yv)
        assert cells.setdefault(sig, j) == j
print(f"   number of cells: {len(cells)}; cell -> j:", sorted(cells.items(), key=lambda kv: kv[1]), flush=True)
assert len(cells) == 12
Isym = sp.symbols('I1:7')
I3s, I4s = Isym[2], Isym[3]
qq, ss, cc = sp.symbols('qq ss cc')
total = 0
for (s1, j1), (s2, j2) in itertools.product(cells.items(), repeat=2):
    n = sum(1 for f in (0, 1, 2, 4) if s1[f] != s2[f])   # exponent -1/2: phase e^{-i pi/2} = -i
    m = 1 if s1[3] != s2[3] else 0                        # exponent tau-1: phase e^{i pi (tau-1)} = -q
    total += (-sp.I)**n*(-qq)**m*(2*Isym[j1 - 1])*(2*Isym[j2 - 1])
Irot = sp.expand(-sp.Rational(1, 4)*total)
twelve = 4*(sp.I*Isym[0]*Isym[1] - sp.I*qq*Isym[0]*Isym[3] - sp.I*Isym[0]*Isym[4] + Isym[0]*Isym[5]
            - sp.I*qq*Isym[1]*Isym[2] - qq*Isym[1]*Isym[3] + Isym[1]*Isym[4] + sp.I*Isym[2]*Isym[3]
            + sp.I*qq*Isym[2]*Isym[4] - qq*Isym[2]*Isym[5] + sp.I*qq*Isym[3]*Isym[5] + sp.I*Isym[4]*Isym[5])
report("D  rotated 144-term sum - twelve-term form", Irot - twelve)
moment = {Isym[0]: cc*I3s + ss*I4s, Isym[4]: ss*I3s - cc*I4s, Isym[1]: ss*I3s, Isym[5]: ss*I4s}
def reduce_sc(e):
    e = sp.expand(e.subs(moment).subs(qq, cc + sp.I*ss))
    for k in (4, 3, 2):
        e = sp.expand(e.subs(cc**k, cc**(k - 2)*(1 - ss**2)))
    return e
report("D  reduced - 4 s^2 (I3^2+I4^2)", reduce_sc(Irot) - 4*ss**2*(I3s**2 + I4s**2))
for name, expr in [("I5^2+2 s I1 I4 - I4^2", Isym[4]**2 + 2*ss*Isym[0]*Isym[3] - Isym[3]**2),
                   ("I1 I6 + I2 I5", Isym[0]*Isym[5] + Isym[1]*Isym[4]),
                   ("s I1 I4 + I2 I5", ss*Isym[0]*Isym[3] + Isym[1]*Isym[4])]:
    report(f"D  {name} - s^2(I3^2+I4^2)", reduce_sc(expr) - ss**2*(I3s**2 + I4s**2))
# Euler: I3 = pi^2 F(1-tau)/(2s), I4 = pi^2 F(tau)/(2s)  ->  (4/pi^2) s^2 (I3^2+I4^2) = pi^2 (F(tau)^2 + F(1-tau)^2)
Ft, F1t = sp.symbols('Ft F1t')
report("D  (4/pi^2) s^2(I3^2+I4^2) - pi^2(F^2+F'^2)",
       sp.expand((4/pi**2*ss**2*((pi**2*F1t/(2*ss))**2 + (pi**2*Ft/(2*ss))**2))) - pi**2*(Ft**2 + F1t**2))

# ---------------------------------------------------------------- E. K2 Laurent extraction
tau = sp.symbols('tau')
uu, vv, sg, rr, Gc = sp.symbols('u v sigma varrho G')
lg2, zeta3 = sp.log(2), sp.zeta(3)
logQ2 = 8*lg2*tau - pi**2*tau**2 + 8*zeta3*tau**3 - pi**4*tau**4/6          # verified in check_series.wl
Q2s = sp.series(sp.exp(logQ2), tau, 0, 5).removeO()
qk = [sp.expand(Q2s.coeff(tau, k)) for k in range(5)]
print("   q_k =", qk, flush=True)
report("E  q_2", qk[2] - (32*lg2**2 - pi**2))
report("E  q_3", qk[3] - (sp.Rational(256, 3)*lg2**3 - 8*pi**2*lg2 + 8*zeta3))
report("E  q_4", qk[4] - (sp.Rational(512, 3)*lg2**4 - 32*pi**2*lg2**2 + 64*lg2*zeta3 + pi**4/3))
Jm = sp.expand(pi**2*(1 + uu*tau + vv*tau**2)**2 + Q2s*(1 + sg*tau**3 + rr*tau**4)**2/tau**2)
JG = sp.expand(sp.series(sp.exp(8*lg2*tau), tau, 0, 5).removeO()/tau**2 - 20*zeta3*tau - 48*lg2*zeta3*tau**2)  # verified in check_series.wl
diff = sp.expand(Jm - JG)
co = {k: sp.expand(diff.coeff(tau, k)) for k in (-2, -1, 0, 1, 2)}
report("E  [tau^-2]", co[-2]); report("E  [tau^-1]", co[-1]); report("E  [tau^0]", co[0])
report("E  [tau^1] - 2(sigma + pi^2 u - 4 pi^2 log2 + 14 zeta3)", co[1] - 2*(sg + pi**2*uu - 4*pi**2*lg2 + 14*zeta3))
report("E  [tau^2] structure", co[2] - (pi**2*(uu**2 + 2*vv) + 2*rr + 16*lg2*sg + qk[4] - sp.Rational(512, 3)*lg2**4 + 48*lg2*zeta3))
K2expr = sp.expand(co[2].subs(rr, pi**2*uu**2/2 - pi**4/6 - pi**2*vv)/4)          # eq:KproofTaylorCancellation
report("E  K2 = pi^2 u^2/2 + 4 log2 sigma - 8 pi^2 log^2 2 + 28 zeta3 log2",
       K2expr - (pi**2*uu**2/2 + 4*lg2*sg - 8*pi**2*lg2**2 + 28*zeta3*lg2))
lower = {uu: 4*lg2 - 8*Gc/pi, sg: 8*pi*Gc - 14*zeta3}                            # eq:KproofLowerCoefficients
report("E  K2 - (32 G^2 - 28 zeta3 log2)", K2expr.subs(lower) - (32*Gc**2 - 28*zeta3*lg2))
report("E  [tau^1] vanishes", co[1].subs(lower))
Au, Uu = 4*lg2, -14*zeta3
report("E  uniform form K2 = (pi^2/2)(u-A)^2 + AU/2 (sigma from order tau)",
       K2expr.subs(sg, pi**2*(Au - uu) - 14*zeta3) - (pi**2/2*(uu - Au)**2 + Au*Uu/2))
report("E  pi(A-u) = 8G", (pi*(Au - uu)).subs(lower) - 8*Gc)
print("ALL ZERO" if ok else "SOME CHECK FAILED", flush=True)
