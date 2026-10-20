"""Correlated low-input propagation and two-quoted-error box sensitivity.
EFM errors are estimates, NOT statistical confidence intervals.
The box extrema sample dimension intervals (not interval-arithmetic certification).
"""
import json,copy,itertools,time
import numpy as np
from pathlib import Path
from spectrum import get_rows,LOW,S,E
from kernels import Functional
BASE=Path(__file__).resolve().parent

def set_low(rows,key,val):
 rows=copy.deepcopy(rows);S1=val if key=='S' else S;E1=val if key=='E' else E;ct=val if key=='ct' else LOW['ct'][0]
 for p in rows:
  if p['ell']==0 and p['Delta']<1:
   if key=='S':p['Delta']=val
   if key=='sse':p['f']=val
  if p['ell']==0 and 1<p['Delta']<2:
   if key=='E':p['Delta']=val
   if key=='sse':p['f']=val
   if key=='eee':p['h']=val
  if p['ell']==2 and p['Delta']==3:
   p['f']=S1*np.sqrt(3/(8*ct));p['h']=E1*np.sqrt(3/(8*ct))
 return rows,S1,E1

def globals_run(keys=None):
 rows=get_rows();fn=Functional(level=20,nr=80,na=80);central=fn.evaluate(rows);out=[]
 for key,(v,e) in LOW.items():
  if keys and key not in keys:continue
  vals=[]
  for sign in [-1,1]:
   rs,ss,ee=set_low(rows,key,v+sign*2*e)
   f=fn if key not in ['S','E'] else Functional(S=ss,E=ee,level=20,nr=80,na=80)
   vals.append(f.evaluate(rs))
  out.append(dict(parameter=key,C1_plus_minus_2error=[q['C1'] for q in vals],
   one_error_effect=(vals[1]['C1']-vals[0]['C1'])/4,
   a_plus_minus_2error=[q['a'] for q in vals],b_plus_minus_2error=[q['b'] for q in vals]))
  print(key,out[-1]['one_error_effect'],flush=True)
 target=BASE/'global_input_results.json'
 prior=json.load(open(target))['global_inputs'] if target.exists() else []
 out=[r for r in prior if r['parameter'] not in {p['parameter'] for p in out}]+out
 json.dump(dict(central=central,global_inputs=out),open(target,'w'),indent=2)

def box_run():
 rows=get_rows();fn=Functional(level=20,nr=80,na=80);central=fn.evaluate(rows);C=central['C1'];out=[]
 for p,pc in zip(rows,central['parts']):
  # Low inputs are varied coherently by globals_run().
  if p['Delta']<2 or (p['Delta']==3 and p['ell']==2):continue
  k0=np.array(pc['kernel']);v0=np.array([pc['contribution_b'],pc['contribution_a']]);poss=[]
  for nd in [-2,-1,0,1,2] if p['Delta_error'] else [0]:
   k=fn.block_kernel(p['Delta']+nd*p['Delta_error'],p['ell'],p['sector'])
   fvals=[p['f']-2*p['f_error'],p['f']+2*p['f_error']]
   if fvals[0]<=0<=fvals[1]:fvals.append(0.)
   for f in fvals:
    for sh in [-1,1] if p['sector']=='even' else[0]:
     h=p.get('h',0)+sh*2*p.get('h_error',0)
     w=np.array([f*f,f*h if p['sector']=='even' else f*f])
     d=k*w-v0;poss.append([float(d[0]),float(d[1]-C*d[0])])
  poss=np.array(poss)
  out.append(dict(name=p['name'],delta_b_min=float(poss[:,0].min()),delta_b_max=float(poss[:,0].max()),delta_F_min=float(poss[:,1].min()),delta_F_max=float(poss[:,1].max())))
 gr=json.load(open(BASE/'global_input_results.json'))['global_inputs']
 for q in gr:
  bb=np.array(q['b_plus_minus_2error'])-central['b'];aa=np.array(q['a_plus_minus_2error'])-central['a'];ff=aa-C*bb
  out.append(dict(name=q['parameter'],delta_b_min=float(bb.min()),delta_b_max=float(bb.max()),delta_F_min=float(ff.min()),delta_F_max=float(ff.max())))
 dblo=sum(p['delta_b_min'] for p in out);dbhi=sum(p['delta_b_max'] for p in out)
 Flo=sum(p['delta_F_min'] for p in out);Fhi=sum(p['delta_F_max'] for p in out)
 result=dict(central=central,two_error_box=dict(delta_b_min=dblo,delta_b_max=dbhi,delta_F_min=Flo,delta_F_max=Fhi,C1_min=C+Flo/(central['b']+dblo),C1_max=C+Fhi/(central['b']+dblo)),parts=out,status='sampled sensitivity envelope; EFM input errors and independence boxes are assumptions; not a confidence interval')
 json.dump(result,open(BASE/'input_box_results.json','w'),indent=2);print(result['two_error_box'],flush=True)
if __name__=='__main__':
 import sys
 if len(sys.argv)<2 or sys.argv[1]=='global':globals_run(sys.argv[2:] or None)
 else:box_run()
