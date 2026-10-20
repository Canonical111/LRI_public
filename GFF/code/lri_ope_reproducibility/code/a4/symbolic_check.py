import sympy as s
A,R,M,T,B,S=s.symbols('A R M T B S')
j0,ja,jb,jaa,jab,jbb=s.symbols('j0 ja jb jaa jab jbb')
e=s.symbols('e')
b3=T+s.Rational(87,4)*A*A-s.Rational(9,4)*R+M
g=e/3+2*A*e**2/9+(8*A*A/27-b3/81)*e**3
# Factor out kappa^-2 throughout.
f2=(j0-e*(ja+3*jb)/4+e**2*(jaa+6*jab+9*jbb)/32)/6
f3=jb/2+e*(-jab/8-jbb/2-R*j0/4)
f4=s.Rational(9,8)*jbb-A*jb+(A*A/8+3*R/4+M/9)*j0
c4=s.expand(g*g*f2+g**3*f3+g**4*f4).coeff(e,4)
rel=s.expand(c4*54/j0)
expected=s.Rational(25,36)*A*A-2*T/27+R/6+A*(jb-ja)/(3*j0)+(jaa-2*jab+jbb)/(32*j0)
assert s.simplify(rel-expected)==0
# log-directional derivatives of J turn the last terms into -AB/3+(B^2+S)/32.
closed=s.Rational(25,36)*A*A-2*T/27+R/6-A*B/3+(B*B+S)/32
# The relation to the thermal third-order coefficient.
C3=s.symbols('C3')
thermal=s.expand(closed.subs(T,s.Rational(3,4)*(A*A+R)-81*C3))
assert s.simplify(thermal-(6*C3+s.Rational(23,36)*A*A+R/9-A*B/3+(B*B+S)/32))==0
# Regulator-dependent bare normalization F=1+f1*e+f2*e^2:
f1,f2c,b2=s.symbols('f1 f2 b2')
gstar=e/3-b2*e**2/27+(2*b2*b2/243-b3/81)*e**3
F=1+f1*e+f2c*e*e
r=-3*f1-3*(f2c+f1*f1)*e
t=9*f1*f1-b2*f1
h=F*gstar+r*gstar*gstar+t*gstar**3
assert all(s.expand(h-gstar).coeff(e,n)==0 for n in (1,2,3))
print('PASS: fixed-point assembly; directional-derivative reduction; C3 relation; bare-normalization matching.')
print('a4/a2 =',closed)
