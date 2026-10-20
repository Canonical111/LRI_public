import sympy as s
import series_engine as se
z=se.z
b0=se.beta(s.Rational(1,2),1-z);b2=se.beta(s.Rational(1,2)+2*z,1-z)
jg=se.add(se.mul(b0,b0,2),se.shift(se.scale(se.add(b0,se.scale(b2,-1)),2),-1))[2]
# Res gamma from shifting one Barnes contour.
A=se.A;j1,j2,j3,u1,u2,u3,v1,v2,v3=s.symbols('j1 j2 j3 u1 u2 u3 v1 v2 v3')
l2=j1/4+u1/2-v1/2;l3=j2/24-u2/12+v2/6;l4=j3/192+u3/96-v3/24
rg=A**4/6+2*A**2*l2+2*l2**2+4*A*l3+4*l4
print('JG',s.expand(jg));print('RES-JG',s.expand(rg-jg))
