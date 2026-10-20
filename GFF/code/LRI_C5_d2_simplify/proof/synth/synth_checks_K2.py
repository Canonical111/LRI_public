# Synthesizer checks of the displayed K2 Laurent data in proof_d2.tex (exact sympy, fast version:
# log-Gamma Taylor series from exact polygamma values, truncated polynomial algebra).
import sympy as sp
t = sp.symbols('tau'); l2 = sp.log(2); g = sp.EulerGamma; z = sp.zeta
G = sp.Catalan; z3 = z(3)
N = 7  # keep tau^0..tau^6
def psik(k, c):            # psi_k(c) for c in {1, 1/2}
    if k == 0:
        return -g if c == 1 else -g - 2*l2
    v1 = (-1)**(k+1)*sp.factorial(k)*z(k+1)
    return v1 if c == 1 else (2**(k+1)-1)*v1
def lgam(c, x):            # log Gamma(c+x) - log Gamma(c), x a polynomial in tau without constant term
    return sum(psik(k-1, c)*x**k/sp.factorial(k) for k in range(1, N))
def trunc(e, n=N):
    e = sp.expand(e); return sum(e.coeff(t, k)*t**k for k in range(n))
def texp(e):               # exp of a polynomial without constant term, truncated
    e = trunc(e); r = 1; term = 1
    for k in range(1, N):
        term = trunc(term*e)/k; r += term
    return trunc(r)
h = sp.Rational(1, 2)
# L = log(pi kappa), kappa = Gamma(1+t)/(Gamma(1-t) Gamma(1/2+t)^2);  Gamma(1/2)^2 = pi
L = trunc(lgam(1, t) - lgam(1, -t) - 2*lgam(h, t))
# M = log(t C X), t C = Gamma(1+t)/Gamma(1-t), X = [Gamma(1/2-t/2)/Gamma(1/2+t/2)]^2
M = trunc(lgam(1, t) - lgam(1, -t) + 2*lgam(h, -t/2) - 2*lgam(h, t/2))
Lt = 4*l2*t - sp.pi**2/2*t**2 + 4*z3*t**3 - sp.pi**4/12*t**4
Mt = 4*l2*t + z3/2*t**3
print('L - displayed (through tau^4):', sp.simplify(trunc(L - Lt, 5)), ' | M - displayed (through tau^4):', sp.simplify(trunc(M - Mt, 5)))
u, v, s, w = sp.symbols('u v sigma w')
FF = 1 + u*t + v*t**2; GG = 1 + s*t**3 + w*t**4
E2L = texp(2*L); E2M = texp(2*M)
num = trunc(E2L*GG**2 - E2M)              # C*D = pi^2 FF^2 + num/t^2
CD = {k: sp.expand(sp.expand(sp.pi**2*FF**2).coeff(t, k) + num.coeff(t, k+2)) for k in range(-2, 3)}
for k in range(-2, 1): print(f'[tau^{k}] C*D =', sp.simplify(CD[k]))
print('[tau^1] - (2pi^2 u + 2 sigma + 7 z3 - 8 pi^2 log2):', sp.simplify(CD[1] - (2*sp.pi**2*u + 2*s + 7*z3 - 8*sp.pi**2*l2)))
disp2 = 2*(w + sp.pi**2*v) + sp.pi**2*u**2 + sp.pi**4/3 + 56*z3*l2 - 32*sp.pi**2*l2**2 + 16*s*l2
print('[tau^2] - displayed:', sp.simplify(CD[2] - disp2))
print('[tau^4] e^{2L} =', sp.simplify(E2L.coeff(t,4)), ' | [tau^4] e^{2M} =', sp.simplify(E2M.coeff(t,4)))
# J^Gamma (gs:Kdefinition at d=2, t = 2 tau) via exact Gamma expansions.
# B2(1, 2-2tau) = Gamma(tau) Gamma(1/2-tau) / (Gamma(1-tau) Gamma(1/2+tau)) = (1/tau) exp(Lb)
Lb = trunc(lgam(1, t) - lgam(1, -t) + lgam(h, -t) - lgam(h, t))
# B2(1+4tau, 2-2tau) = Gamma(1/2-2tau) Gamma(tau) Gamma(1/2+tau) / (Gamma(1/2+2tau) Gamma(1-tau) Gamma(1/2-tau)) = (1/tau) exp(Lc)
Lc = trunc(lgam(h, -2*t) + lgam(1, t) + lgam(h, t) - lgam(h, 2*t) - lgam(1, -t) - lgam(h, -t))
eb, ec = texp(Lb), texp(Lc)
# J^Gamma = eb^2/tau^2 + (1/tau)(eb - ec)/tau ;  C^2 X^2 = E2M/tau^2
JGm = trunc(eb**2 + (eb - ec) - E2M)     # (J^Gamma - C^2 X^2) * tau^2
for k in range(0, 4): print(f'[tau^{k-2}](J^Gamma - C^2X^2) =', sp.simplify(JGm.coeff(t, k)))
cst = sp.simplify(JGm.coeff(t, 4)/4)
print('(1/4)[tau^2](J^Gamma - C^2 X^2) =', cst, ' ; + 14 zeta3 log2 =', sp.simplify(cst + 14*z3*l2))
# J = pi^2[FF(tau)^2 + FF(1-tau)^2] = pi^2 FF^2 + E2L GG^2/tau^2
dJ = {k: sp.expand(sp.expand(sp.pi**2*FF**2).coeff(t, k) + trunc(E2L*GG**2 - eb**2 - (eb - ec)).coeff(t, k+2)) for k in range(-2, 3)}
for k in range(-2, 2): print(f'[tau^{k}](J - J^Gamma) =', sp.simplify(dJ[k]))
K2def = sp.expand(dJ[2]/4).subs(w, sp.pi**2*u**2/2 - sp.pi**4/6 - sp.pi**2*v).subs({u: 4*l2 - 8*G/sp.pi, s: 8*sp.pi*G - 14*z3})
print('K2 via gs:Kdefinition, (1/4)[tau^2](J - J^Gamma) =', sp.simplify(sp.expand(K2def)))
