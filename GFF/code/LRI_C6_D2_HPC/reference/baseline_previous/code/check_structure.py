"""Exact tests of compressed sector selection; normalization and graph coverage."""
import itertools,json,sys,hashlib,math
from fractions import Fraction as Q
from pathlib import Path
import mpmath as mp
import numpy as np
from run_precision import W,graph_ids
out={'sector_selection':[],'gamma_normalization':[],'graph_coverage':[]}
for E in (3,4,5,6):
 alpha={s:Q(s.bit_count()+1+(s%5),7)for s in range(1,(1<<E)-1)}
 dp={0:Q(1)}
 for s in range(1,1<<E):dp[s]=sum(dp[s^(1<<j)]for j in range(E)if s>>j&1)/(1 if s==(1<<E)-1 else alpha[s])
 def interval(order):
  s=(1<<E)-1;lo=Q(0);width=Q(1);prod=Q(1)
  for j in order:
   tot=sum(dp[s^(1<<k)]for k in range(E)if s>>k&1)
   lo+=width*sum(dp[s^(1<<k)]for k in range(j)if s>>k&1)/tot
   width*=dp[s^(1<<j)]/tot;s^=1<<j
   if s:prod/=alpha[s]
  assert width==prod/dp[(1<<E)-1]
  return lo,width
 def invert(u):
  s=(1<<E)-1;o=[]
  while s:
   tot=sum(dp[s^(1<<k)]for k in range(E)if s>>k&1);rem=u*tot
   for j in range(E):
    if not(s>>j&1):continue
    p=dp[s^(1<<j)]
    if rem<p:
     o.append(j);u=rem/p;s^=1<<j;break
    rem-=p
  return tuple(o)
 prev=Q(0)
 for order in itertools.permutations(range(E)):
  lo,width=interval(order);assert lo==prev;assert invert(lo+width/2)==order;prev=lo+width
 assert prev==1
 out['sector_selection'].append({'E':E,'permutations':math.factorial(E),'exact_cover_probability':'1','exact_interval_reconstruction':True,'telescoping_DP_probability':True})
mp.mp.dps=70
for d in (2,3):
 lines=(W/f'inputs/gamma_d{d}.txt').read_text().splitlines()
 for L,line in zip(range(2,7),lines):
  vals=list(map(mp.mpf,line.split()));norm=vals[1];logs=vals[2:]
  q=mp.mpf(d)/4
  def logG(z):return mp.loggamma(1+L*z/2)+L*(mp.loggamma(d/2+z/2)-mp.loggamma(1+z/2))-2*L*mp.loggamma(q+z/4)
  # Independent differentiation verifies the logarithmic Taylor normalization.
  rr=max(abs(mp.diff(logG,0,k)/mp.factorial(k)-logs[k])for k in range(1,5))
  nn=abs(2*(-1)**(L+1)*mp.exp(logG(0))-norm)
  assert max(rr,nn)<mp.mpf('1e-53')
  out['gamma_normalization'].append({'d':d,'L':L,'max_abs_error':mp.nstr(max(rr,nn),15)})
for L in range(3,7):
 p=W/'baseline/lri_C6_d3_complete_update/inputs'/f'forest_L{L}.txt';_,rows=graph_ids(p)
 out['graph_coverage'].append({'L':L,'finite_kernels':len(rows),'unique_ids':len(set(r[0]for r in rows)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(W/'verification/structure_checks.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
