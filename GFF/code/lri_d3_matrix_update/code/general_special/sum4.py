import json,sympy as s
from pathlib import Path
root=Path(__file__).parent
rows=json.loads((root/'rows_4_0_27.json').read_text())
b=sum(s.sympify(x['wb'])*s.sympify(x['r'],locals={'Q':s.Symbol('Q')}) for x in rows);c=sum(s.sympify(x['wc'])*s.sympify(x['r'],locals={'Q':s.Symbol('Q')}) for x in rows)
A,R,V,U,N,M,Q,P=s.symbols('A R V U N M Q P4')
sub={s.Symbol('v1'):R+s.Symbol('j1'),s.Symbol('v2'):V-s.Symbol('j2'),s.Symbol('u2'):U,s.Symbol('m0'):s.Symbol('j0')+s.Symbol('v0')-s.Symbol('w0')+N}
b=s.expand(b.subs(sub))-6*P;c=s.expand(c.subs(sub));D=s.expand(3*c-b)
C4=s.expand((D-51*A**3+9*A*R-48*A*Q-2*A*M)/243)
for key,v in [('b4',b),('c4',c),('D4',D),('C4',C4)]:print(key,s.factor(v),flush=True)
(root/'sum4.json').write_text(json.dumps({key:str(v)for key,v in [('b4',b),('c4',c),('D4',D),('C4',C4)]},indent=2))
