"""Full finite-cutoff checks using Taylor ODE, not cutoff fitting.
Scalar logs are distinguished between original and scaled coordinates.
"""
from pathlib import Path
from functools import lru_cache
import json,ast,time,sys
import mpmath as mp
import sympy as s
from evaluate_periods_gmp import evaluate
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'raw_engine'))
from finite_gpl_check import detrail

def main(target,eps='.1',dps=65):
 start=time.time();mp.mp.dps=dps;epsilon=mp.mpf(eps);T=1/epsilon-5;ell=mp.log(epsilon);Lt=mp.log(T)
 specs=[]
 if target=='Xvv':
  mm=json.loads((ROOT/'Q6_vv/manifest.json').read_text())
  for r in mm['blocks']:
   p=ROOT/'Q6_vv'/r['block'];assert (p/'result.json').exists(),p
   specs.append((p/'negative.json',mp.mpf(1),False))
 elif target=='XE':
  p=ROOT/'SEQ6_combined/b00';assert (p/'result.json').exists()
  specs.append((p/'negative.json',mp.mpf(1),True))
  specs.append((ROOT.parent/'raw_engine/EQ6_base_negative.json',-6*ell,False))
 else:raise ValueError(target)
 env={'e':epsilon,**{f'Z{k}':mp.zeta(k) for k in range(2,7)}}
 def ev(x):
  if isinstance(x,ast.Constant):return mp.mpf(x.value)
  if isinstance(x,ast.Name):return env[x.id]
  if isinstance(x,ast.UnaryOp):return -ev(x.operand) if isinstance(x.op,ast.USub) else ev(x.operand)
  if isinstance(x,ast.BinOp):
   a,b=ev(x.left),ev(x.right)
   if isinstance(x.op,ast.Add):return a+b
   if isinstance(x.op,ast.Sub):return a-b
   if isinstance(x.op,ast.Mult):return a*b
   if isinstance(x.op,ast.Div):return a/b
   if isinstance(x.op,ast.Pow):return a**b
  raise ValueError(ast.dump(x))
 @lru_cache(None)
 def coeff(text):return ev(ast.parse(text.replace('^','**'),mode='eval').body)
 @lru_cache(None)
 def pval(pol):
  L=s.Symbol('L');return mp.fsum(mp.mpf(int(c.p))/int(c.q)*Lt**i for (i,),c in s.Poly(pol,L).terms())
 sums={};rows_count=0;recs=[]
 for path,weight,scaled in specs:
  rr=json.loads(path.read_text());rows_count+=len(rr)
  for word,logs,c in rr:
   fac=weight*coeff(c)*mp.fprod(mp.log(k)+(0 if scaled else ell) for k in logs)
   if not fac:continue
   assert all(a<=0 for a in word)
   for w,p in detrail(tuple(-a for a in word)).items():sums[w]=sums.get(w,mp.mpf(0))+fac*pval(p)
  recs.append({'path':str(path),'rows':len(rr),'logs_scaled':scaled,'weight':str(weight)})
 print('FINITE_PREPARED',target,rows_count,len(sums),time.time()-start,flush=True)
 wanted=set(sums)-{()};vals=evaluate(wanted,dps=dps,R=mp.nstr(T,dps),ntaylor=210,nasym=-1,stepfrac='.3')
 vv={w:mp.mpf(str(v)) for w,v in vals.items()};vv[()]=mp.mpf(1)
 terms=[c*vv[w] for w,c in sums.items()];ans=mp.fsum(terms);cond=mp.fsum(map(abs,terms))/abs(ans)
 report={'target':target,'epsilon':eps,'value':mp.nstr(ans,dps-10),'dps':dps,'terms':rows_count,'ODE_words':len(sums),'absolute_sum_condition':mp.nstr(cond,20),'seconds':time.time()-start,'method':'convergent finite-argument hyperlogarithm ODE; no asymptotic subtraction or period table','interval_bound':False,'sources':recs}
 (ROOT/'data'/f'{target}_finite_check.json').write_text(json.dumps(report,indent=2));print(report,flush=True)
if __name__=='__main__':main(sys.argv[1])
