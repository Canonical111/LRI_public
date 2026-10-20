import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import sys,json,copy
from pathlib import Path
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE.parent/'c1_precision'))
import numpy as np
from scipy.optimize import linprog
from spectrum import get_rows,S,E,LOW
from build_crossing import residual
from crossing_envelope import Envelope

def actual(env,x):
 rows=get_rows();low={k:v[0] for k,v in LOW.items()}
 for p,t in zip(env.meta['parameters'],x):
  if 'global_key' in p:low[p['global_key']]+=t*p['scale']
  else:rows[p['row']][p['key']]+=t*p['scale']
 for p in rows:
  if p['ell']==0 and p['Delta']<1:p.update(Delta=low['S'],f=low['sse'])
  if p['ell']==0 and 1<p['Delta']<2:p.update(Delta=low['E'],f=low['sse'],h=low['eee'])
  if p['ell']==2 and p['Delta']==3:p.update(f=low['S']*np.sqrt(3/(8*low['ct'])),h=low['E']*np.sqrt(3/(8*low['ct'])))
 return residual(rows,env.z,40,S=low['S'],E=low['E'])

def main():
 env=Envelope(level=40);lp=np.load(BASE/'final_8_7_pad1_lp.npz');env.A=lp['A'];env.B=lp['B'];rg=np.random.default_rng(6087)
 bounds=np.array(env.bnds);cases=[]
 for i in range(20):cases.append(('interior',bounds[:,0]+(bounds[:,1]-bounds[:,0])*rg.uniform(size=len(env.obj))))
 for i in range(12):cases.append(('corners',bounds[:,0]+(bounds[:,1]-bounds[:,0])*rg.integers(0,2,size=len(env.obj))))
 for sign in [-1,1]:
  r=linprog(sign*env.obj,A_ub=env.A,b_ub=env.B,bounds=env.bnds,method='highs')
  if not r.success:raise RuntimeError(r.message)
  cases.append(('LP_objective_extremum',r.x))
 out=[]
 for i,(kind,x) in enumerate(cases):
  err=abs(actual(env,x)-env.d0-env.J@x);ratio=err/env.pad
  out.append(dict(kind=kind,max_actual_over_allowance=float(ratio.max()),absolute_error_by_correlator=err.max(axis=1).tolist()))
  if i%5==0:print(i,out[-1],flush=True)
 if max(q['max_actual_over_allowance'] for q in out)>=1:
  raise RuntimeError('Sampled nonlinear crossing remainder exceeds chosen allowance')
 json.dump(dict(seed=6087,cases=out,max_ratio=max(q['max_actual_over_allowance'] for q in out),status='Finite nonlinear tests, not a uniform certificate'),open(BASE/'nonlinear_crossing_validation.json','w'),indent=2)
if __name__=='__main__':main()
