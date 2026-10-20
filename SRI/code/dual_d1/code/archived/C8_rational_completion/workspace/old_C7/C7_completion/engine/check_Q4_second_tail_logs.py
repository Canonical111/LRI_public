"""Independent matched nonautonomous flow for the fourth-order current's
second-tail logarithms. The new Q coefficient cannot enter powers >=2.
"""
from pathlib import Path
import sympy as s,json,time
import assemble_C7 as ext
ac=ext.ac
from read_expression import load
ROOT=Path(__file__).resolve().parent;start=time.time()
g,h,d,l=s.symbols('g h d ell');p,V,c,q,Q=s.symbols('p V c q Q');a,A,E,f,L,M=s.symbols('a A E f L M')
qs=s.symbols('Q20 Q20d Q20dd');ls=s.symbols('lam2 lam2d lam2dd')
v0=(1-s.sqrt(2)*h)**2
expdl=1+d*l+d*d*l*l/2
u=g*g*(1-d*l*l+d*d*(l**4/2-l**3/3))
z=v0*expdl-1
bg=g*((v0-1)*expdl+(1+a*z+p*d+A*z*z+E*z*d+V*d*d)*u)
bh=-(1-s.sqrt(2)*h)/(2*s.sqrt(2))*(4*u+(c+f*z+q*d+L*z*z+M*z*d+Q*d*d)*u*u)
init=h+s.sqrt(2)*g*g*(qs[0]+qs[1]*d+qs[2]*d*d/2)+h*g*g*(ls[0]+ls[1]*d+ls[2]*d*d/2)
def trunc(ex):
 return s.Add(*(co*g**i*h**j*d**k for (i,j,k),co in s.Poly(s.expand(ex),g,h,d).terms() if i+2*j<=4 and k<=2))
bg=trunc(bg);bh=trunc(bh);rg=[trunc(init)]
for n in range(8):
 ex=sum(s.expand(bg).coeff(l,m)*s.diff(rg[n-m],g)+s.expand(bh).coeff(l,m)*s.diff(rg[n-m],h) for m in range(n+1))
 rg.append(trunc(ex)/(n+1))
 print('recursion',n+1,flush=True)
sub={p:load(ROOT/'p_check_symbolic.expr'),V:load(ROOT/'V_symbolic.expr'),c:-16,q:load(ROOT/'q_check_symbolic.expr')}
sub.update({a:load(ROOT/'a_check_symbolic.expr'),A:load(ROOT/'A_check_symbolic.expr'),E:load(ROOT/'E_check_symbolic.expr'),f:load(ROOT/'f_check_symbolic.expr'),L:load(ROOT/'L_symbolic.expr'),M:load(ROOT/'M_symbolic.expr')})
for j in range(3):
 sub[qs[j]]=ac.npol('Q2',0,j).coeff(ac.ell,0)
 sub[ls[j]]=ac.betaexpr(s.diff(ac.l2,ac.d,j),f'lambda2_d{j}_check')
raw=ac.npol('K4',0,2)/2
checks={}
for n in range(2,9):
 pred=s.expand(rg[n].subs(h,0)).coeff(g,4).coeff(d,2)/s.sqrt(2)
 assert not pred.has(Q),(n,pred)
 pred=s.expand(pred.subs(sub));diff=s.expand(raw.coeff(ac.ell,n)-pred).subs(s.pi**2,6*s.Symbol('Z2')).expand()
 (ROOT/f'K4_dd_log{n}_predicted.expr').write_text(str(pred));(ROOT/f'K4_dd_log{n}_residual.expr').write_text(str(diff))
 checks[str(n)]={'prediction_terms':len(s.Add.make_args(pred)),'residual_terms':0 if diff==0 else len(s.Add.make_args(diff)),'exact_zero':diff==0,'new_Q_used':False}
 print('POWER',n,'residual',checks[str(n)]['residual_terms'],flush=True)
(ROOT/'Q4_second_tail_higher_log_checks.json').write_text(json.dumps({'checks':checks,'seconds':time.time()-start},indent=2))
