import sympy as s,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
read=lambda n:s.sympify((ROOT/(n+'_symbolic.expr')).read_text())
a,p,A,E,c,f,q,b,G,k=[read(n+'_check') for n in ['a','p','A','E','c','f','q','b','G','k']]
V=read('V');R,L,M,N,J=[read(n) for n in ['R','L','M','N','J']]
B=A/8-E/2-G/4+(a*a-a*b)/8+a*c/16-a*p/2-b*c/8+c*c/64-c*f/32-c*p/8-f/32-k/32-q/8
B=s.expand(B)
C6=s.expand(B+2*V+R+3*J/8-L/8+M/4+N/16)
# All old and new inputs are exact regulated-period expressions.
for n,ex in [('B_old',B),('C6',C6),('T3',C6/4)]:
 ex=s.expand_log(ex,force=True).expand()
 (ROOT/(n+'_symbolic.expr')).write_text(str(ex))
 print(n,'terms',len(s.Add.make_args(ex)),'symbols',len(ex.free_symbols),flush=True)
regs={str(x):len(str(x).split('_'))-1 for x in C6.free_symbols if str(x).startswith('R_')}
print('period weights',sorted(set(regs.values())),flush=True)
print('zero-letter periods',sum('_0' in x for x in regs),flush=True)
