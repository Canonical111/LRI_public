"""Exact re-derivation of the algebra of Z/Z_general_d.tex (review key Z-rigor).
Trig functions of pi*b/2 are handled as s, c with the derivation d/db: s -> (pi/2) c, c -> -(pi/2) s, and the
result is reduced on the circle by the rational parametrisation s = 2x/(1+x^2), c = (1-x^2)/(1+x^2) (exact)."""
import sympy as sp

P, s, c, x = sp.symbols('P s c x')          # P stands for pi
R = sp.symbols('R0:3'); M = sp.symbols('M0:3')
circ = {s: 2*x/(1+x**2), c: (1-x**2)/(1+x**2)}

def Db(e):
    """d/db acting on polynomials/rational functions in s, c, R_k, M_k."""
    out = sp.diff(e, s)*(P/2)*c + sp.diff(e, c)*(-(P/2)*s)
    for k in range(2):
        out += sp.diff(e, R[k])*R[k+1] + sp.diff(e, M[k])*M[k+1]
    return out

def zero(e):
    return sp.simplify(sp.together(e.subs(circ))) == 0

def show(name, e):
    print('%-48s %s' % (name, 'OK (exact 0)' if zero(e) else 'FAIL: ' + str(sp.factor(sp.together(e.subs(circ))))))

# ---- (F3) second form: residue of [c0 + c1 cos 2pi(t + b/4)]/D^3 at t=0 (numerical, with true trig) ----
t, bb, k0, k1 = sp.symbols('t b k0 k1')
D = sp.sin(sp.pi*t)*sp.sin(sp.pi*(t + bb/2))
Xi = k0 + k1*sp.cos(2*sp.pi*(t + bb/4))
coef = sp.series(Xi*t**3/D**3, t, 0, 3).removeO().coeff(t, 2)
claimed = -(2/(sp.pi*sp.sin(sp.pi*bb/2)**5))*((1+2*sp.cos(sp.pi*bb/2)**2)*k0 + 3*sp.cos(sp.pi*bb/2)*k1)
f = sp.lambdify((bb, k0, k1), -coef - claimed, 'mpmath')
import mpmath as mp
mp.mp.dps = 40
print('F3 second form, max numeric residual:', max(abs(f(mp.mpf(bv), mp.mpf('1.3'), mp.mpf('-0.7'))) for bv in ['0.3', '0.77', '1.3', '1.61']))

# ---- two-node theorem ----
X, Y, c0, c1, N, Rs, Ms = sp.symbols('X Y c0 c1 N Rs Ms')
sol = sp.solve([sp.Eq(X, c0 + c*c1), sp.Eq(Y, c0 - c1)], [c0, c1])
W = -2*N**3/(P*s**5)*((1+2*c**2)*sol[c0] + 3*c*sol[c1])
sub = {X: -(P*s/N)**3*Rs, Y: ((1+c)/2)**3*Ms/N**3}
u = 2*P**2*(1+2*c)/s**2
v = c*(1+c)**2/(2*P*s**3)
show('two-node W3 = uR + vMh', W.subs(sub) - (u*Rs + v*Ms))
chat = (N**3*sol[c0]).subs(sub)
show('c0hat = c(1+c)^2 Mh/8 - pi^3 s^3 R/(1+c)', chat - (c*(1+c)**2/8*Ms - P**3*s**3/(1+c)*Rs))
show('W3 = 6pi^2 R/s^2 + 4 c0hat/(pi s^3)', W.subs(sub) - (6*P**2/s**2*Rs + 4/(P*s**3)*chat))

# ---- jets of u, v (eq:uvjets) ----
show("u'",  Db(u) - (-2*P**3*(1+c+c**2)/s**3))
show("u''", Db(Db(u)) - (P**4*(1+5*c+2*c**2+c**3)/s**4))
show("v'",  Db(v) - (-(1+c)**2*(1+2*c)/(4*s**4)))
show("v''", Db(Db(v)) - (P*(1+c)**3*(2+c)/(4*s**5)))
# and the example in the proof
show("u' (proof form)", Db(u) - (-2*P**3*(s**2 + c*(1+2*c))/s**3))

