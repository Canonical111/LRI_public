# Independent algebraic check that L2 (gs:Lseries at d=2) = (1/2) d/dx P(x) at x=1/2, where
#   P(x) = - Gamma(x)^-8 [u^3] { Phi(u;x)^2 sigma(u;x)^4 },
#   Phi(u;x) = sum_k h(k+u;x)^4,  h(s;x)=Gamma(s+x)/Gamma(s+1),
#   sigma(u;x) = pi u sin(pi(x+u)) / (sin(pi u) sin(pi x)).
# No two-mode theorem is used: every Taylor coefficient of Phi is a single sum sum_k c_k^4 * monomial,
# evaluated from the finder's 70-digit singles (confirm_dps70.json).
import json, sympy as sp, mpmath as mp
mp.mp.dps = 70
D = json.load(open('<PROJECT>/LRI_C5_d2_simplify/confirm_dps70.json'))
singles = {}
for k, v in D['singles'].items():
    t = eval(k)
    if t[0] == 'L':
        singles[tuple(t[1])] = mp.mpf(v)
X1, X2, X3, Y, Z1, Z2, Z3 = syms = sp.symbols('X1 X2 X3 Y Z1 Z2 Z3')
u, e = sp.symbols('u e')
# per-k: c_k(x)^4 = c_k^4 (1 + 4 e Y) + O(e^2);  x_j(k;x) = x_j(k) + e Z_j + O(e^2)
xs = [X1 + e*Z1, X2 + e*Z2, X3 + e*Z3]
logE = 4*sum(xs[j]*u**(j+1)/sp.factorial(j+1) for j in range(3))
perk = sp.expand(sp.series((1 + 4*e*Y)*sp.exp(logE), u, 0, 4).removeO())
perk = sp.expand(perk).subs(e**2, 0)
def S(poly):
    poly = sp.expand(poly); tot = mp.mpf(0)
    for mono, coef in sp.Poly(poly, *syms).terms():
        tot += mp.mpf(sp.Rational(coef).p)/sp.Rational(coef).q*singles[tuple(mono)]
    return tot
Phi = {}
for i in range(4):
    ci = sp.expand(perk.coeff(u, i))
    Phi[(i, 0)] = S(ci.subs(e, 0)); Phi[(i, 1)] = S(ci.coeff(e, 1))
# Phi(u;x)/Gamma(x)^4 = sum_i (Phi[i,0] + e Phi[i,1]) u^i ; then P(x) = -Gamma(x)^-8 Gamma(x)^8 [u^3]{(.)^2 sigma^4}
p0 = [Phi[(i, 0)] for i in range(4)]; p1 = [Phi[(i, 1)] for i in range(4)]
# sigma^4 jets: sigma = pi u sin(pi(x+u))/(sin(pi u) sin(pi x)), x = 1/2 + e
x = sp.Rational(1, 2) + e
sig4 = sp.series(sp.series((sp.pi*u*sp.sin(sp.pi*(x+u))/(sp.sin(sp.pi*u)*sp.sin(sp.pi*x)))**4, u, 0, 4).removeO(), e, 0, 2).removeO()
sj = [[mp.mpf(sp.N(sp.expand(sig4).coeff(u, i).coeff(e, k) if k else sp.expand(sig4).coeff(u, i).subs(e, 0), 80)) for k in range(2)] for i in range(4)]
def coef3(eorder):
    # [u^3] of (sum (p0+e p1) u^i)^2 * (sum (s0 + e s1) u^i), coefficient of e^eorder
    tot = mp.mpf(0)
    for i in range(4):
        for j in range(4):
            k = 3 - i - j
            if k < 0: continue
            if eorder == 0:
                tot += p0[i]*p0[j]*sj[k][0]
            else:
                tot += p1[i]*p0[j]*sj[k][0] + p0[i]*p1[j]*sj[k][0] + p0[i]*p0[j]*sj[k][1]
    return tot
P0 = -coef3(0); P1 = -coef3(1)
print('P(1/2) from singles      :', mp.nstr(P0, 30))
a = mp.mpf(D['a']); b = mp.mpf(D['b'])
print('8 pi^3 a b               :', mp.nstr(8*mp.pi**3*a*b, 30))
L2 = mp.mpf(D['checks']['L2'])
print('(1/2) P\'(1/2) - L2       :', mp.nstr(P1/2 - L2, 5))
