# Step 5: numerical side conditions and exact algebraic identities of the dictionary.
import mpmath as mp
import sympy as sp
from params import setup
P = setup(60)
pi = P['pi']
def pr(name, val): print(f"{name:45s} {mp.nstr(val, 25)}")

print("== signs ==")
pr("X4", P['X4']); pr("Y4", P['Y4'])
pr("q72", P['q72']); pr("q71", P['q71']); pr("q70", P['q70'])
s2 = mp.sqrt(2)
a, b, c = 1233 - 278*s2, mp.mpf(556), 139*s2
pr("4ac-b^2", 4*a*c - b**2); pr("685548sqrt2-618272", 685548*s2 - 618272)
pr("rho8^2 - ((a-c)^2+b^2)", P['rho8']**2 - ((a - c)**2 + b**2))
pr("acosh argument (must be >1)", (1233 - 139*s2)/P['rho8'])
pr("a-c (>0 for principal atan)", a - c)
pr("radicand 40lam-279", P['rad1'])
pr("radicand C+ - B+^2/4", P['rad2p']); pr("radicand C- - B-^2/4", P['rad2m'])
pr("lambda (findroot)", P['lam_root']); pr("lambda (trig form)", P['lam_trig'])
pr("diff", P['lam_root'] - P['lam_trig'])
# all roots of cubic
x = sp.symbols('x')
cub = 4*x**3 - 112*x**2 + 909*x - 2250
print("cubic real roots:", [sp.N(r, 20) for r in sp.real_roots(cub)])
print("roots in (15,16):", [r for r in sp.real_roots(cub) if 15 < r < 16])
# 4 det(M + lam N)
lm = sp.symbols('lam')
M = sp.Matrix([[10, sp.Rational(21, 2), 0], [sp.Rational(21, 2), 18, sp.Rational(15, 2)], [0, sp.Rational(15, 2), 0]])
N = sp.Matrix([[0, 0, 1], [0, -1, 0], [1, 0, 1]])
print("4det(M+lam N) =", sp.expand(4*(M + lm*N).det()))
# M + lam N = 5(v+ v-^T + v- v+^T)
lam = P['lam']
Mn = mp.matrix([[10, 10.5, 0], [10.5, 18, 7.5], [0, 7.5, 0]]) + lam*mp.matrix([[0, 0, 1], [0, -1, 0], [1, 0, 1]])
vp = mp.matrix([1, P['Bp'], P['Cp']]); vm = mp.matrix([1, P['Bm'], P['Cm']])
R = Mn - 5*(vp*vm.T + vm*vp.T)
pr("max|M+lam N - 5(v+v-^T+v-v+^T)|", max(abs(R[i, j]) for i in range(3) for j in range(3)))
Pp = lambda z: z**2 + P['Bp']*z + P['Cp']
Pm = lambda z: z**2 + P['Bm']*z + P['Cm']
pr("P+(i)P-(i) re (claim -4/5)", (Pp(1j)*Pm(1j)).real); pr("P+(i)P-(i) im (claim -3/5)", (Pp(1j)*Pm(1j)).imag)
Dp = mp.sqrt((1 - P['Cp'])**2 + P['Bp']**2); Dm = mp.sqrt((1 - P['Cm'])**2 + P['Bm']**2)
pr("|P+(i)| - D+", abs(Pp(1j)) - Dp); pr("D+ D- - 1", Dp*Dm - 1)
# factorization P_sigma(tan th) = D sin(th+pi b) sin(th+pi bbar)/cos^2 th
th = mp.mpf('0.37')
for name, Pf, D, bet in (('+', Pp, Dp, P['betap']), ('-', Pm, Dm, P['betam'])):
    lhs = Pf(mp.tan(th)); rhs = D*mp.sin(th + pi*bet)*mp.sin(th + pi*mp.conj(bet))/mp.cos(th)**2
    pr(f"P{name}(tan th) factorization residual", abs(lhs - rhs))
