# Symbolic check of the collapse  L2 = 3 pi^4 a^2 - 2 pi^4 b^2 + 8 pi^3 b Sy - 12 pi^2 a Sxy
# from the general-x two-mode theorem.
#   P(x)  = - Gamma(x)^-8 [u^3] { Phi(u;x)^2 sigma(u;x)^4 },  L2 = (1/2) P'(1/2)
#   sin^4(pi(u+x)) Phi(u;x) = A(x) + B(x) cos(2 pi u + pi x) + O(u^4)
#   A + B cos(pi x)      = sin^4(pi x) Gamma(x)^4 P11(x)
#   -2 pi B sin(pi x)    = 4 pi sin^3 cos Gamma^4 P11 + 4 sin^4 Gamma^4 S1(x)
#   P11(1/2)=a, P11'(1/2)=4 Sy, S1(1/2)=-pi b/2, S1'(1/2)=Sxy
import sympy as sp
u, e = sp.symbols('u epsilon')
a, b, Sy, Sxy = sp.symbols('a b Sy Sxy')
pi = sp.pi
x = sp.Rational(1, 2) + e
# first-order jets in e (that is all L2 needs)
P11 = a + 4*Sy*e
S1 = -pi*b/2 + Sxy*e
Gx = sp.gamma(x)
s, c = sp.sin(pi*x), sp.cos(pi*x)
A_plus_Bc = s**4*Gx**4*P11
B = -(4*pi*s**3*c*Gx**4*P11 + 4*s**4*Gx**4*S1)/(2*pi*s)
A = A_plus_Bc - B*c
expr = (A + B*sp.cos(2*pi*u + pi*x))**2/(sp.sin(pi*u)**4*sp.sin(pi*(u + x))**4)
# residue in u at 0: series of u^4*expr to order u^3, keeping first order in e
num = sp.series(u**4*expr, u, 0, 4).removeO()
R = sp.expand(num).coeff(u, 3)
Pcal = -pi**4*R/(Gx**8*s**4)
Pser = sp.series(Pcal, e, 0, 2).removeO()
P0 = sp.simplify(Pser.coeff(e, 0)); P1 = sp.simplify(Pser.coeff(e, 1))
print('P(1/2)       =', sp.simplify(P0), '   expected P4(2) = 8 pi^3 a b')
L2 = sp.simplify(sp.expand(P1/2))
print('L2 collapse  =', sp.expand(L2))
target = 3*pi**4*a**2 - 2*pi**4*b**2 + 8*pi**3*b*Sy - 12*pi**2*a*Sxy
print('difference   =', sp.simplify(sp.expand(L2 - target)))
l = sp.log(2)
L2final = sp.simplify(sp.expand(L2.subs({Sy: (pi*b - 2*a*l)/4, Sxy: pi**2*a/4 + pi*b*l})))
print('with (L-a),(L-b):  L2 =', sp.factor(L2final), '  = -2 log2 * P4(2)?', sp.simplify(L2final + 2*l*8*pi**3*a*b) == 0)
