# Exact symbolic checks (sympy, explicit truncated power series -- fast) for the K2-parseval proof.
#  (A) tau-expansion of Re(R_tau - S_tau) on the Mellin line (note gs:RS, gs:Kweights): 0 + 0 tau + E2 tau^2 + X3 tau^3
#  (B) Laurent extraction: K2 = -AU/4 + (1/4)[tau^2]{ J(tau) - C(tau)^2 X(tau)^2 },  J = pi^2 (FF(tau)^2 + FF(1-tau)^2),
#      and the alternative (1/4)[tau^2]{ J(tau) - J^Gamma_{2tau} } (note gs:Kdefinition); both must give 32G^2-28 z3 log2.
import sympy as sp
N = 6          # keep powers tau^0 .. tau^(N-1) in regular series

def mul(a, b):
    out = [0]*N
    for i in range(N):
        if a[i] == 0: continue
        for k in range(N-i):
            out[i+k] += a[i]*b[k]
    return [sp.expand(x) for x in out]
def exp_ser(l):          # exp of a series with l[0] = 0
    assert l[0] == 0
    out = [sp.Integer(1)] + [0]*(N-1); term = out[:]
    for n in range(1, N):
        term = [sp.expand(x/n) for x in mul(term, l)]
        out = [sp.expand(x+y) for x, y in zip(out, term)]
    return out
def add(*ss): return [sp.expand(sum(x)) for x in zip(*ss)]
def scal(c, a): return [sp.expand(c*x) for x in a]

print('(A) expansion of Re(R_tau - S_tau)', flush=True)
al = sp.symbols('al0:4'); alb = sp.symbols('alb0:4'); be = sp.symbols('be0:4'); beb = sp.symbols('beb0:4')
def logR(al, alb, be, beb):
    l = [0]*N
    for k in range(1, N):
        l[k] = ((-1)**k*beb[k-1] - al[k-1])/sp.factorial(k) if k <= 4 else 0
    return l
lS = [0]*N
for k in range(1, N):
    lS[k] = 2*((-sp.Rational(1, 4))**k*(al[k-1]+alb[k-1]) - sp.Rational(1, 4)**k*(be[k-1]+beb[k-1]))/sp.factorial(k) if k <= 4 else 0
Rs = add(scal(sp.Rational(1, 2), exp_ser(logR(al, alb, be, beb))), scal(sp.Rational(1, 2), exp_ser(logR(alb, al, beb, be))))
D = add(Rs, scal(-1, exp_ser(lS)))
I = sp.I
p = (al[0]+alb[0]+be[0]+beb[0])/2
hh = (al[0]-alb[0]-be[0]+beb[0])/(2*I)
j = (al[1]+alb[1]-be[1]-beb[1])/2
kk = (al[1]-alb[1]+be[1]-beb[1])/(2*I)
r = (al[2]+alb[2]+be[2]+beb[2])/2
E2 = -hh**2/2 - sp.Rational(5, 8)*j
X3 = -p*E2 - hh*kk/2 - sp.Rational(5, 32)*r
for n, target in [(0, 0), (1, 0), (2, E2), (3, X3)]:
    print('  [tau^%d] residual:' % n, sp.expand(D[n] - target), flush=True)

print('(B) Laurent extraction', flush=True)
z = {k: sp.zeta(k) for k in range(2, 8)}
gE = sp.EulerGamma; L2 = sp.log(2); Cat = sp.Catalan; pi = sp.pi
def psi(k, c):            # polygamma psi_k(c) for c in {1, 1/2}
    if k == 0:
        return -gE if c == 1 else -gE - 2*L2
    val = (-1)**(k+1)*sp.factorial(k)*sp.zeta(k+1)
    return val if c == 1 else val*(2**(k+1)-1)
def lgam(c, x):           # series of log Gamma(c + x tau) - log Gamma(c), x rational
    return [0] + [sp.expand(psi(k-1, c)*x**k/sp.factorial(k)) for k in range(1, N)]
def gam(c, x, power=1):   # series of [Gamma(c+x tau)/Gamma(c)]^power
    return exp_ser(scal(power, lgam(c, x)))
