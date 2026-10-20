# Residue functional for general x:  W = -Res_{u=0} (Ah + Bh cos(2 pi u + pi x))^2 / (sin^4(pi u) sin^4(pi (u+x)))
#   = -( rho0 Ah^2 + 2 rho1 Ah Bh + rho2 Bh^2 ),   rho_p(x) = Res_{u=0} cos^p(2 pi u+pi x)/(sin^4(pi u) sin^4(pi(u+x))).
import sympy as sp
u,x=sp.symbols('u x')
s,c=sp.sin(sp.pi*x),sp.cos(sp.pi*x)
def res(p):
    expr=sp.cos(2*sp.pi*u+sp.pi*x)**p*(u/sp.sin(sp.pi*u))**4/sp.sin(sp.pi*(u+x))**4
    ser=sp.series(expr,u,0,4).removeO()
    return sp.simplify(sp.trigsimp(ser.coeff(u,3)))
rho=[res(p) for p in range(3)]
for p,r in enumerate(rho): print('rho%d(x) ='%p,sp.factor(sp.simplify(r)))
h=sp.Rational(1,2)
for p,r in enumerate(rho):
    print('rho%d(1/2)='%p,sp.simplify(r.subs(x,h)),"  rho%d'(1/2)="%p,sp.simplify(sp.diff(r,x).subs(x,h)))
