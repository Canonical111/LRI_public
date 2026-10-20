# Exact (symbolic) checks for the collapse of L_2 (gs:Lseries at d=2) onto the two-mode coefficients.
#
# Part 1 (per-lattice-point identity).  For fixed m,n >= 0 put r_x(s)=Gamma(s+x)/Gamma(s+1), N(x)=Gamma(1-x)/Gamma(x),
#   E_{mn}(x) := -N(x)^4 Res_{u=0} [ sin(pi(x+u))^4/sin(pi u)^4 * r_x(m+u)^4 r_x(n+u)^4 ].
# Claim: (1/2) dE_{mn}/dx at x=1/2 equals the gs:Lseries summand  -c_m^4 c_n^4 (4 mu_1 F_4 + F_{4,1})  at q=1/2,
# and E_{mn}(1/2) equals the gs:QPseries summand  -c_m^4 c_n^4 F_4.  Verified as a polynomial identity in the jet
# symbols  X_j^{(m)}(x) = psi_{j-1}(m+x) - psi_{j-1}(m+1)  (j=1,2,3),  Z_j^{(m)} = dX_j^{(m)}/dx = psi_j(m+x),
# Y^{(m)} = d/dx log r_x(m) = psi(m+x)  (same for n), i.e. for all m,n simultaneously, using
#   log r_x(m+u) = log r_x(m) + sum_j X_j^{(m)}(x) u^j/j!   (only j<=3 matter for a 4th-order pole).
#
# Part 2 (collapse).  Summing Part 1 over the (m,n) square and using the two-mode theorem
#   sin^4(pi(x+u)) f(u;x) = Omega(u;x) - sin^4(pi u) g(u;x),   Omega = A(x) + B(x) cos(2 pi u + pi x),
# gives  L_2 = (1/2) d/dx { -N(x)^4 Res_{u=0} [Omega(u;x)^2 / (sin^4(pi(x+u)) sin^4(pi u))] }  at x=1/2.
import sympy as sp

u, x = sp.symbols('u x')
pi = sp.pi
half = sp.Rational(1, 2)

def res4(expr):
    """Res_{u=0} of expr, which has at most a 4th-order pole at u=0: Taylor coefficient of u^3 in u^4*expr."""
    t = sp.series(sp.simplify(expr*u**4), u, 0, 4).removeO()
    return sp.expand(t).coeff(u, 3)

# ---------------- Part 1 ----------------
X = {(s, j): sp.Symbol(f'X{j}{s}') for s in 'mn' for j in (1, 2, 3)}
Z = {(s, j): sp.Symbol(f'Z{j}{s}') for s in 'mn' for j in (1, 2, 3)}
Y = {s: sp.Symbol(f'Y{s}') for s in 'mn'}
psih, W = sp.symbols('psih W')     # psih = psi(1/2);  W = c_m^4 c_n^4, so r_{1/2}(m)^4 r_{1/2}(n)^4 = pi^4 W
jet = sum(X[(s, j)]*u**j/sp.factorial(j) for s in 'mn' for j in (1, 2, 3))
res = res4((sp.sin(pi*(x + u))/sp.sin(pi*u))**4*sp.exp(4*jet))     # depends on x and the X symbols
# E = -N^4 * r_x(m)^4 r_x(n)^4 * res ;  d/dx log(N^4 r^4 r^4) = -4 psi(1-x) - 4 psi(x) + 4 Ym + 4 Yn
dres = sp.diff(res, x) + sum(sp.diff(res, X[(s, j)])*Z[(s, j)] for s in 'mn' for j in (1, 2, 3))
dlogpref = -8*psih + 4*Y['m'] + 4*Y['n']           # value at x=1/2
E_half = sp.expand(-pi**4*W*res.subs(x, half))
dE_half = sp.expand(-pi**4*W*(dlogpref*res + dres).subs(x, half))
# note's polynomials at q=1/2 (gs:lambda, gs:etaTheta, gs:Fpolys)
k2 = 2*(sp.polygamma(1, 1) - sp.polygamma(1, half))
p1 = sp.polygamma(1, half); p3 = sp.polygamma(3, half)
l1 = X[('m', 1)] + X[('n', 1)]; l2 = X[('m', 2)] + X[('n', 2)] + k2; l3 = X[('m', 3)] + X[('n', 3)]
mu1 = (Y['m'] - psih + Y['n'] - psih)/2
e1 = (Z[('m', 1)] + Z[('n', 1)])/2 - p1; e2 = (Z[('m', 2)] + Z[('n', 2)])/2; e3 = (Z[('m', 3)] + Z[('n', 3)])/2 - p3
F4 = sp.Rational(32, 3)*l1**3 + 8*l1*l2 + sp.Rational(2, 3)*l3
F41 = 32*l1**2*e1 + 8*e1*l2 + 8*l1*e2 + sp.Rational(2, 3)*e3
print('Part 1: E(1/2)       - (-W F4)                   =', sp.simplify(E_half - sp.expand(-W*F4)))
print('Part 1: (1/2)E\'(1/2) - (-W(4 mu1 F4 + F41))      =', sp.simplify(dE_half/2 - sp.expand(-W*(4*mu1*F4 + F41))))

