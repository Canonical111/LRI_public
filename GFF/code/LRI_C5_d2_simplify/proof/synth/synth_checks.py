# Synthesizer checks for proof_d2.tex (note normalization a = A(1/2), b = B(1/2)).
# Exact sympy algebra + 70-digit stored single sums (confirm_dps70.json). Quick (< 1 min).
import json, sympy as sp, mpmath as mp
mp.mp.dps = 70
ok = []
def rep(name, val, tol=None):
    print(f'{name}: {val}')
# ---------- 1. residues rho_j(x) at x=1/2 and their x-derivatives ----------
u, x = sp.symbols('u x')
eps = sp.symbols('epsilon')
rho = []
for j in range(3):
    expr = sp.cos(2*sp.pi*u + sp.pi*(sp.Rational(1,2)+eps))**j / (sp.sin(sp.pi*(sp.Rational(1,2)+eps+u))**4 * sp.sin(sp.pi*u)**4)
    ser = sp.series(expr, u, 0, 1).removeO()
    r = sp.simplify(ser.coeff(u, -1))
    r0 = sp.simplify(sp.series(r, eps, 0, 2).removeO())
    rho.append((sp.nsimplify(r0.coeff(eps,0)), sp.nsimplify(r0.coeff(eps,1))))
print('rho_j(1/2), rho_j\'(1/2):', rho)
assert rho == [(0,12),(-4/sp.pi,0),(0,16)] or [(sp.simplify(a-b),sp.simplify(c-d)) for (a,c),(b,d) in zip(rho,[(0,12),(-4/sp.pi,0),(0,16)])]==[(0,0)]*3
# ---------- 2. collapse algebra (note normalization) ----------
a,b,Sy,Sxy,L2c = sp.symbols('a b S_y S_xy log2', positive=True)
g = sp.EulerGamma; psih = -g - 2*L2c
Ad = sp.pi*b + 4*sp.pi**2*Sy + 4*psih*a
Bd = 2*sp.pi*a - 2*sp.pi*Sxy + 4*psih*b
Lcoll = -6*a**2 - 8*b**2 + 4/sp.pi*(a*Bd + Ad*b) - 32/sp.pi*psih*a*b
print('collapse (sums form) - [2a^2-4b^2+16 pi b Sy - 8 a Sxy] =', sp.simplify(sp.expand(Lcoll - (2*a**2-4*b**2+16*sp.pi*b*Sy-8*a*Sxy))))
lemA = (sp.pi*b - 2*a*L2c)/(4*sp.pi**2); lemB = a/4 + b*L2c/sp.pi
print('Adot with lemmas - [2 pi b - (10log2+4g)a] =', sp.simplify(sp.expand(Ad.subs({Sy:lemA}) - (2*sp.pi*b-(10*L2c+4*g)*a))))
print('Bdot with lemmas - [3pi/2 a - (10log2+4g)b] =', sp.simplify(sp.expand(Bd.subs({Sxy:lemB}) - (sp.Rational(3,2)*sp.pi*a-(10*L2c+4*g)*b))))
print('L2 with lemmas + 2log2*8ab/pi =', sp.simplify(sp.expand(Lcoll.subs({Sy:lemA,Sxy:lemB}) + 2*L2c*8*a*b/sp.pi)))
pslq = 3*a**2 - 2*b**2 + 8*sp.pi*b*Sy - 12*a*Sxy   # finder's PSLQ form, note normalization
Delta = pslq - (2*a**2-4*b**2+16*sp.pi*b*Sy-8*a*Sxy)
print('PSLQ form - structural form =', sp.factor(Delta), '; with lemmas:', sp.simplify(Delta.subs({Sy:lemA,Sxy:lemB})))
# ---------- 3. K2 Laurent extraction (exact) ----------
t = sp.symbols('tau')
uu, vv, ss, ww = sp.symbols('u v sigma w')
FF = 1 + uu*t + vv*t**2
GG = 1 + ss*t**3 + ww*t**4
C = sp.gamma(t)/sp.gamma(1-t)
X = (sp.gamma(sp.Rational(1,2)-t/2)/sp.gamma(sp.Rational(1,2)+t/2))**2
kap = sp.gamma(1+t)/(sp.gamma(1-t)*sp.gamma(sp.Rational(1,2)+t)**2)
expr = sp.pi**2*FF**2 + sp.pi**2*(kap*GG/t)**2 - C**2*X**2
ser = sp.series(expr, t, 0, 3).removeO()
coef = {k: sp.simplify(sp.expand(ser.coeff(t,k))) for k in range(-2,3)}
for k in range(-2,2): print(f'[tau^{k}] C*D =', sp.simplify(coef[k]))
c2 = coef[2]
G = sp.Catalan; z3 = sp.zeta(3); l2 = sp.log(2)
subs = {uu: 4*l2 - 8*G/sp.pi, ss: 8*sp.pi*G - 14*z3}
c2s = sp.expand(c2.subs(ww, sp.pi**2*uu**2/2 - sp.pi**4/6 - sp.pi**2*vv).subs(subs))
print('[tau^2] C*D =', sp.simplify(c2s), ' target 128G^2-168 zeta3 log2: diff', sp.simplify(c2s-(128*G**2-168*z3*l2)))
c1s = sp.simplify(sp.expand(coef[1].subs(subs)))
print('[tau^1] C*D =', c1s, ' (+21 zeta3 =', sp.simplify(c1s+21*z3), ')')
K2 = 14*z3*l2 + sp.Rational(1,4)*(128*G**2-168*z3*l2)
print('K2 =', sp.expand(K2))
# ---------- 4. C5(2) assembly from gc:d2coefficients ----------
P4, P5, Q2 = sp.symbols('P4 P5 Q2')
K2s = 32*G**2 - 28*z3*l2; L2s = -2*l2*P4
c5 = (-1536*(P5+K2s) + 1536*l2*P4 - 576*L2s - 1728*Q2**2 + (11520*l2**2 + 28608*G)*Q2 - 3840*l2**4 - 21456*l2*z3)/48
target = -32*P5 + 56*l2*P4 - 36*Q2**2 + (240*l2**2 + 596*G)*Q2 - 1024*G**2 + 449*z3*l2 - 80*l2**4
print('972 C5(2) - formula =', sp.simplify(sp.expand(c5 - target)))
# ---------- 5. numerics with the finder's 70-digit sums ----------
d = json.load(open('<PROJECT>/LRI_C5_d2_simplify/confirm_dps70.json'))
S = {k: mp.mpf(v) for k,v in d['singles'].items()}
s0 = S["('L', (0, 0, 0, 0, 0, 0, 0))"]; sX = S["('L', (1, 0, 0, 0, 0, 0, 0))"]
sY = S["('L', (0, 0, 0, 1, 0, 0, 0))"]; sXY = S["('L', (1, 0, 0, 1, 0, 0, 0))"]; sZ1 = S["('L', (0, 0, 0, 0, 1, 0, 0))"]
an = mp.pi**2*s0; bn = -2*mp.pi*sX; Syn = sY; Sxyn = 4*sXY + sZ1
Bm, Bp = mp.mpf(d['B-']), mp.mpf(d['B+']); L2n = mp.mpf(d['checks']['L2']); K2n = mp.mpf(d['checks']['K2'])
ln2 = mp.log(2)
print('a - (B- - B+)/(4pi):', mp.nstr(an - (Bm-Bp)/(4*mp.pi),5), '  b - (B- + B+)/(8pi):', mp.nstr(bn-(Bm+Bp)/(8*mp.pi),5))
print('(L-a) note norm.:', mp.nstr(Syn - (mp.pi*bn - 2*an*ln2)/(4*mp.pi**2),5))
print('(L-b) note norm.:', mp.nstr(Sxyn - (an/4 + bn*ln2/mp.pi),5))
print('collapse sums form - L2:', mp.nstr(2*an**2-4*bn**2+16*mp.pi*bn*Syn-8*an*Sxyn - L2n,5))
print('L2 + 16 log2 ab/pi:', mp.nstr(L2n + 16*ln2*an*bn/mp.pi,5), '  8ab/pi - (B-^2-B+^2)/(4pi^3):', mp.nstr(8*an*bn/mp.pi - (Bm**2-Bp**2)/(4*mp.pi**3),5))
print('K2 - (32G^2-28 zeta3 log2):', mp.nstr(K2n - (32*mp.catalan**2 - 28*mp.zeta(3)*ln2),5))
print('a, b (note normalization):', mp.nstr(an,30), mp.nstr(bn,30))
print('S_y, S_xy:', mp.nstr(Syn,30), mp.nstr(Sxyn,30))