# seventh: p(tan th) = sqrt185 sin sin / cos^2, q similar
z = mp.tan(th)
p7 = 7*z**2 + 13*z + 11
q7 = P['q72']*z**2 + P['q71']*z + P['q70']
b7 = P['beta7']
pr("p(tan th) factorization residual", abs(p7 - mp.sqrt(185)*mp.sin(th + pi*b7)*mp.sin(th + pi*mp.conj(b7))/mp.cos(th)**2))
pr("q(tan th) factorization residual", abs(q7 - P['rho7']*mp.sin(th + pi*P['eta7p'])*mp.sin(th + pi*P['eta7m'])/mp.cos(th)**2))
tb = mp.tan(pi*b7)
pr("tan(pi b)+tan(pi bbar) (13/7)", 2*tb.real); pr("tan(pi b)tan(pi bbar) (11/7)", abs(tb)**2)
pr("(1+t^2)(1+tbar^2) (185/49)", abs(1 + tb**2)**2)
# eighth factorization a sin^2+b sin cos+c cos^2 = rho8 sin(x+pi a+) sin(x+pi a-)
xx = mp.mpf('0.81')
lhs = a*mp.sin(xx)**2 + b*mp.sin(xx)*mp.cos(xx) + c*mp.cos(xx)**2
rhs = P['rho8']*mp.sin(xx + pi*P['a8p'])*mp.sin(xx + pi*P['a8m'])
pr("eighth factorization residual", abs(lhs - rhs))
# alpha relations
pr("cos(pi aW)-8/sqrt89", mp.cos(pi*P['alphaW']) - 8/mp.sqrt(89))
pr("cos(pi a6)-13/sqrt290", mp.cos(pi*P['alpha6']) - 13/mp.sqrt(290))
pr("sin(pi a6)-11/sqrt290", mp.sin(pi*P['alpha6']) - 11/mp.sqrt(290))
pr("rho4 cos(pi a4) - X4", P['rho4']*mp.cos(pi*P['alpha4']) - P['X4'])
pr("rho4 sin(pi a4) - Y4", P['rho4']*mp.sin(pi*P['alpha4']) - P['Y4'])
# Section 5.3 crude bounds: Gamma(1/4)<4 etc
pr("Gamma(1/4)", mp.gamma(0.25)); pr("C_s=-Y4", -P['Y4']); pr("C_d=-X4", -P['X4'])
# Eshift and Ereal coefficient checks
print("-544/3-476*32/3 =", sp.Rational(-544, 3) - sp.Rational(476*32, 3), "; 37631/128-476*9/3 =", sp.Rational(37631, 128) - sp.Rational(476*9, 3))
# F_0 audit formula vs definition (Section 6.1)
ell = P['ell']
def F_n(n):
    from mpmath import harmonic
    y = n + mp.mpf(1)/4
    H2n = mp.harmonic(2*n); Hn = mp.harmonic(n)
    h = ell + Hn - H2n
    H2n2 = sum(mp.mpf(1)/j**2 for j in range(1, 2*n + 1)); Hn2 = sum(mp.mpf(1)/j**2 for j in range(1, n + 1))
    H2n3 = sum(mp.mpf(1)/j**3 for j in range(1, 2*n + 1))
    delta = pi**2/3 - 4*H2n2 + 2*Hn2
    u = 1 - 14*y*h
    v = 196*y*h**2 - 28*h + 7*y*(delta - pi**2)
    T = 80*pi**2*y - 26*pi*u + 11*v
    K = 28*pi**2*y - 10*pi*u + 3*v
    return (98*H2n + 74*ell - 6*pi)*T - 98*pi*K - 98*(11*u - 13*pi*y)*(pi**2/3 + 4*H2n2) - 8624*y*(mp.zeta(3) - H2n3)
F0_audit = (39886*ell**3 - 10906*pi*ell**2 - 22792*ell**2 - 2188*pi**2*ell + 8156*pi*ell
            - mp.mpf(1679)/6*pi**3 + mp.mpf(2330)/3*pi**2 - 2156*mp.zeta(3))
pr("F_0 (definition)", F_n(0)); pr("F_0 (audit formula line 924)", F0_audit); pr("diff", F_n(0) - F0_audit)
