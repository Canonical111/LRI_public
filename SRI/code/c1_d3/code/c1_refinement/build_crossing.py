"""Build numerical affine outer approximations, retaining nonlinear pads.
No interval certificate: dimension intervals are sampled. All input variables
are scaled so [-1,1] is twice the source's quoted error.
"""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import sys,json,copy,time
from pathlib import Path
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE.parent/'c1_precision'))
import numpy as np
from scipy.special import gammaln
from spectrum import get_rows,S,E,LOW
from kernels import cb,crossing_rows
from complete_input_errors import set_low

def block(p,z,level=32):
 l=p['ell']; fac=np.exp(gammaln(l+1)-gammaln(l+.5)+gammaln(.5))
 da,db=(0,0) if p['sector']=='even' else(E-S,S-E)
 return fac*cb.Block(p['Delta'],l,level,da,db)(z)

def rowval(p,g,gt,z):
 if p['sector']=='even':
  ds=abs(z)**(-2*S)*g-abs(1-z)**(-2*S)*gt
  de=abs(z)**(-2*E)*g-abs(1-z)**(-2*E)*gt
  return np.array([p['f']**2*ds,p['h']**2*de,-p['f']*p['h']*abs(1-z)**(-2*S)*gt])
 return np.array([np.zeros(len(z)),np.zeros(len(z)),p['f']**2*abs(z)**(-S-E)*g])

def residual(rows,z,level=32,S=S,E=E):
 r=crossing_rows(rows,z,level,S,E)
 return np.array([np.array(r[k]['direct'])-np.array(r[k]['crossed']) for k in ['sigma','epsilon','mixed']])

def main(level=32):
 rows=get_rows(); xs=np.linspace(.15,.49,35); xo=np.linspace(.64,.85,15)
 grid=np.array([x+1j*y for x in np.linspace(.2,.8,7) for y in [0,.12,.24,.36,.48,.6]])
 z=np.r_[xs,xo,grid]; nz=len(z)
 d0=residual(rows,z,level);J=[];names=[];params=[];pad=np.zeros_like(d0)
 errs=json.load(open(BASE.parent/'c1_precision/analysis_results.json'))
 ce={p['name']:p for p in errs['input_error_linearization']}
 glob=json.load(open(BASE.parent/'c1_precision/global_input_results.json'))['global_inputs']
 ge={p['parameter']:p['one_error_effect'] for p in glob}
 obj=[]
 for i,p in enumerate(rows):
  if p['Delta']<2 or (p['ell']==2 and p['Delta']==3):continue
  g=block(p,z,level);gt=block(p,1-z,level) if p['sector']=='even' else g*0
  v0=rowval(p,g,gt,z); derivatives={}
  for k in ['f','h','Delta'] if p['sector']=='even' else ['f','Delta']:
   if not p.get(k+'_error',0):continue
   e=2*p[k+'_error']; pp=dict(p);pm=dict(p);pp[k]+=e;pm[k]-=e
   if k=='Delta':
    gp=block(pp,z,level);gm=block(pm,z,level)
    gtp=block(pp,1-z,level) if p['sector']=='even' else gt
    gtm=block(pm,1-z,level) if p['sector']=='even' else gt
    dj=(rowval(pp,gp,gtp,z)-rowval(pm,gm,gtm,z))/2
   else:dj=(rowval(pp,g,gt,z)-rowval(pm,g,gt,z))/2
   J.append(dj);names.append(p['name']+':'+k);params.append(dict(row=i,key=k,scale=e));derivatives[k]=dj
   obj.append(2*ce[p['name']]['error_effect_'+k])
  # Sum per-family sampled absolute nonlinear errors, padded by factor 1.5.
  rp=np.zeros_like(d0)
  for nd in [-1,-.5,0,.5,1] if p['Delta_error'] else [0]:
   pd=dict(p,Delta=p['Delta']+nd*2*p['Delta_error'])
   gd=block(pd,z,level);gtd=block(pd,1-z,level) if p['sector']=='even' else gt
   for nf in [-1,0,1]:
    for nh in [-1,0,1] if p['sector']=='even' else [0]:
     pq=dict(pd,f=p['f']+nf*2*p['f_error'])
     if p['sector']=='even':pq['h']=p['h']+nh*2*p['h_error']
     pred=v0.copy()
     for k,x in [('Delta',nd),('f',nf),('h',nh)]:pred+=x*derivatives.get(k,0)
     rp=np.maximum(rp,abs(rowval(pq,gd,gtd,z)-pred))
  pad+=1.5*rp
  if i%10==0:print('row',i,'of',len(rows),flush=True)
 for key,(v,e) in LOW.items():
  vals=[]
  for s in [-1,1]:
   rr,ss,ee=set_low(rows,key,v+s*2*e)
   vals.append(residual(rr,z,level,S=ss,E=ee))
  dj=(vals[1]-vals[0])/2
  J.append(dj);names.append('global:'+key);params.append(dict(global_key=key,scale=2*e));obj.append(2*ge[key])
  pad+=2*abs((vals[1]+vals[0])/2-d0)
 J=np.moveaxis(np.array(J),0,-1)
 # Conservative numerical floor for near cancellations. Not a proof of global errors.
 pad+=2e-10*(1+abs(d0))
 np.savez_compressed(BASE/f'basis_L{level}.npz',z=z,xs=xs,xo=xo,d0=d0,J=J,pad=pad,obj=np.array(obj))
 json.dump(dict(names=names,parameters=params,level=level,npoints=nz,nparams=len(names),
  status='Sampled numerical affine remainder; no interval arithmetic'),open(BASE/f'basis_L{level}.json','w'),indent=2)
 print('finished',nz,len(names),'maxpad',pad.max(axis=1),flush=True)
if __name__=='__main__':main(int(sys.argv[1]) if len(sys.argv)>1 else 32)
