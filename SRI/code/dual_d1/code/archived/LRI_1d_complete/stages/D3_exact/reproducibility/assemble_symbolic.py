import sympy as s,json
from pathlib import Path
R=Path(__file__).resolve().parent
Z2,Z3,Z4=s.symbols('Z2 Z3 Z4');L=s.log(2)
def load(name):return s.sympify((R/(name+'.expr')).read_text()).subs(s.pi**2,6*Z2)
a=-4*Z2;c=-16;p=8-2*Z2-7*Z3-8*L
b=-18-6*Z2+s.Rational(28,3)*Z3+32*L-12*s.log(3)-4*L**2-8*s.polylog(2,-s.Rational(1,2))
f=32-s.Rational(136,3)*Z3-64*L+48*s.log(3)+16*L**2+32*s.polylog(2,-s.Rational(1,2))
P=4*Z2+s.Rational(8,3)*Z3-2+3*s.log(3)+L**2+2*s.polylog(2,-s.Rational(1,2))
A=-8-4*Z2-2*Z3+16*L
E=-16+14*Z2-22*Z3+12*Z4+8*L-8*L**2-16*s.polylog(4,s.Rational(1,2))-14*Z3*L+4*Z2*L**2-s.Rational(2,3)*L**4
EP3v=-108+60*Z2+22*Z3-34*Z4+16*L
EPQ4=6-12*Z2-54*Z3-25*Z4
C30=3-2*Z2;C30v=18-14*Z2-15*Z3-8*L;C30vv=load('Avv3_0_0')+8
K40=P+4*Z2-10;L2=10-4*Z2;L2d=-60+12*Z2+12*Z3+8*Z4
C51v=load('Av5_0_1')-load('Zv4_0_1')-C30v-14-4*Z2-load('Av3_1_1')
K61=load('Qbase6_0_1')+load('Zbase4_0_0')-P+7-6*Z2-load('Qbase4_1_1')-load('Zbase4_-1_1')
J3=-2*C30v-26+8*Z2
J3v=-2*C30vv+EP3v+4*Z2-4*Z3
L4=-2*K40-4*load('Qv4_0_0')+2*(EPQ4-6)
G=s.expand(C51v-3*C30v-3*C30*a+16-f+2*J3+2*J3v)
qd=s.expand(-4*(load('Qdelta4_0_1')-4+2*p+L2d))
k=s.expand(-4*(K61+2*b-4*K40-4*L2+L4))
D=s.expand((16*A-32*E-8*G+8*b+c*c+4*f-4*k+32*p-8*qd)/64)
Dstar=s.Rational(21,4)-13*Z2+11*Z3+11*Z4
for name,expr in [('G',G),('qd',qd),('k',k),('D3',D),('D3_difference',D-Dstar)]:
 expr=s.expand_log(expr,force=True).expand().subs(Z2**2,s.Rational(5,2)*Z4)
 (R/(name+'_symbolic.expr')).write_text(str(expr))
 regs=sorted([x for x in expr.free_symbols if str(x).startswith('R_')],key=str)
 print(name,'regularized symbols',len(regs),'terms',len(s.Add.make_args(expr)))
 byweight={}
 for x in regs:byweight.setdefault(len(str(x).split('_'))-1,[]).append(x)
 print({w:len(v) for w,v in byweight.items()})
