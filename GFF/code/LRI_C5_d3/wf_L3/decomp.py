"""Exact (symbolic) decomposition of L3 = dW_4(3;b)/db = -(1/2) dW/dgamma at gamma=3/4 in terms of the
normalized pieces X = (A,B,H0,Hh,V0q,V1q) and their gamma-derivatives X'.  (session L3)
W(gamma) = sum_k w_k(sigma) C_k,  w_k = -B_{4,k}(sigma)/(pi sin pi sigma)^4,  sigma = 3/2-gamma,
C1 = 2AB, C2 = (E_q - E_a)/(1+cos 4 pi alpha), C0 = E_q - C2,
E_a = s(alpha) H0 + 2AB sin(2 pi alpha),  E_q = 2 s(1/4) Hh + 4 sin^4(pi(alpha-1/4)) cos^4(pi(alpha+1/4)) V0q V1q + 2AB,
s(u) = sin^4(2 pi (u+alpha))/16, alpha = (1-gamma)/2."""
import sympy as sp
g = sp.symbols('gamma', real=True)
A, B, H0, Hh, V0q, V1q = sp.symbols('A B H0 Hh V0q V1q')
sig = sp.Rational(3, 2) - g
al = (1 - g) / 2
pi = sp.pi
c = sp.cot(pi * sig)
r = 4
u1 = -r * pi * c
u2 = r * pi ** 2 * (c ** 2 + sp.Rational(4, 3))
u3 = -2 * r * pi ** 3 * c * (1 + c ** 2)
E3 = lambda x1, x2, x3: (x1 ** 3 + 3 * x1 * x2 + x3) / 6
Bk = [sp.simplify(sp.re(sp.expand(sp.exp(sp.I * pi * k * sig) * E3(u1 + 2 * pi * sp.I * k, u2, u3), complex=True)))
      for k in range(4)]
w = [-Bk[k] / (pi * sp.sin(pi * sig)) ** 4 for k in range(4)]
s = lambda u: sp.sin(2 * pi * (u + al)) ** 4 / 16
Ea = s(al) * H0 + 2 * A * B * sp.sin(2 * pi * al)
Eq = 2 * s(sp.Rational(1, 4)) * Hh + 4 * sp.sin(pi * (al - sp.Rational(1, 4))) ** 4 * sp.cos(pi * (al + sp.Rational(1, 4))) ** 4 * V0q * V1q + 2 * A * B
C2 = (Eq - Ea) / (1 + sp.cos(4 * pi * al))
C0 = Eq - C2
C1 = 2 * A * B
W = w[0] * C0 + w[1] * C1 + w[2] * C2
g0 = sp.Rational(3, 4)
X = [A, B, H0, Hh, V0q, V1q]
W0 = sp.nsimplify(sp.simplify(W.subs(g, g0)))
expl = sp.simplify(sp.diff(W, g).subs(g, g0))
part = [sp.simplify(sp.diff(W, x).subs(g, g0)) for x in X]
if __name__ == '__main__':
    print('B_{4,k}(3/4)/pi^3 =', [sp.nsimplify(sp.simplify(b.subs(g, g0) / pi ** 3)) for b in Bk])
    print('W(3/4) =', sp.expand(W0))
    print('dW/dgamma explicit =', sp.expand(sp.simplify(expl)))
    for x, p in zip(X, part):
        print('dW/d' + str(x), '=', sp.expand(sp.simplify(p)))
    L3 = sp.expand(-(sp.expand(expl) + sum(p * sp.Symbol(str(x) + 'p') for x, p in zip(X, part))) / 2)
    print('\nL3 =', L3)