h = sp.Rational(1, 2)
u, v, f3, f4, sig, w, g5 = sp.symbols('u v f3 f4 sigma w g5')
FF = [1, u, v, f3, f4, 0]
GG = [1, 0, 0, sig, w, g5]
# kappa(tau) = Gamma(1+tau)/(Gamma(1-tau) Gamma(1/2+tau)^2) = (1/pi) * series ;  FF(1-tau) = kappa GG / tau
kap = scal(1/pi, mul(mul(gam(1, 1), gam(1, -1, -1)), gam(h, 1, -2)))
J_reg = scal(pi**2, mul(FF, FF))                  # pi^2 FF^2 (regular)
J_sing = scal(pi**2, mul(mul(kap, kap), mul(GG, GG)))   # times tau^-2
# C(tau) X(tau) = Gamma(tau) G(1/2-tau/2)^2/(G(1-tau) G(1/2+tau/2)^2) = (1/tau) * series
CX = mul(mul(gam(1, 1), gam(1, -1, -1)), mul(gam(h, -h, 2), gam(h, h, -2)))
CX2 = mul(CX, CX)                                  # times tau^-2
# [tau^n] of J - C^2X^2 :  J_reg[n] + J_sing[n+2] - CX2[n+2]
def cJmCX(n): return sp.expand((J_reg[n] if n >= 0 else 0) + J_sing[n+2] - CX2[n+2])
# J^Gamma_{2 tau} = B(1,2-t)^2 + (2/t)[B(1,2-t) - B(1+2t,2-t)], t = 2 tau, at d=2:
#   B(1,2-t)      = G(tau) G(1/2-tau)/(G(1-tau) G(1/2+tau)) = (1/tau) S1
#   B(1+2t,2-t)   = G(1/2-2tau) G(tau) G(1/2+tau)/(G(1/2+2tau) G(1-tau) G(1/2-tau)) = (1/tau) S2
G11 = mul(gam(1, 1), gam(1, -1, -1))                 # Gamma(1+tau)/Gamma(1-tau)
S1 = mul(G11, mul(gam(h, -1), gam(h, 1, -1)))
S2 = mul(mul(G11, mul(gam(h, -2), gam(h, 2, -1))), mul(gam(h, 1), gam(h, -1, -1)))
# J^G = tau^-2 S1^2 + (1/tau)(1/tau)(S1 - S2) = tau^-2 (S1^2 + S1 - S2)
JGs = add(mul(S1, S1), S1, scal(-1, S2))
def cJmJG(n): return sp.expand((J_reg[n] if n >= 0 else 0) + J_sing[n+2] - JGs[n+2])
for n in (-2, -1, 0, 1):
    print('  [tau^%d]  J - C^2X^2 :' % n, sp.simplify(cJmCX(n)), '   J - J^Gamma :', sp.simplify(cJmJG(n)), flush=True)
rules = {w: pi**2*u**2/2 - pi**4/6 - pi**2*v}      # note eq:KproofTaylorCancellation (the note's 'tau' coefficient = w here)
vals = {u: 4*L2 - 8*Cat/pi, sig: 8*pi*Cat - 14*sp.zeta(3)}   # note eq:KproofLowerCoefficients
A = 4*L2; U = -14*sp.zeta(3)
K2a = sp.simplify(sp.expand((-A*U/4 + cJmCX(2)/4).subs(rules).subs(vals)))
K2b = sp.simplify(sp.expand((cJmJG(2)/4).subs(rules).subs(vals)))
target = 32*Cat**2 - 28*sp.zeta(3)*L2
print('  K2 (spectral subtraction, -AU/4 included) =', K2a, '  residual:', sp.simplify(K2a-target))
print('  K2 (definition, J^Gamma subtraction)      =', K2b, '  residual:', sp.simplify(K2b-target))
print('  [tau^2] C^2X^2 / 4 =', sp.simplify(CX2[4]/4), ' ;  [tau^2] J^Gamma / 4 =', sp.simplify(JGs[4]/4))
print('  ([tau^2]J^Gamma - [tau^2]C^2X^2)/4 =', sp.simplify((JGs[4]-CX2[4])/4), '  (expect AU/4 = -14 zeta3 log2)')
print('  before substitution, (1/4)[tau^2](J - J^G) =', sp.expand(cJmJG(2)/4))
