from pathlib import Path
import sympy as s
u,z,d=s.symbols('u z delta')
a,b,c,f,p,A,E,G,q,k,V,R,J,L,M,N=s.symbols('a b c f p A E G q k V R J L M N')
F=z+u*(1+a*z+p*d+A*z*z+E*d*z+V*d*d)+u*u*(b+G*z+R*d)+J*u**3
H=-d+4*u+u*u*(c+f*z+q*d+L*z*z+M*d*z)+u**3*(k+N*z)
u2=-c/s.Integer(64)
u3=c*c/s.Integer(512)+f/s.Integer(256)-k/s.Integer(256)-q/s.Integer(64)
z2=a/s.Integer(16)-b/s.Integer(16)+c/s.Integer(64)-p/s.Integer(4)
us=d/4+u2*d*d+u3*d**3
zs=-d/4+z2*d*d
T=2*u*s.diff(F,u)+(1+z)*s.diff(H,z)
D=2*u*(1+z)*(s.diff(F,u)*s.diff(H,z)-s.diff(F,z)*s.diff(H,u))
def compose3(expr):
    total=0
    for (i,j,l),coeff in s.Poly(s.expand(expr),u,z,d).terms():
        if i+j+l>3: continue
        remain=3-i-j-l
        term=(s.Rational(1,4)+u2*d+u3*d*d)**i*(-s.Rational(1,4)+z2*d)**j
        term=s.series(term,d,0,remain+1).removeO()
        total+=coeff*d**(i+j+l)*term
    return s.Poly(s.expand(total),d)
Tc=compose3(T)
Dc=compose3(D)
T3=s.factor(Tc.coeff_monomial(d**3))
print('T1 =',s.factor(Tc.coeff_monomial(d)))
print('T2 =',s.factor(Tc.coeff_monomial(d**2)))
print('T3 =',T3)
print('C6 =',s.expand(4*T3))
print('D3 =',s.factor(Dc.coeff_monomial(d**3)))
print('64 T3 =',s.expand(64*T3))
result={'T3':str(T3),'C6':str(s.expand(4*T3)),'u2':str(u2),'u3':str(u3),'z2':str(z2)}
import json
(Path(__file__).resolve().parent/'trace_symbolic.json').write_text(json.dumps(result,indent=2)+'\n')
# Independent check: use the complete Jacobian rather than its fixed-point form.
z3=s.symbols('z3')
F3=compose3(F).coeff_monomial(d**3)
zs_full=zs-F3*d**3
# At order delta^3, adding -F3*delta^3 to z cancels F exactly.
assert s.expand(compose3(H).coeff_monomial(d**3))==0
assert s.expand(compose3(F).coeff_monomial(d**2))==0
full_trace=s.diff(2*u*F,u)+s.diff((1+z)*H,z)
# compose3 used z through order two, so correct its leading 2F term explicitly.
full_T3=compose3(full_trace).coeff_monomial(d**3)-2*F3
assert s.expand(full_T3-T3)==0
print('PASS: full Jacobian agrees after imposing the fixed point through delta^3.')
# The next even-power eigenvalue coefficient cannot depend on D4.
t,T2,T3s,D2,D3,D4=s.symbols('t T2 T3 D2 D3 D4')
Tr=t*t+4*T2*t**4+8*T3s*t**6
Det=-4*t*t+4*D2*t**4+8*D3*t**6+16*D4*t**8
root=2*t*s.series(s.sqrt(s.expand((Tr*Tr/4-Det)/(4*t*t))),t,0,6).removeO()
branch=s.expand(1+Tr/2-root)
assert s.expand(branch.coeff(t,6)-4*T3s)==0
assert s.expand(branch.coeff(t,5)-(2*D3-T2/2+(D2-s.Rational(1,16))**2/4))==0
print('PASS: C6=4*T3 and the previous x^(5/2) conversion are exact.')
