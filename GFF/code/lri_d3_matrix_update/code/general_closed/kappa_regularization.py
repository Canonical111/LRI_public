import sympy as s
x,p=s.symbols('x p',real=True) # p = pi^2
D=s.symbols('D1:5')
J=s.symbols('J1:4')
H=s.symbols('H')
l1,l2,l3,l4=s.symbols('l1:5')
r0=l1/2+H
r1=l2/2+J[0]-p/3
r2=l3/2+J[1]
r3=l4/2+J[2]-2*p**2/15
R=r0/2*(l1**3+3*l1*l2+l3)+s.Rational(3,4)*r1*(l1*l1+l2)-(l1*r2+r3)/4-l1**4/12+l1*l1*l2/8+s.Rational(7,24)*l1*l3+l2*l2/8+l4/12
C=[-x,-x*x-s.Rational(2,3)*p,-2*x**3-2*p*x,-6*x**4-8*p*x*x-s.Rational(28,15)*p*p]
Rinf=s.factor(R.subs(dict(zip([l1,l2,l3,l4],C))).subs(dict(zip(J,[0]*3))))
P=s.Poly(s.expand(R.subs(dict(zip([l1,l2,l3,l4],[C[i]+D[i] for i in range(4)])))-(p+x*x)**2/2),*D,*J,H)
print('Rinf=',Rinf)
print('regular terms',len(P.terms()), 'zero constant=',P.coeff_monomial(1))
print(s.collect(P.as_expr(),H))
for powers,c in P.terms():
    assert sum(powers[:-1])>=1
open(__import__('pathlib').Path(__file__).resolve().parents[2]/'verification/general_closed/K_regular_poly.txt','w').write(str(P.as_expr()))
