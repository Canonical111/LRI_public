"""Independent numerical checks of the refinement's pads and radial normalization."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import sys,json,copy
from pathlib import Path
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE.parent/'c1_precision'))
import numpy as np
from scipy.special import roots_legendre,eval_legendre,eval_chebyt
from spectrum import get_rows,S,E,LOW
from kernels import cb,Functional,crossing_rows
from build_crossing import residual
from crossing_envelope import Envelope
from runtime_config import OBJECTIVE_ALLOWANCE

def positive_radial():
 N=14;eta,w=roots_legendre(90);a=E-S
 L=np.zeros((N+1,len(eta)));q=np.zeros_like(L);q[0]=1
 for n in range(1,N+1,2):L[n]=4*a*eval_chebyt(n,eta)/n
 for n in range(1,N+1):q[n]=sum(k*L[k]*q[n-k] for k in range(1,n+1))/n
 out=[]
 for delta,ell in [(S,0),(4.180305,2),(4.63804,3),(7.,0),(7.,1),(7.,3),(7.73,6),(10.,5),(12.,8)]:
  c=cb.Block(delta,ell,N,E-S,S-E).coefs
  P=np.array([eval_legendre(j,eta) for j in range(c.shape[1])]);g=c@P
  prod=np.array([sum(q[k]*g[n-k] for k in range(n+1)) for n in range(N+1)])
  # Project into Legendre polynomials. Their normalized coefficients must be nonnegative.
  proj=prod@(P*w).T*(2*np.arange(len(P))+1)/2
  mn=float(proj.min());scale=max(1,float(proj.max()))
  out.append(dict(Delta=delta,ell=ell,min_coefficient=mn,relative_negative=mn/scale))
  if mn < -1e-9*scale:raise RuntimeError('Normalized radial positivity check failed')
 return out

def objective_pads():
 env=Envelope(level=40);names=env.meta['names'];coef=dict(zip(names,env.obj));rows=get_rows();fn=Functional(level=24,nr=64,na=64)
 data=json.load(open(BASE.parent/'c1_precision/analysis_results.json'))['central'];C=data['C1'];b=data['b'];out=[]
 for p,pc in zip(rows,data['parts']):
  if p['Delta']<2 or (p['ell']==2 and p['Delta']==3):continue
  initial=(pc['contribution_a']-C*pc['contribution_b'])/b
  mx=0.;witness=None
  for nd in np.linspace(-1,1,9) if p['Delta_error'] else [0]:
   K=fn.block_kernel(p['Delta']+nd*2*p['Delta_error'],p['ell'],p['sector'])
   for nf in [-1,0,1]:
    for nh in [-1,0,1] if p['sector']=='even' else [0]:
     f=p['f']+nf*2*p['f_error'];h=p.get('h',0)+nh*2*p.get('h_error',0)
     exact=(K[1]*(f*h if p['sector']=='even' else f*f)-C*K[0]*f*f)/b-initial
     linear=sum(x*coef.get(p['name']+':'+k,0) for k,x in [('f',nf),('h',nh),('Delta',nd)])
     r=abs(exact-linear)
     if r>mx:mx=r;witness=[float(nd),nf,nh]
  out.append(dict(name=p['name'],sampled_max_abs_remainder=mx,witness=witness))
 # Low-input remainder obtained from independently saved full evaluations.
 glo=json.load(open(BASE.parent/'c1_precision/global_input_results.json'))['global_inputs'];low=0.
 for p in glo:
  f=(np.array(p['a_plus_minus_2error'])-C*np.array(p['b_plus_minus_2error']))/b
  low+=float(np.max(abs(f-np.array([-1,1])*coef['global:'+p['parameter']])))
 total=sum(q['sampled_max_abs_remainder'] for q in out)+low
 return dict(rows=out,low_input_remainder=low,total_sampled_remainder=total,allowance_used=OBJECTIVE_ALLOWANCE,ratio_to_allowance=total/OBJECTIVE_ALLOWANCE,
  numerical_quad=dict(level=24,nr=64,na=64),continuous_dimension_sampling='nine points over each two-error interval')

def basis_comparison():
 a=np.load(BASE/'basis_L32.npz');b=np.load(BASE/'basis_L40.npz')
 return {k:float(np.max(abs(a[k]-b[k]))) for k in ['d0','J','pad']}

if __name__=='__main__':
 mode=sys.argv[1] if len(sys.argv)>1 else 'radial'
 if mode=='radial':out=dict(radial_positive=positive_radial(),descendant_order_comparison=basis_comparison())
 else:out=objective_pads()
 json.dump(out,open(BASE/f'validation_{mode}.json','w'),indent=2);print(out if mode=='radial' else {k:v for k,v in out.items() if k!='rows'},flush=True)
