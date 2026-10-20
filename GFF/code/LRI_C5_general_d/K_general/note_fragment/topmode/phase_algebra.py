#!/usr/bin/env python3
"""Symbolic check of the phase bookkeeping in the top-mode argument (tag topmode).

General kernel on the lattice s = a_l + n + t, z = n + t:
   F_L(l+sigma+z) = prod_i Gamma(l+sigma+alpha_i+z)/Gamma(l+sigma+alpha_i+g_i+z)
   F_R(z)         = prod_i Gamma(beta_i-z)/Gamma(beta_i+h_i-z)
Upper half plane (coefficient s_1): Laplace variables v_i (left), v'_i (right), constraint sum v + sum v' = 2 pi.
For 0<v<2pi:  log(1-e^{iv}) = l(v) + i(v-pi)/2,  log(1-e^{-iv}) = l(v) - i(v-pi)/2,  l(v) = log(2 sin(v/2)).
The 'phase' Theta collects every i*(linear in v) term of the integrand
   e^{i sigma V} (1+e^{iV}) (1-e^{iV})^{1-d} prod_i e^{i alpha_i v_i}(1-e^{i v_i})^{g_i-1} prod_j e^{-i beta_j v'_j}(1-e^{-i v'_j})^{h_j-1},
with 1+e^{iV} = 2cos(V/2) e^{iV/2}.  Lower half plane (s'_1): every i -> -i.
Checks:
 (1) general: Theta - swap(Theta) = sum_i (sigma+alpha_i+beta_i+g_i-d/2)(v_i-v'_i) when h_i = g_i (on the constraint surface);
 (2) wheel (alpha=beta=0, g_i=g, sigma+g=d/2): Theta = pi(sigma+1/2)  (foundation Thm 6, Step 5);
 (3) R kernel (sigma=q, d=4q, left (0,q),(0,q),(0,tau), right (0,q),(0,q),(q-tau,tau)):
     Theta = pi(q+1/2) + (tau-q)(v3+v3')/2  -- not constant, but swap-symmetric;
 (4) lower half plane: Theta' = -Theta for the R kernel.
"""
import sympy as sp

pi = sp.pi


def theta(sigma, d, left, right, v, vp, sign=+1):
    """sign=+1: upper half plane; sign=-1: lower (all i -> -i)."""
    V = sum(v)
    th = sigma * V + V / 2 + (1 - d) * (V - pi) / 2
    for (al, g), x in zip(left, v):
        th += al * x + (g - 1) * (x - pi) / 2
    for (be, h), x in zip(right, vp):
        th += -be * x - (h - 1) * (x - pi) / 2
    return sign * th


def on_surface(expr, v, vp):
    """eliminate v'_last with the constraint sum v + sum v' = 2 pi"""
    return sp.expand(expr.subs(vp[-1], 2 * pi - sum(v) - sum(vp[:-1])))


def swap(expr, v, vp):
    tmp = sp.symbols('tmp0:%d' % len(v))
    e = expr.subs(dict(zip(v, tmp)), simultaneous=True)
    e = e.subs(dict(zip(vp, v)), simultaneous=True)
    return e.subs(dict(zip(tmp, vp)), simultaneous=True)


r = 3
v = sp.symbols('v1:%d' % (r + 1), positive=True)
vp = sp.symbols('w1:%d' % (r + 1), positive=True)
sigma, d = sp.symbols('sigma d')
al = sp.symbols('alpha1:%d' % (r + 1))
be = sp.symbols('beta1:%d' % (r + 1))
g = sp.symbols('g1:%d' % (r + 1))

# (1) general antisymmetric part
left = list(zip(al, g)); right = list(zip(be, g))
Th = theta(sigma, d, left, right, v, vp)
anti = on_surface(Th - swap(Th, v, vp), v, vp)
pred = on_surface(sum((sigma + al[i] + be[i] + g[i] - d / 2) * (v[i] - vp[i]) for i in range(r)), v, vp)
print('(1) Theta - swap(Theta) - sum_i (sigma+alpha_i+beta_i+g_i-d/2)(v_i-v_i\') =', sp.simplify(anti - pred))

# (2) wheel
gg = sp.symbols('g')
Thw = theta(sigma, 2 * (sigma + gg), [(0, gg)] * r, [(0, gg)] * r, v, vp)
print('(2) wheel Theta - pi(sigma+1/2) =', sp.simplify(on_surface(Thw - pi * (sigma + sp.Rational(1, 2)), v, vp)))

# (3) R kernel
q, tau = sp.symbols('q tau')
leftR = [(0, q), (0, q), (0, tau)]
rightR = [(0, q), (0, q), (q - tau, tau)]
ThR = theta(q, 4 * q, leftR, rightR, v, vp)
target = pi * (q + sp.Rational(1, 2)) + (tau - q) * (v[2] + vp[2]) / 2
print('(3) R kernel: Theta - [pi(q+1/2) + (tau-q)(v3+v3\')/2] =', sp.simplify(on_surface(ThR - target, v, vp)))
print('    R kernel: Theta - swap(Theta) =', sp.simplify(on_surface(ThR - swap(ThR, v, vp), v, vp)))
print('    per-factor balance sigma+alpha_i+beta_i+g_i-d/2:',
      [sp.simplify(q + a + b + gi - 2 * q) for (a, gi), (b, _) in zip(leftR, rightR)])
# naive (literal Thm 6) reading: one g for all three factors would need sigma + g = d/2 for each; the third has g=tau
print('    literal Thm-6 balance of the third factor without its shift (beta_3 -> 0): sigma+g_3-d/2 =', sp.simplify(q + tau - 2 * q))

# (4) lower half plane
ThRl = theta(q, 4 * q, leftR, rightR, v, vp, sign=-1)
print('(4) R kernel lower half plane: Theta\' + Theta =', sp.simplify(on_surface(ThRl + ThR, v, vp)))

# (5) controls: per-factor balance broken but total balance kept
eps = sp.symbols('epsilon')
rightC1 = [(eps, q), (-eps, q), (q - tau, tau)]
ThC1 = theta(q, 4 * q, leftR, rightC1, v, vp)
print('(5) control C1 (beta=(eps,-eps,q-tau)): Theta - swap(Theta) =', sp.factor(on_surface(ThC1 - swap(ThC1, v, vp), v, vp)))
# wrong multiplicity dimension
dp = sp.symbols('dprime')
ThC2 = theta(q, dp, leftR, rightR, v, vp)
print('    control C2 (multiplicity at d\'): Theta - swap(Theta) =', sp.factor(on_surface(ThC2 - swap(ThC2, v, vp), v, vp)))