# ---- p, w jets (proof of Thm simplified) ----
p = 6*P**2/s**2; w = 4/(P*s**3)
show("p'", Db(p) - (-6*P**3*c/s**3)); show("p''", Db(Db(p)) - 3*P**4*(1+2*c**2)/s**4)
show("w'", Db(w) - (-6*c/s**4)); show("w''", Db(Db(w)) - 3*P*(1+3*c**2)/s**5)

# ---- first-derivative identity ----
W3 = u*R[0] + v*M[0]
W1 = Db(W3)
W2 = Db(W1)
first = 8*P**3*s**2*(1+2*c)*R[1] + 2*s*c*(1+c)**2*M[1] - (8*P**4*s*(1+c+c**2)*R[0] + P*(1+c)**2*(1+2*c)*M[0])
lam = sp.symbols('lam')
# eq:first must equal (nonzero factor) * W1
show('eq:first = 4 pi s^4 * W1', first - 4*P*s**4*W1)
ch = c*(1+c)**2/8*M[0] - P**3*s**3/(1+c)*R[0]
ch1 = Db(ch); ch2 = Db(ch1)
firstzm = 3*P**3*s**2*R[1] + 2*s*ch1 - 3*P*c*(P**3*s*R[0] + ch)
show('eq:firstzm = (pi s^4/2)*W1', firstzm - (P*s**4/2)*W1)

# ---- simplified Z (eq:simplified) and Q form ----
cos_pid2 = c**2 - s**2       # cos(pi d/2) = cos(2 pi q) at b = d/2
Zfull = W2/9
Zsimp = 2*P**2/(3*s**2)*R[2] - P**4*cos_pid2/(3*s**4)*R[0] + (3*P/s**3*ch - 4*c/s**4*ch1 + 4/(P*s**3)*ch2)/9
kfac = sp.factor(sp.together(((Zfull - Zsimp)/W1).subs(circ)))
print('Zfull - Zsimp = W1 *', kfac, '(must be a pure multiple of W1, i.e. vanish when W1=0)')
# check that Zfull - Zsimp - kfac*W1 == 0 identically
show('  (Zfull - Zsimp) + (2 pi c/(9 s)) W1 == 0', (Zfull - Zsimp) + 2*P*c/(9*s)*W1)
Q = W3/3
ZQ = 2*P**2/(3*s**2)*R[2] - P**2*cos_pid2/(6*s**2)*Q + (P*(1+c**2)/s**5*ch - 4*c/s**4*ch1 + 4/(P*s**3)*ch2)/9
show('eq:simplified == eq:simplifiedQ', Zsimp - ZQ)
show('coefficient of R2 is u/9', sp.diff(Zsimp, R[2]) - u/9)
show('coefficient of M2 is v/9', sp.diff(Zsimp, M[2]) - v/9)
# R' expression of Prop. first
C0, C1 = sp.symbols('C0 C1')
# treat c0hat, c0hat' as independent symbols C0, C1 in eq:firstzm and solve for R'
fz = 3*P**3*s**2*R[1] + 2*s*C1 - 3*P*c*(P**3*s*R[0] + C0)
R1sol = sp.solve(sp.Eq(fz, 0), R[1])[0]
show("R' = pi c R/s + c c0/(pi^2 s^2) - 2 c0'/(3 pi^3 s)", R1sol - (P*c/s*R[0] + c/(P**2*s**2)*C0 - 2/(3*P**3*s)*C1))
# 3 s^2 + 2 cos 2pi q = 1 + c^2
show('3s^2 + 2cos(2pi q) = 1 + c^2', 3*s**2 + 2*cos_pid2 - (1 + c**2))
