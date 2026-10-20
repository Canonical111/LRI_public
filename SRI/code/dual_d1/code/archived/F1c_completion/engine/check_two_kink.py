#!/usr/bin/env python3
from pathlib import Path
from math import comb
import json
import sympy as s
from read_expression import load
ROOT=Path(__file__).resolve().parent
r,e,ell=s.symbols('r e ell',positive=True)
L=s.Symbol('ell')
insertions={'base':1,'v':-2*s.log(r),'d':-s.log(r)**2,
'vd':2*s.log(r)**3-s.log(r)**2,'vv':4*s.log(r)**2,
'vvd':4*s.log(r)**3-4*s.log(r)**4}
out={}
for name,ins in insertions.items():
 primitive=s.integrate((1-r)/r*ins,r)
 expression=s.expand(primitive.subs(r,1)-primitive.subs(r,e))
 finite=s.Add(*(term for term in s.Add.make_args(expression)
   if term.as_powers_dict().get(e,s.S.Zero)==0)).subs(s.log(e),L).expand()
 expected=load(ROOT/'series'/f'Q2_{name}_p0.expr')
 out[name]={'polynomial':str(finite),'exact_equal':s.expand(finite-expected)==0}
assert all(v['exact_equal'] for v in out.values())
target=ROOT.parent/'verification'/'Q2_elementary.json'
target.parent.mkdir(exist_ok=True);target.write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
