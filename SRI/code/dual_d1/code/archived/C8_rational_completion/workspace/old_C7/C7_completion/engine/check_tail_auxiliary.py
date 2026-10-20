"""Independent nonautonomous matched-flow check of the five-kink tail logs.
The new R enters only the single logarithm; all higher logs are tested.
"""
import sympy as s
from pathlib import Path
import assemble_C6 as ac
ROOT=Path(__file__).resolve().parent
g,h,d,l=s.symbols('g h d ell')
a,A,p,E,b,G,R,c,f,q=s.symbols('a A p E b G R c f q')
z2,z3=s.symbols('Z2 Z3')
C30,C30d,j3,j3d=s.symbols('C30 C30d j3 j3d')
v0=(1-s.sqrt(2)*h)**2; vb=v0*(1+d*l); yy=g*g*(1-d*l*l)
bg=g*((v0-1)*(1+d*l)+(1+a*(vb-1)+p*d+A*(vb-1)**2+E*d*(vb-1))*yy+(b+G*(vb-1)+R*d)*yy**2)
bh=-(1-s.sqrt(2)*h)/(2*s.sqrt(2))*(4*yy+(c+f*(vb-1)+q*d)*yy**2)
eta=s.sqrt(2)*h-2*h*h
A10=1-2*eta+(4-z2)*eta**2
A11=2*eta+(-12+2*z2+2*z3)*eta**2
initial=g*(A10+d*A11)+g**3*(C30+d*C30d+s.sqrt(2)*h*(j3+d*j3d))
def tr(ex):
    return s.Add(*(co*g**ig*h**ih*d**idd for (ig,ih,idd),co in s.Poly(s.expand(ex),g,h,d).terms() if ig+2*ih<=5 and idd<=1))
bg=tr(bg);bh=tr(bh)
rg=[tr(initial)];maxn=7
for n in range(maxn):
    ex=0
    for m in range(n+1):
        ex+=s.expand(bg).coeff(l,m)*s.diff(rg[n-m],g)+s.expand(bh).coeff(l,m)*s.diff(rg[n-m],h)
    rg.append(tr(ex)/(n+1))
sub={a:ac.betaexpr(ac.needed['a_check'],'a_check'),A:ac.betaexpr(ac.needed['A_check'],'A_check'),p:ac.betaexpr(ac.needed['p_check'],'p_check'),E:ac.betaexpr(ac.needed['E_check'],'E_check'),b:ac.betaexpr(ac.needed['b_check'],'b_check'),G:ac.betaexpr(ac.needed['G_check'],'G_check'),c:-16,f:ac.betaexpr(ac.needed['f_check'],'f_check'),q:ac.betaexpr(ac.needed['q_check'],'q_check')}
sub.update({C30:ac.npol('C3').coeff(l,0),C30d:ac.npol('C3',0,1).coeff(l,0),j3:-2*ac.npol('C3',1,0).coeff(l,0)+ac.npol('EC3').coeff(l,0),j3d:-2*ac.npol('C3',1,1).coeff(l,0)+ac.npol('EC3',0,1).coeff(l,0)})
raw=ac.npol('C5',0,1)
for n in range(2,maxn+1):
    co=s.expand(rg[n].subs(h,0)).coeff(g,5).coeff(d,1)
    assert R not in co.free_symbols
    pred=s.expand(co.subs(sub)).subs(s.pi**2,6*z2)
    diff=s.expand(raw.coeff(l,n)-pred).subs(s.pi**2,6*z2).expand()
    (ROOT/f'C5_tail_log{n}_predicted.expr').write_text(str(pred))
    (ROOT/f'C5_tail_log{n}_residual_symbolic.expr').write_text(str(diff))
    print('log power',n,'predicted terms',len(s.Add.make_args(pred)),'residual terms',len(s.Add.make_args(diff)),flush=True)
print('PASS: all higher-log predictions exclude the new R.',flush=True)
for ig in [3,5]:
 rawx=ac.npol('C'+str(ig),0,1)
 for nn in range(1,8):
  co=s.expand(rg[nn].subs(h,0)).coeff(g,ig).coeff(d,1)
  sx=sub.copy();sx[R]=ac.betaexpr(ac.needed['R'],'R')
  pred=s.expand(co.subs(sx)).subs(s.pi**2,6*z2)
  diff=s.expand(rawx.coeff(l,nn)-pred).subs(s.pi**2,6*z2).expand()
  (ROOT/f'aux_g{ig}_d_log{nn}_residual_symbolic.expr').write_text(str(diff))
print('AUXILIARY ALL LOGS WRITTEN')
rawx=ac.npol('C5')
for nn in range(1,8):
 co=s.expand(rg[nn].subs({h:0,d:0})).coeff(g,5)
 pred=s.expand(co.subs(sub)).subs(s.pi**2,6*z2)
 diff=s.expand(rawx.coeff(l,nn)-pred).subs(s.pi**2,6*z2).expand()
 (ROOT/f'aux_g5_base_log{nn}_residual_symbolic.expr').write_text(str(diff))
