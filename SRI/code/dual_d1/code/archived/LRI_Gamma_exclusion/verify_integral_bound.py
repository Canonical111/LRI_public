#!/usr/bin/env python3
"""Symbolic normalization/cancellation and positivity-bound checks.
SymPy only; does not evaluate any multiloop integral numerically.
"""
import sympy as s
A,D1,J,u,v,w,a4=s.symbols('A D1 J u v w a4')
S1=(A*A+8*A*D1+3*u+4*w-7*v-4*J)/4
U=-u-w+2*v+J
I1=s.Rational(3,2)*A*A+(u-v)/2
bracket=-12*A*A+9*S1-18*D1*A+9*U+6*I1+a4
assert s.expand(bracket-(s.Rational(3,4)*(u-v-A*A)+a4))==0
p,l=s.symbols('p l')
b=(bracket/81).subs({u:p*p/6,v:p*p/2,A:-p-4*l})
assert s.expand(b-(a4/81-((p+4*l)**2+p*p/3)/108))==0

# Squares avoid branch/sign assumptions in the density identities.
x,y=s.symbols('x y',real=True)
P=x*(1-x)*y*(1-y)*(x-y)
# Simultaneous inversion: P(1/x,1/y)^2 = P(x,y)^2/(xy)^8.
assert s.factor(P.subs({x:1/x,y:1/y}, simultaneous=True)**2-P**2/(x*y)**8)==0
assert s.factor(P.subs({x:1-x,y:1-y},simultaneous=True)**2-P**2)==0

# E|X-Y| for independent arcsine variables.
a=s.symbols('a',nonnegative=True)
F=2*a/s.pi
mean=s.simplify(2*s.integrate(F*(1-F)*s.sin(2*a),(a,0,s.pi/2)))
assert mean==4/s.pi**2

# Covariance of massless two-loop integral normalization at d=1.
K0,Ieps=s.symbols('K0 Ieps')
Ieps=2*K0/(3*(4*s.pi)**s.Rational(1,2)*s.gamma(s.Rational(1,2)))
alpha=s.simplify(3*(4*s.pi)**s.Rational(3,2)*s.gamma(s.Rational(1,2))**3*Ieps)
assert alpha==8*s.pi**2*K0
# K0 = (2 pi)^(-2) times the positive two-dimensional integral.
assert s.simplify(alpha.subs(K0,1/(2*s.pi)**2))==2

# Conversion from epsilon=1-4t^2 to f(t)=Delta_epsilon(t^2).
t=s.symbols('t'); eps=1-4*t*t
z=s.symbols('z')
f=s.Rational(1,2)-eps/6+z*eps**2/9-b*eps**3
assert s.simplify(s.diff(f,t,2).subs(t,s.Rational(1,2))-(s.Rational(4,3)+s.Rational(32,9)*z))==0
assert s.simplify(s.diff(f,t,3).subs(t,s.Rational(1,2))-(s.Rational(64,3)*z+384*b))==0
print('PASS: beta cancellation, integral normalization, two Mobius density symmetries, arcsine mean, endpoint derivative conversion.')
