#!/usr/bin/env python3
"""Exact checks of the displayed RG decomposition and retained certificate."""
from pathlib import Path
import json
import sympy as s
R=Path(__file__).resolve().parent
A,Q,K,L,P4,P5,G,p,z,l=s.symbols('A Q K L P4 P5 G pi zeta3 log2')
loc=dict(pi=p,log2=l,Catalan=G,Q=Q,K=K,zeta3=z,B4=P4)
rows=json.loads((R/'inputs/residue_certificate.json').read_text())
v=lambda x:s.sympify(x,locals=loc)
b3=6*Q+s.Rational(87,4)*A**2-3*p**2/4-4*p
c3=s.Rational(7,2)*A**2-p**2/6-4*p/3
b4=-6*P4-s.Rational(393,4)*A**3-54*A*Q+s.Rational(39,4)*A*p**2+16*A*p+s.Rational(165,4)*p**3+12*p**2+24*p+1119*z
c4=-s.Rational(127,8)*A**3-3*A*Q+s.Rational(17,8)*A*p**2+s.Rational(8,3)*A*p+s.Rational(57,8)*p**3+4*p**2+8*p+s.Rational(387,2)*z
rem=-s.Rational(16347,64)*A**4+A**2*(-s.Rational(1179,4)*Q+s.Rational(1053,32)*p**2+45*p)+A*(s.Rational(3657,16)*p**3+24*p**2+48*p+s.Rational(24843,4)*z)-24*K+Q*(894*G+s.Rational(343,4)*p**2+24*p)-s.Rational(95,64)*p**4-p**3
checks={
'b4_certificate':s.expand(b4.subs(A,p+4*l)-(sum(v(r['wb'])*v(r['r']) for r in rows['4'])-6*P4)),
'c4_certificate':s.expand(c4.subs(A,p+4*l)-sum(v(r['wc'])*v(r['r']) for r in rows['4'])),
'D5_remainder_certificate':s.expand(rem.subs(A,p+4*l)-sum((3*v(r['wc'])-v(r['wb']))*v(r['r']) for r in rows['5']))}
R5=(336*A**4-60*A**2*b3+108*A**2*c3+b3**2-3*b3*c3-10*A*b4+24*A*c4)/729
D5=-24*P5-63*Q**2-54*A*P4-9*L+rem
H=2*p**2/3+8*G
closed=(-1536*(P5+K)+384*A*P4-576*L-1728*Q**2+48*Q*(15*A**2+149*H+7*p**2)-15*A**4-30*A**2*p**2-828*A*p**3-21456*A*z-83*p**4)/46656
checks['RG_assembly_equals_original_C5']=s.expand(R5+D5/729-closed)
assert all(x==0 for x in checks.values()),checks
out={'certificate_rows_4':len(rows['4']),'certificate_rows_5':len(rows['5']),'checks':{k:str(v)for k,v in checks.items()},'all_exact':True}
(R/'records/symbolic_audit.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
