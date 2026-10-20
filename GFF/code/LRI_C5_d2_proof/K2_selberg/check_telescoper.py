"""Exact check of the termwise telescoping identity (note eq:KproofTelescoper) behind the recurrence
t^2 F(t+1) - (2t^2-2t+3/4) F(t) + (t-1)^2 F(t-1) = 0, with a_n(t) = (1/2)_n^2 (t)_n / n!^3."""
import sympy as sp
n, t = sp.symbols('n t')
def a(n_, t_):
    return sp.rf(sp.Rational(1, 2), n_)**2*sp.rf(t_, n_)/sp.factorial(n_)**3
lhs = t**2*a(n, t+1) - (2*t**2-2*t+sp.Rational(3, 4))*a(n, t) + (t-1)**2*a(n, t-1)
rhs = (n+1)**3*a(n+1, t)/(n+t) - n**3*a(n, t)/(n+t-1)
ratio = sp.simplify(sp.gammasimp(sp.combsimp((lhs - rhs)/a(n, t))))
print('(lhs - rhs)/a_n(t) =', ratio)
# spot check with explicit integers
for nn in range(0, 6):
    for tt in [sp.Rational(1, 3), sp.Rational(-2, 7)]:
        assert sp.simplify(lhs.subs({n: nn, t: tt}) - rhs.subs({n: nn, t: tt})) == 0
print('spot checks n = 0..5 at t = 1/3, -2/7: OK')
