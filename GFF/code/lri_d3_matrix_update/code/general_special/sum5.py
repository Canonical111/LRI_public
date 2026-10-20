import json,sympy as s
from pathlib import Path
root=Path(__file__).parent
A,R,V,U,N,M,Q,P4,P5,Z,K,X=s.symbols('A R V U N M Q P4 P5 Z K X')
loc={str(x):x for x in [A,R,V,U,N,M,Q,P4,P5,Z,K,X]}
sub={s.Symbol('v1'):R+s.Symbol('j1'),s.Symbol('v2'):V-s.Symbol('j2'),s.Symbol('u2'):U,
     s.Symbol('m0'):s.Symbol('j0')+s.Symbol('v0')-s.Symbol('w0')+N,
     s.Symbol('v3'):X+s.Symbol('j3')}
rows=json.loads((root/'rows_5_0_129.json').read_text())
b=sum(s.sympify(x['wb'])*s.sympify(x['r'],locals=loc) for x in rows)
c=sum(s.sympify(x['wc'])*s.sympify(x['r'],locals=loc) for x in rows)
D=s.expand((3*c-b).subs(sub))
out4=json.loads((root/'sum4.json').read_text())
b4=s.sympify(out4['b4'],locals=loc);c4=s.sympify(out4['c4'],locals=loc)
b3=6*Q+s.Rational(87,4)*A**2-s.Rational(9,4)*R+M
c3=s.Rational(7,2)*A**2-R/2+M/3
# Exclude P4 contribution at this stage, to handle wheel sector separately.
rest=s.expand(336*A**4-60*A**2*b3+108*A**2*c3+b3**2-3*b3*c3-10*A*(b4+6*P4)+24*A*c4+D)
print('rows',len(rows));print('D5rem',D,flush=True);print('729_C5rest',rest,flush=True)
(root/'sum5.json').write_text(json.dumps({'row_count':len(rows),'D5rem':str(D),'729C5rest':str(rest),'remaining_symbols':sorted(map(str,rest.free_symbols))},indent=2))
