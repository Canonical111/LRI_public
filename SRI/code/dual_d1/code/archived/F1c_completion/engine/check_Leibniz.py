#!/usr/bin/env python3
"""Independent symbolic checks of every Leibniz factor and the explicit-v derivative."""
import sympy as s
from pathlib import Path
import json
v,d=s.symbols('v d');Q,B,K,b,L,h,E=(s.Function(x)(v,d) for x in ['Q','B','K','b','L','h','E'])
def prod(A,B):
 return s.diff(A,v,d)*B+s.diff(A,v)*s.diff(B,d)+s.diff(A,d)*s.diff(B,v)+A*s.diff(B,v,d)
checks={}
for name,A,B,co in [('Q_B',Q,B,-2),('K_b',K,b,-4),('L_h',L,h,-1)]:
 checks[name]=s.expand(s.diff(co*A*B,v,d)-co*prod(A,B))==0
lam=-2*K-4*v*s.diff(K,v)+2*v*E
prediction=-6*s.diff(K,v,d)-4*v*s.diff(K,v,2,d)+2*s.diff(E,d)+2*v*s.diff(E,v,d)
checks['lambda4_explicit_v']=s.expand(s.diff(lam,v,d)-prediction)==0
# Multiplicative mixed jet must agree with polynomial (dual-number) extraction.
q00,q10,q01,q11,b00,b10,b01,b11=s.symbols('q00 q10 q01 q11 b00 b10 b01 b11')
jetQ=q00+q10*v+q01*d+q11*v*d
jetB=b00+b10*v+b01*d+b11*v*d
target=q11*b00+q10*b01+q01*b10+q00*b11
checks['dual_number_product']=s.expand(jetQ*jetB).coeff(v,1).coeff(d,1)==target
assert all(checks.values()),checks
path=Path(__file__).resolve().parents[1]/'verification'/'Leibniz_checks.json'
path.parent.mkdir(exist_ok=True);path.write_text(json.dumps(checks,indent=2))
print(json.dumps(checks,indent=2))
