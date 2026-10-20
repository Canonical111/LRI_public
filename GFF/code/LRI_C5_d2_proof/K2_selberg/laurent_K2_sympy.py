"""Exact Laurent extraction of K_2 with no zero-testing: all Gamma factors are expanded through the standard
series (DLMF 5.7.3, 5.4.13, 5.15.3)
   log Gamma(1+x)   = -gamma x + sum_{k>=2} (-1)^k zeta(k) x^k / k,
   log Gamma(1/2+x) = log sqrt(pi) + psi(1/2) x + sum_{k>=2} psi^{(k-1)}(1/2) x^k / k!,
   psi(1/2) = -gamma - 2 log 2,  psi^{(k-1)}(1/2) = (-1)^k (k-1)! (2^k - 1) zeta(k)  (k >= 2),
so the computation is polynomial algebra in gamma, log 2, pi, zeta(3), zeta(5) (gamma cancels identically).
Inputs (proved in the note's d=1 K proof, reproduced in PROOF.md):
   F(x) = 1 + u x + v x^2 + O(x^3),  G(x) = 1 + sig x^3 + w x^4 + O(x^5),
   w + pi^2 v = pi^2 u^2/2 - pi^4/6,   u = 4 log2 - 8 Cat/pi,   sig = 8 pi Cat - 14 zeta(3)."""
import sympy as sp
x, g, l, z3, z5, u, v, w, sig, f3, g5, Cat = sp.symbols('x gamma_E ell zeta3 zeta5 u v w sigma f3 g5 Cat')
pi = sp.pi
N = 6
zeta = {2: pi**2/6, 3: z3, 4: pi**4/90, 5: z5, 6: pi**6/945}
def lnG1(y):   # log Gamma(1+y)
    return -g*y + sum((-1)**k*zeta[k]*y**k/k for k in range(2, N+1))
def lnGh(y):   # log Gamma(1/2+y) - log sqrt(pi)
    return (-g - 2*l)*y + sum((-1)**k*sp.factorial(k-1)*(2**k-1)*zeta[k]*y**k/sp.factorial(k) for k in range(2, N+1))
def ser(expr, order):
    return sp.series(expr, x, 0, order).removeO()
def expser(lg, order):   # exp of a polynomial with zero constant term, truncated
    lg = sp.expand(lg)
    out, term = 1, 1
    for k in range(1, order+1):
        term = sp.expand(term*lg/k)
        term = sum(term.coeff(x, j)*x**j for j in range(0, order+1))
        out += term
    return sp.expand(sum(sp.expand(out).coeff(x, j)*x**j for j in range(0, order+1)))
O = 5
# h(tau) = pi Gamma(1+tau)/(Gamma(1-tau) Gamma(1/2+tau)^2)
log_h = lnG1(x) - lnG1(-x) - 2*lnGh(x)
h2 = expser(2*log_h, O)
# tau*B(1,2-t) = Gamma(1+tau)Gamma(1/2-tau)/(Gamma(1-tau)Gamma(1/2+tau))
tB = expser(lnG1(x) - lnG1(-x) + lnGh(-x) - lnGh(x), O)
# tau*B(1+2t,2-t) = Gamma(1+tau)Gamma(1/2-2tau)Gamma(1/2+tau)/(Gamma(1-tau)Gamma(1/2+2tau)Gamma(1/2-tau))
tBt = expser(lnG1(x) - lnG1(-x) + lnGh(-2*x) - lnGh(2*x) + lnGh(x) - lnGh(-x), O)
print('log h   =', sp.expand(sum(sp.expand(log_h).coeff(x, j)*x**j for j in range(1, 5))))
print('log tB  =', sp.expand(sum(sp.expand(lnG1(x) - lnG1(-x) + lnGh(-x) - lnGh(x)).coeff(x, j)*x**j for j in range(1, 5))))
print('log tBt =', sp.expand(sum(sp.expand(lnG1(x) - lnG1(-x) + lnGh(-2*x) - lnGh(2*x) + lnGh(x) - lnGh(-x)).coeff(x, j)*x**j for j in range(1, 5))))
# tau^2 J^Gamma = (tau B)^2 + (tau B - tau Bt)   [since (1/tau)(B - Bt) = (tau B - tau Bt)/tau^2];   tau^2 J = pi^2 tau^2 F^2 + h^2 G^2
F = 1 + u*x + v*x**2 + f3*x**3
G = 1 + sig*x**3 + w*x**4 + g5*x**5
t2JG = sp.expand(tB**2 + (tB - tBt))
t2J = sp.expand(pi**2*x**2*F**2 + h2*G**2)
D = sp.expand(t2J - t2JG)
coef = {k-2: sp.factor(sp.expand(D.coeff(x, k))) for k in range(0, 5)}
for k in range(-2, 3):
    print('[tau^%d](J - J^Gamma) =' % k, coef[k])
print('tau^2 J^Gamma (through tau^4) =', sp.expand(sum(t2JG.coeff(x, j)*x**j for j in range(0, 5))))
rule = {w: pi**2*u**2/2 - pi**4/6 - pi**2*v}
vals = {u: 4*l - 8*Cat/pi, sig: 8*pi*Cat - 14*z3}
c1 = sp.simplify(sp.expand(coef[1].subs(rule).subs(vals)))
K2_uv = sp.expand(coef[2].subs(rule)/4)
K2 = sp.simplify(sp.expand(K2_uv.subs(vals)))
print('[tau^1] after u, sigma:', c1)
print('K2 in terms of u, sigma (after bilinear rule):', K2_uv)
print('K2 =', K2, '   K2 - (32 Cat^2 - 28 zeta3 log2) =', sp.simplify(K2 - (32*Cat**2 - 28*z3*l)))
