#!/usr/bin/env python3
from pathlib import Path
import sympy as s,json
from read_expression import load
import assemble_F1c as ac
ROOT=Path(__file__).resolve().parent
v,d=s.symbols('v d')
q,b,k,bb,l,h,e=(s.Function(n)(v,d) for n in ['q','b','k','bb','l','h','e'])
orig=-2*q*b-4*k*bb-l*h-2*k-4*v*s.diff(k,v)+2*v*e
derived=s.diff(orig,v,d)
jets=[(0,0),(1,0),(0,1),(1,1)]
qj={(i,j):ac.raw('Q2',i,j,0) for i,j in jets+[(2,0),(2,1)]}
e2j={(i,j):ac.raw('EQ2',i,j,0) for i,j in jets}
b5=dict(zip(jets,map(ac.beta,['b_check','G_check','R','Psi'])))
b3={(0,0):s.S.One,(1,0):ac.beta('a_check'),(0,1):ac.beta('p_check'),(1,1):ac.beta('E_check')}
h4=dict(zip(jets,(-ac.beta(n)/4 for n in ['c_check','f_check','q_check','M'])))
lj={(0,0):-2*qj[0,0]-4*qj[1,0]+2*e2j[0,0],
(1,0):-6*qj[1,0]-4*qj[2,0]+2*e2j[0,0]+2*e2j[1,0],
(0,1):-2*qj[0,1]-4*qj[1,1]+2*e2j[0,1],
(1,1):-6*qj[1,1]-4*qj[2,1]+2*e2j[0,1]+2*e2j[1,1]}
values={q:qj,b:b5,bb:b3,h:h4,l:lj,
 k:{(i,j):ac.K4(i,j) for i,j in jets+[(2,1)]},
 e:{(i,j):ac.EK4(i,j) for i,j in [(0,1),(1,1)]}}
subs={}
for fun,jet in values.items():
 for (i,j),z in jet.items():
  subs[s.diff(fun,v,i,d,j)]=z
direct=s.expand(derived.xreplace(subs).subs({v:1,d:0}))
expected=load(ROOT.parent/'data/Dct.expr')
residual=s.expand(direct-expected)
assert residual==0
print('Full symbolic differentiation versus mixed-jet assembly: exact zero')
out=ROOT.parent/'verification'/'independent_full_derivative.json'
out.write_text(json.dumps({'method':'differentiate the whole finite-response expression, then substitute full derivative jets','exact_residual':'0','used_rational_or_numerical_guess':False},indent=2))
