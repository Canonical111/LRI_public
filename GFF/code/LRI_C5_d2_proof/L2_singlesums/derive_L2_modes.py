# Derive L2 = (1/2) dW/dx at x=1/2 from the two-mode form Omega_hat(t;x) = Ah(x) + Bh(x) cos(2 pi t + pi x),
# W(x) = -Res_{t=0} Omega_hat^2 / (sin^4(pi t) sin^4(pi (t+x))).
import sympy as sp
t,d=sp.symbols('t delta')
A0,B0,A1,B1=sp.symbols('A0 B0 A1 B1')   # Ah(1/2), Bh(1/2), Ah'(1/2), Bh'(1/2)
x=sp.Rational(1,2)+d
Ah=A0+A1*d; Bh=B0+B1*d
f=(Ah+Bh*sp.cos(2*sp.pi*t+sp.pi*x))**2/(sp.sin(sp.pi*t)**4*sp.sin(sp.pi*(t+x))**4)
# residue at t=0: coefficient of t^-1; expand to first order in delta
f1=sp.series(f,d,0,2).removeO()
W0=-sp.residue(f1.coeff(d,0),t,0)
W1=-sp.residue(f1.coeff(d,1),t,0)
W0=sp.simplify(W0); W1=sp.simplify(W1)
print('W(1/2) =',W0)
print("W'(1/2) =",sp.expand(W1))
a,b,Sy,Sxy=sp.symbols('a b Sy Sxy')
sub={A0:sp.pi**2*a,B0:sp.pi**2*b,A1:sp.pi*sp.pi**2*b+4*sp.pi**2*Sy,B1:2*sp.pi**3*a-2*sp.pi*Sxy}
L2=sp.expand(W1.subs(sub)/2)
print('L2 =',L2)
C62d=3*sp.pi**4*a**2-2*sp.pi**4*b**2+8*sp.pi**3*b*Sy-12*sp.pi**2*a*Sxy
print('L2 - C62d formula =',sp.simplify(L2-C62d))
L2rel=sp.simplify(L2.subs({Sy:(sp.pi*b-2*a*sp.log(2))/4,Sxy:sp.pi**2*a/4+sp.pi*b*sp.log(2)}))
print('L2 with R1,R2 =',L2rel,'  target -16 pi^3 log2 ab:',sp.simplify(L2rel+16*sp.pi**3*sp.log(2)*a*b))
