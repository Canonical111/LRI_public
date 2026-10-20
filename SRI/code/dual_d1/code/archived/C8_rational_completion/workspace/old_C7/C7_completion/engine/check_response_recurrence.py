"""Check the finite-response subtraction recurrence by exact polynomial algebra."""
import sympy as s
from pathlib import Path
g,b=s.symbols('g b');v=b*b
c3,c5,c31,c51,c71,q0,k4,k41,k61,j1,j3,j5,l2,l4=s.symbols('c3 c5 c31 c51 c71 q0 k4 k41 k61 j1 j3 j5 l2 l4')
b3=c31+2*v*j1
h4=k41-2*q0*b3+l2
b5=c51-3*c3*b3-2*v*j1*h4+2*v*j3
h6=k61-2*q0*b5-4*k4*b3-l2*h4+l4
b7=c71-3*c3*b5-5*c5*b3-2*v*j1*h6-2*v*j3*h4+2*v*j5
J=s.Matrix([[1+3*c3*g*g+5*c5*g**4,s.sqrt(2)*b*(j1*g+j3*g**3+j5*g**5)],
 [s.sqrt(2)*b*(2*q0*g+4*k4*g**3),1+l2*g*g+l4*g**4]])
beta=s.Matrix([b3*g**3+b5*g**5+b7*g**7,s.sqrt(2)*b*(-g*g+h4*g**4+h6*g**6)])
rhs=s.Matrix([c31*g**3+c51*g**5+c71*g**7,s.sqrt(2)*b*(-g*g+k41*g**4+k61*g**6)])
res=J*beta-rhs
for j in (3,5,7): assert s.expand(res[0]).coeff(g,j)==0
for j in (2,4,6): assert s.expand(res[1]).coeff(g,j)==0
print('PASS: all six response-Jacobian equations through g^7/g^6.')
# Vacuum normalization at seven insertions.
a1,a3,a5,a7,z2,z4,z6=s.symbols('a1 a3 a5 a7 z2 z4 z6')
C7=a7-a5*z2+a3*(z2*z2-z4)+a1*(-z2**3+2*z2*z4-z6)
ratio=s.series((a1+a3*g*g+a5*g**4+a7*g**6)/(1+z2*g*g+z4*g**4+z6*g**6),g,0,8).removeO()
assert s.expand(ratio.coeff(g,6)-C7)==0
print('PASS: seven-kink vacuum-normalization formula.')
