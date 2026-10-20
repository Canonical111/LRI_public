"""Independent exact stability-invariant expansion at the next half order."""
import sympy as s, json
from pathlib import Path
OUT=Path(__file__).resolve().parent.parent/'verification/algebra'
OUT.mkdir(parents=True,exist_ok=True)
u,z,d=s.symbols('u z delta')
a,b,c,f,p,A,E,G,q,k,V,R,J,L,M,N=s.symbols('a b c f p A E G q k V R J L M N')
alpha,beta,gamma,Phi,Psi,Omega,Q,P,K=s.symbols('alpha beta gamma Phi Psi Omega Q P K')
F=z+u*(1+a*z+p*d+A*z*z+E*d*z+V*d*d+alpha*z**3+beta*z*z*d+gamma*z*d*d)+u*u*(b+G*z+R*d+Phi*z*z+Psi*z*d)+u**3*(J+Omega*z)
H=-d+4*u+u*u*(c+f*z+q*d+L*z*z+M*z*d+Q*d*d)+u**3*(k+N*z+P*d)+K*u**4
# Truncated polynomial composition avoids expanding high powers of symbolic jets.
def cut(ex,n=4):
 return s.Add(*(co*u**i*z**j*d**l for (i,j,l),co in s.Poly(s.expand(ex),u,z,d).terms() if i+j+l<=n))
def comp(ex,us,zs,n):
 def truncmul(a,b):
  out={}
  for i,v in a.items():
   for j,w in b.items():
    if i+j<=n:out[i+j]=out.get(i+j,0)+v*w
  return {i:s.expand(v) for i,v in out.items()}
 uc={int(k[0]):v for k,v in s.Poly(us,d).terms()};zc={int(k[0]):v for k,v in s.Poly(zs,d).terms()}
 up=[{0:s.S.One}];zp=[{0:s.S.One}]
 for h in range(n):up.append(truncmul(up[-1],uc));zp.append(truncmul(zp[-1],zc))
 out={}
 for (i,j,l),co in s.Poly(cut(ex,n),u,z,d).terms():
  for m,v in truncmul(up[i],zp[j]).items():
   if m+l<=n:out[m+l]=out.get(m+l,0)+co*v
 return s.Poly(s.Add(*(s.expand(v)*d**i for i,v in out.items())),d)

u2=-c/s.Integer(64)
z2=a/s.Integer(16)-b/s.Integer(16)+c/s.Integer(64)-p/s.Integer(4)
u3=c*c/s.Integer(512)+f/s.Integer(256)-k/s.Integer(256)-q/s.Integer(64)
us=d/4+u2*d*d+u3*d**3
zs=-d/4+z2*d*d
z3=-comp(F,us,zs,3).nth(3);zs+=s.expand(z3)*d**3
u4=-comp(H,us,zs,4).nth(4)/4;us+=s.expand(u4)*d**4
# Avoid unneeded z4 expression in the determinant, but enforce it for full Jacobian.
z4=-comp(F,us,zs,4).nth(4)
assert all(comp(H,us,zs,4).nth(i)==0 for i in range(5))
Det=2*u*(1+z)*(s.diff(F,u)*s.diff(H,z)-s.diff(F,z)*s.diff(H,u))
Trace=2*u*s.diff(F,u)+(1+z)*s.diff(H,z)
Dj=comp(Det,us,zs,4);Tj=comp(Trace,us,zs,3)
D4=s.factor(Dj.nth(4));full=s.det(s.Matrix([2*u*F,(1+z)*H]).jacobian([u,z]))
# z4 affects 2F in full Jacobian but its determinant correction starts at delta^5,
# since H_z begins at delta^2. Verify directly at this order.
assert s.expand(comp(full,us,zs,4).nth(4)-D4)==0
new=[alpha,beta,gamma,Phi,Psi,Omega,Q,P,K]
old=s.expand(D4).subs(dict.fromkeys(new,0))
print('D4 =',s.expand(D4));print('new combination =',s.expand(D4-old));print('old =',old)
print('D2 =',s.factor(Dj.nth(2)));print('D3 =',s.factor(Dj.nth(3)))
for key,val in [('D4',D4),('old_D4',old),('u4',u4),('z3',z3)]:(OUT/(key+'_symbolic.expr')).write_text(str(s.expand(val)))
out={k:str(s.expand(v)) for k,v in {'D4':D4,'old_D4':old,'u4':u4,'z3':z3,'new':D4-old}.items()}
out['checks']=['H=0 through delta^4; z4 fixed by F=0','Full Jacobian determinant equals fixed-point determinant through delta^4']
(OUT/'D4_algebra.json').write_text(json.dumps(out,indent=2))
print('PASS: exact determinant and fixed-point checks')
