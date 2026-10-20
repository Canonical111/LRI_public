"""Independent Lie-series predictions for the charge derivative of C7 response.
The auxiliary fugacity conversion is applied before comparing with raw moments.
No Omega, new raw single logarithm, or all-orders extrapolation is used.
"""
from pathlib import Path
import sympy as s,json,time
ROOT=Path(__file__).resolve().parent
start=time.time();g,h,e=s.symbols('g h e');b0=1+e/2;B=b0-s.sqrt(2)*h;z=B*B-1
Z2,Z3,Z4=s.symbols('Z2 Z3 Z4')
a,A,alpha,b,G,Phi,J,Omega,c,f,L,k,N=s.symbols('a A alpha b G Phi J Omega c f L k N')
bg=z*g+(1+a*z+A*z*z+alpha*z**3)*g**3+(b+G*z+Phi*z*z)*g**5+(J+Omega*z)*g**7
bh=-B/(2*s.sqrt(2))*(4*g*g+(c+f*z+L*z*z)*g**4+(k+N*z)*g**6)
C30,C30v,j3,j3v,H3,H3v,C50,C50v,j5,j5v,C70,C70v=s.symbols('C30 C30v j3 j3v H3 H3v C50 C50v j5 j5v C70 C70v')
et=s.symbols('eta');logB=-2*et+(2-Z2)*et**2+(2*Z3-s.Rational(8,3))*et**3
A1=s.series(s.exp(logB),et,0,4).removeO().subs(et,s.sqrt(2)*b0*h-2*h*h)
R0=g*A1+g**3*(C30+C30v*e+s.sqrt(2)*b0*h*(j3+j3v*e)+h*h*(H3+H3v*e))+g**5*(C50+C50v*e+s.sqrt(2)*b0*h*(j5+j5v*e))+g**7*(C70+C70v*e)
def trunc(ex):
 return s.Add(*(co*g**ig*h**ih*e**ie for (ig,ih,ie),co in s.Poly(s.expand(ex),g,h,e).terms() if ig+2*ih<=7 and ie<=1))
bg=trunc(bg);bh=trunc(bh);cur=trunc(R0);pred={0:s.expand(cur.subs(h,0)).coeff(g,7)}
for n in range(1,9):
 cur=trunc(bg*s.diff(cur,g)+bh*s.diff(cur,h));pred[n]=s.expand(cur.subs(h,0)).coeff(g,7)/s.factorial(n)
 print('computed lie step',n,'seconds',time.time()-start,flush=True)
known={a:-4*Z2,c:-16,C30:3-2*Z2,C30v:18-14*Z2-15*Z3-8*s.log(2),A:-8-4*Z2-2*Z3+16*s.log(2)}
known[j3]=-2*known[C30v]-26+8*Z2
out={}
for n in range(5,9):
 co=s.expand(pred[n]).coeff(e)-7*s.expand(pred[n-1]).subs(e,0)
 co=s.expand(co.subs(known));out[str(n)]=str(co)
 assert not co.free_symbols.intersection({Omega,J,k,alpha,Phi,L,N,C50,C50v,C70,C70v,j5,j5v,H3,H3v,j3v}),(n,co)
 print('auxiliary charge derivative log',n,co,flush=True)
 (ROOT/f'A7v_log{n}_predicted.expr').write_text(str(co))
expected={5:(3848*Z2-8824)/15,6:-s.Rational(1622,9),7:-s.Rational(6416,315),8:0}
for n,val in expected.items():assert s.expand(s.sympify(out[str(n)])-val)==0,(n,out[str(n)],val)
(ROOT/'A7v_high_log_predictions.json').write_text(json.dumps({'predictions':out,'auxiliary_fugacity_matching':'g_physical=g_auxiliary*exp[-e*ell], e=b0^2-1','single_log_used':False,'seconds':time.time()-start},indent=2))
print('PASS: independent regenerated leading logs',flush=True)