# ---------------- Part 2 ----------------
A, B, Ap, Bp = sp.symbols('A B Ap Bp')     # A(1/2), B(1/2), A'(1/2), B'(1/2)
Ax = A + Ap*(x - half); Bx = B + Bp*(x - half)   # first-order jets suffice for d/dx at x=1/2
Om = Ax + Bx*sp.cos(2*pi*u + pi*x)
R = res4(Om**2/(sp.sin(pi*(x + u))**4*sp.sin(pi*u)**4))
N4 = (sp.gamma(1 - x)/sp.gamma(x))**4
P4_half = sp.simplify((-N4*R).subs(x, half))
L2_half = sp.simplify(sp.expand_func((sp.Rational(1, 2)*sp.diff(-N4*R, x)).subs(x, half)))
L2_half = sp.expand(L2_half.subs(sp.polygamma(0, half), psih).subs(-sp.EulerGamma - 2*sp.log(2), psih))
print('P_4(2) = -Res[...] at x=1/2                       =', P4_half)
print('L_2 in A,B,A\',B\'                                 =', sp.collect(L2_half, [Ap, Bp, psih]))
a, b, Sy, Sxy = sp.symbols('a b Sy Sxy')
g = sp.EulerGamma; lg2 = sp.log(2)
psi_half = -g - 2*lg2
# A'(1/2), B'(1/2) <-> single sums (t-jets of Omega at t=0):
#   A'(1/2) = pi B + 4 pi^2 (Sy + psi(1/2) a),   -2 pi B'(1/2) = -4 pi^4 a + 4 pi^2 Sxy - 8 pi^3 psi(1/2) b
L2_sums = L2_half.subs({Ap: pi*B + 4*pi**2*(Sy + psih*a), Bp: (4*pi**4*a - 4*pi**2*Sxy + 8*pi**3*psih*b)/(2*pi)})
L2_sums = sp.expand(L2_sums.subs({A: pi**2*a, B: pi**2*b}).subs(psih, psi_half))
structural = 2*pi**4*a**2 - 4*pi**4*b**2 + 16*pi**3*b*Sy - 8*pi**2*a*Sxy
finder = 3*pi**4*a**2 - 2*pi**4*b**2 + 8*pi**3*b*Sy - 12*pi**2*a*Sxy
Delta = pi**4*a**2 + 2*pi**4*b**2 - 8*pi**3*b*Sy - 4*pi**2*a*Sxy
print('L_2 in a,b,Sy,Sxy (no lemmas used)               =', sp.collect(L2_sums, [Sy, Sxy]))
print('  minus structural form 2pi^4a^2-4pi^4b^2+16pi^3bSy-8pi^2aSxy =', sp.simplify(L2_sums - structural))
print('finder PSLQ form - structural form - Delta       =', sp.simplify(finder - structural - Delta))
lem = {Sy: (pi*b - 2*a*lg2)/4, Sxy: pi**2*a/4 + pi*b*lg2}
print('Delta with (L-a),(L-b)                           =', sp.simplify(Delta.subs(lem)))
print('structural form with (L-a),(L-b)                 =', sp.factor(sp.expand(structural.subs(lem))), ' [= -2 log2 * 8 pi^3 a b]')
L2_direct = sp.expand(L2_half.subs({Ap: 2*pi*B - (10*lg2 + 4*g)*A, Bp: sp.Rational(3, 2)*pi*A - (10*lg2 + 4*g)*B}).subs(psih, psi_half))
print('L_2 from the A\',B\' relations (eq. AdotBdot)      =', sp.factor(L2_direct), '   vs -2 log2 * P_4(2) =', sp.factor(-2*lg2*P4_half))
