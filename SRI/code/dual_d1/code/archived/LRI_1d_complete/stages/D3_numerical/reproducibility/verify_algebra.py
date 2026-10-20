import sympy as s
u,z,d,t=s.symbols('u z d t');a,b,c,f,p,A,E,G,q,k=s.symbols('a b c f p A E G q k')
F=z+(1+a*z+p*d+A*z*z+E*d*z)*u+(b+G*z)*u*u
H=-d+4*u+(c+f*z+q*d)*u*u+k*u**3
u2,u3,z2=s.symbols('u2 u3 z2');us=d/4+u2*d*d+u3*d**3;zs=-d/4+z2*d*d
fs=s.series(F.subs({u:us,z:zs}),d,0,3).removeO().expand();hs=s.series(H.subs({u:us,z:zs}),d,0,4).removeO().expand()
sol=s.solve([fs.coeff(d,2),hs.coeff(d,2),hs.coeff(d,3)],(u2,u3,z2),dict=True)[0]
D=2*u*(1+z)*(s.diff(F,u)*s.diff(H,z)-s.diff(F,z)*s.diff(H,u));D=s.series(D.subs({u:us,z:zs}).subs(sol),d,0,4).removeO().expand()
D3=(16*A-32*E-8*G+8*b+c*c+4*f-4*k+32*p-8*q)/64
assert s.simplify(D.coeff(d,3)-D3)==0
D2,T2,dd3=s.symbols('D2 T2 D3')
expr=1+(d/2+T2*d*d)/2-s.sqrt(2*d+(s.Rational(1,16)-D2)*d*d+(T2/4-dd3)*d**3)
ss=s.series(expr.subs(d,2*t*t),t,0,6).removeO().expand()
assert s.simplify(ss.coeff(t,5)-(2*dd3-T2/2+(D2-s.Rational(1,16))**2/4))==0
print('Fixed point:',sol);print('D3:',D3);print('Thermal coefficient:',ss.coeff(t,5));print('All invariant algebra checks passed.')
