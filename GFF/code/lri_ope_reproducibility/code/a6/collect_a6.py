"""Collect the completed diagram/forest result into the physical sixth coefficient."""
import json,sympy as s
from pathlib import Path
names='A R U V X M N T P P5 K L Z Ccross p1_3 p1_m1 t1 W4 W5 W6 b5'
v=dict(zip(names.split(),s.symbols(names)))
r=json.load(open('symbolic_results.json'));u=json.load(open('universal_assembly.json'))
parse=lambda expr:s.sympify(expr,locals=v)
w4=parse(r['S4']['2']);w5=parse(r['S5']['1']);w6=parse(r['S6']['0']);b5=parse(r['b5']);c5=parse(r['c5']);base=parse(u['h4'])
h4=s.expand(base.subs({v['W4']:w4,v['W5']:w5,v['W6']:w6,v['b5']:b5}))
# Match the zeta4 variable to the Gamma jet's fixed trigamma.
h4=h4.subs(v['t1'],s.Symbol('p1_0'))
print('h4 =',h4,flush=True)
A,R,U,V,X,M,N,T,P,P5,K,L,Z=[v[x] for x in 'A R U V X M N T P P5 K L Z'.split()]
D5=-s.Rational(16347,64)*A**4-s.Rational(57,4)*A*A*M-s.Rational(393,8)*A*A*T+s.Rational(3159,32)*A*A*R-3*A*M*N-s.Rational(3657,32)*A*U+s.Rational(189,16)*A*V-24*K-M*T+s.Rational(3,4)*M*R+s.Rational(45,8)*R*T-s.Rational(225,64)*R**2-s.Rational(75,64)*X+s.Rational(447,4)*Z-54*A*P-9*L-s.Rational(7,4)*T**2-24*P5
assert s.expand(3*c5-b5-D5)==0
for sym in ('M','N','Ccross','p1_m1','p1_3'):
 assert not h4.has(v[sym]),('did not cancel',sym)
# fixed zeta4 may still survive: show rather than discard.
C3,C4,C5=s.symbols('C3 C4 C5')
thermal5=(-1536*(P5+K)+384*A*P-576*L-48*T**2+120*A**2*T+168*T*R+7152*Z-15*A**4-90*A**2*R+414*A*U-108*A*V-117*R**2-75*X)/46656
thermal4=(16*P-A**3-s.Rational(4,3)*A*T-3*A*R+s.Rational(53,2)*U-3*V)/648
thermal3=(A*A+R)/108-T/81
# Eliminate P5, P and T successively using the already evaluated thermal series.
elim={P5:s.solve(s.Eq(C5,thermal5),P5)[0],P:s.solve(s.Eq(C4,thermal4),P)[0],T:s.solve(s.Eq(C3,thermal3),T)[0]}
h4therm=h4
for sym in (P5,P,T):h4therm=s.expand(h4therm.subs(sym,elim[sym]))
print('h4 thermal =',h4therm,flush=True)
B,S,D2,D3=s.symbols('B S D2 D3')
h1=4*A/3;h2=25*A*A/36+R/6-2*T/27
h3=s.Rational(17,108)*A**3+A*R/12-2*A*T/27+4*P/27+s.Rational(71,216)*U-V/36
p6=s.expand(h4-B*h3/4+(B*B+S)*h2/32-(B**3+3*B*S+D2)*h1/384+(B**4+6*B*B*S+3*S*S+4*B*D2+D3)/6144)
print('a6/a2=',p6,flush=True)
res={'h4':str(h4),'h4_thermal':str(h4therm),'a6_over_a2':str(p6),'b5':str(b5),'c5':str(c5),'D5_match':True,'mass_and_crossed_master_cancel':True,'h4_latex':s.latex(h4),'h4_thermal_latex':s.latex(h4therm)}
Path('collected_a6.json').write_text(json.dumps(res,indent=2))
