#!/usr/bin/env python3
"""Extract the finite constant directly, rather than expanding unnecessary logarithms."""
from pathlib import Path
import json,sys,time
import sympy as s
from asymptotic_gpl import rseries,big,shiftcoef,L
from read_expression import load
ROOT=Path(__file__).resolve().parent
def finite(rows,N):
 terms={};contrib=[]
 def flush():
  for x in s.Add.make_args(s.expand(s.Add(*contrib))):
   c,b=x.as_coeff_Mul(rational=True);terms[b]=terms.get(b,s.S.Zero)+c
  contrib.clear()
 for word,logs,rat in rows:
  # Factors log(epsilon*1) have zero constant at log epsilon=0.
  if 1 in logs:continue
  scalar=s.prod(s.log(k) for k in logs)
  if scalar==0:continue
  rs=rseries(rat,0)
  val=0
  for pp,cc in rs.items():
   d=-pp
   for j in range(d+1):
    polynomial=big(tuple(word),j)
    if not polynomial:continue
    for k in range(min(s.degree(polynomial,L),d-j)+1):
     sc=shiftcoef(N,j,k,d)
     if sc:
      val+=cc*sc*s.factorial(k)*polynomial.coeff(L,k)
  contrib.append(scalar*val)
  if len(contrib)>=48:flush()
 if contrib:flush()
 return s.Add(*(c*b for b,c in terms.items() if c))
for tag in sys.argv[1:]:
 st=time.time();rows=json.loads((ROOT/(tag+'_negative.json')).read_text())
 ans=finite(rows,3)
 out=ROOT/'scalars'/f'{tag}_p0_l0.expr'
 out.parent.mkdir(exist_ok=True);out.write_text(s.sstr(ans,order='none'))
 prior=ROOT/'series'/f'{tag}_p0.expr'
 same=None
 if prior.exists():
  same=s.expand(ans-s.expand(load(prior)).coeff(s.Symbol('ell'),0))==0
  assert same
 print(tag,'finite terms',len(s.Add.make_args(ans)),'agrees_full_extractor',same,
       'seconds',time.time()-st,flush=True)
