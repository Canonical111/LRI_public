"""Independent lower-flow prediction and exact reduction of Q8 higher logs."""
from pathlib import Path
import sympy as s,json,time
from read_expression import load
ROOT=Path(__file__).resolve().parent;start=time.time();g,h,l=s.symbols('g h ell');Z2=s.Symbol('Z2')
a,A,b,G,J,c,f,L,k,N,K=s.symbols('a A b G J c f L k N K')
B=1-s.sqrt(2)*h;z=B*B-1
bg=z*g+(1+a*z+A*z*z)*g**3+(b+G*z)*g**5+J*g**7
bh=-B/(2*s.sqrt(2))*(4*g*g+(c+f*z+L*z*z)*g**4+(k+N*z)*g**6+K*g**8)
Q20,lam2,U2,U3,K40,V1,V2,K60,W1,K80=s.symbols('Q20 lam2 U2 U3 K40 V1 V2 K60 W1 K80')
R0=h+s.sqrt(2)*Q20*g*g+lam2*h*g*g+U2*h*h*g*g+U3*h**3*g*g+s.sqrt(2)*K40*g**4+V1*h*g**4+V2*h*h*g**4+s.sqrt(2)*K60*g**6+W1*h*g**6+s.sqrt(2)*K80*g**8
def trunc(ex):return s.Add(*(co*g**i*h**j for (i,j),co in s.Poly(s.expand(ex),g,h).terms() if i+2*j<=8))
bg=trunc(bg);bh=trunc(bh);cur=trunc(R0);pred={}
for n in range(1,8):
 cur=trunc(bg*s.diff(cur,g)+bh*s.diff(cur,h));pred[n]=s.expand(cur.subs(h,0)).coeff(g,8)/s.sqrt(2)/s.factorial(n)
 print('lie',n,flush=True)
sub={Q20:-1,lam2:10-4*Z2,a:-4*Z2,c:-16}
expected={5:96*Z2-s.Rational(3656,15),6:-s.Rational(664,15),7:-s.Rational(1088,315)}
raw=load(ROOT/'series'/'norm_K8_0_0.expr');checks={}
for n in (5,6,7):
 co=s.expand(pred[n].subs(sub));assert s.expand(co-expected[n])==0,(n,co)
 diff=s.expand(raw.coeff(l,n)-co)
 (ROOT/f'K8_log{n}_residual.expr').write_text(str(diff))
 diff=diff.subs(s.polylog(2,s.Rational(5,8)),Z2-s.log(s.Rational(3,8))*s.log(s.Rational(5,8))-s.polylog(2,s.Rational(3,8)))
 diff=diff.subs(s.polylog(2,-s.Rational(2,3)),-s.log(s.Rational(3,5))**2/2-s.polylog(2,s.Rational(2,5)))
 diff=s.expand(s.expand_log(diff.subs(s.pi**2,6*Z2),force=True))
 diff=s.expand(diff.subs({s.log(6):s.log(2)+s.log(3),s.log(10):s.log(2)+s.log(5)}))
 assert diff==0,(n,diff)
 checks[str(n)]={'prediction':str(co),'exact_residual':'0','unknown_K_used':False,'dilogarithm_identities':['Euler reflection at 3/8','Landen at 2/5'] if n==5 else []}
 print('PASS',n,co,flush=True)
(ROOT/'Q8_fresh_higher_log_checks.json').write_text(json.dumps({'checks':checks,'seconds':time.time()-start,'new_raw_integral_used_for_comparison_only':True},indent=2))
