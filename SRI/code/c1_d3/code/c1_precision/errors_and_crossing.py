import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import json,math,time,copy
from pathlib import Path
import numpy as np
from spectrum import get_rows,LOW
from kernels import Functional,crossing_rows
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parent

def main():
  out={}; rows=get_rows();json.dump(rows,open(ROOT/'expanded_spectrum.json','w'),indent=2)
  with threadpool_limits(limits=1):
    fn=Functional(level=24,nr=100,na=100)
    res=fn.evaluate(rows);out['central']=res
    print('central',res['a'],res['b'],res['C1'],flush=True)
    error=[]
    C=res['C1'];b=res['b']
    for p,part in zip(rows,res['parts']):
        K=np.array(part['kernel'])
        # Change one input by its quoted error; exact OPE quadratic variation.
        if p['sector']=='even':
            df=(K[1]*p['h']-2*C*K[0]*p['f'])/b*p['f_error']
            dh=K[1]*p['f']/b*p['h_error']
            w=np.array([p['f']**2,p['f']*p['h']])
        else:
            df=2*K[1]*p['f']/b*p['f_error'];dh=0.;w=np.array([0.,p['f']**2])
        ed=p['Delta_error']
        if ed>0 and p['Delta']>2:
            dK=(fn.block_kernel(p['Delta']+ed,p['ell'],p['sector'])-fn.block_kernel(p['Delta']-ed,p['ell'],p['sector']))/2
            dC=(dK[1]*w[1]-C*dK[0]*w[0])/b
        else: dC=0.
        error.append(dict(name=p['name'],Delta=p['Delta'],ell=p['ell'],sector=p['sector'],error_effect_f=df,error_effect_h=dh,error_effect_Delta=dC,quadrature=math.sqrt(df*df+dh*dh+dC*dC)))
    error.sort(key=lambda p:p['quadrature'],reverse=True)
    out['input_error_linearization']=error
    out['independent_input_error_rss']=math.sqrt(sum(p['quadrature']**2 for p in error))
    out['input_error_l1_no_covariance']=sum(abs(p[k]) for p in error for k in ['error_effect_f','error_effect_h','error_effect_Delta'])
    print('errors',out['independent_input_error_rss'],out['input_error_l1_no_covariance'],flush=True)
    for x in error[:10]: print(x,flush=True)
    zs=[.3+.25j,.2+.5j,.5+.1j,.5+.5j,.7+.25j,.8+.5j]+[x+1j*y for x in [.3,.4,.6,.7] for y in [.0,.1,.2,.3,.4,.5]]
    out['crossing_z']=[[z.real,z.imag] for z in zs];out['crossing']=crossing_rows(rows,zs,level=28)
    for k,v in out['crossing'].items(): print('crossing',k,'max',max(abs(x) for x in v['relative']),'first',v['relative'][:6],flush=True)
    json.dump(out,open(ROOT/'analysis_results.json','w'),indent=2)
if __name__=='__main__':main()
