"""Additional non-fit diagnostics and reproducibility checks from saved replicates."""
import json,hashlib,sys
import numpy as np
from pathlib import Path
from final_analysis import summarize,load,K,W
from analysis import F,jacobians

def coefficient_blocks(text):
 import re
 pat=r'(?<!\\)\\begin\{(equation\*?|align\*?|gather\*?|multline\*?|eqnarray\*?|displaymath)\}[\s\S]*?\\end\{\1\}|(?<!\\)\\\[[\s\S]*?(?<!\\)\\\]'
 return [m.group(0) for m in re.finditer(pat,text)]

if __name__=='__main__':
 out={};tags=tuple(sys.argv[1:]) or ('prod_a','prod_b')
 for d in (2,3):
  j=summarize(d,tags);means={int(k):np.array(v)for k,v in j['pooled_jet_means'].items()}
  J=jacobians(d,means)
  # First-order variance comparison to direct deterministic resampling of replicate means.
  raw={t:load(d,t)[1]for t in tags};rng=np.random.default_rng(614209+d)
  estimates=[]
  for b in range(4096):
   mm={L:sum(a[L][rng.integers(0,len(a[L]),len(a[L]))].mean(0)/len(tags) for a in raw.values())for L in range(3,7)}
   v=F[d](mm)[6]
   if d==2:v+=K['mean']+rng.normal(0,K['se'])
   estimates.append(v)
  x=np.array(estimates)
  vcov=sum(J[L]@np.array(j['pooled_jet_covariances'][str(L)])@J[L].T for L in range(3,7))
  if d==2:vcov[6,6]+=K['se']**2
  # A separate Lagrange evaluation from the same jets checks the fixed-point iteration.
  from analysis import base_module
  b2=base_module(d).B2
  jetsb={1:np.array([3.]),2:b2};jetsc={1:np.array([1.]),2:b2/6}
  for L,a in means.items():k=7-L;jetsb[L]=a[:k];jetsc[L]=a[k:]
  # 2-variable truncation, using only finite convolutions (g degree and eps degree).
  N=7
  B=np.zeros((N,N));G=np.zeros((N,N));B[0,0]=3
  for L,v in jetsb.items():
   if L>=2:B[L-1,:len(v)]=v
  for L,v in jetsc.items():G[L-1,:len(v)]=L*v
  def mul(a,b):
   c=np.zeros_like(a)
   for i in range(N):
    for k in range(N-i):c[i+k]+=np.convolve(a[i],b[k])[:N]
   return c
  H=B/3;H[0,0]-=1;ans=np.zeros(N);ans[0]=d/2;ans[1]=-.5
  import math
  for n in range(1,N):
   power=np.zeros_like(H);power[0,0]=1;inv=power.copy()
   for k in range(1,N):power=mul(power,H);inv+=((-1)**k*math.comb(n+k-1,k))*power
   prod=mul(G,inv)/(n*3**n)
   for eps_order in range(N-n):ans[n+eps_order]+=prod[n-1,eps_order]
  if d==2:ans[6]+=K['mean']
  out[str(d)]={'bootstrap_resamples':4096,'bootstrap_se':float(x.std(ddof=1)),'delta_method_se':j['sampling_standard_error'],'bootstrap_mean_shift':float(x.mean()-j['C6']),'bootstrap_percentile_2_5_97_5':np.quantile(x,[.025,.975]).tolist(),'interpretation':'Diagnostic, approximate; not a rigorous confidence interval. Common 2D known-sector uncertainty sampled once per full bootstrap.','independent_finite_Lagrange_coefficients':ans.tolist(),'max_Lagrange_difference':float(max(abs(ans-np.array(j['coefficients'])))),'variance_reassembly_difference':float(max(abs(vcov-np.array(j['coefficient_covariance'])).flat))}
 (W/f'verification/extra_precision_checks_{"_".join(tags)}.json').write_text(json.dumps(out,indent=2));print(out)
