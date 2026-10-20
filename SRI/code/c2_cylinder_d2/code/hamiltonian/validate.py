#!/usr/bin/env python3
"""Regenerate finite-basis/finite-series checks. No proposed C2 is an input."""
from __future__ import annotations
import json,subprocess,sys,time,platform,os
from pathlib import Path
import numpy as np
ROOT=Path(__file__).parent

def block_test():
    from ising_basis import modes,spin_chiral
    from block_check import blocks
    N=20;rr=modes(2*N,True);nn=modes(2*N,False)
    er=np.array([sum(r)/2+1/16 for r in rr]);en=np.array([sum(n)/2 for n in nn])
    S=np.array([[spin_chiral(r,n) for r in rr] for n in nn]);rows=[]
    for u,v,w in [(.2,.3,.4),(.17*np.exp(.3j),.23*np.exp(-.4j),.29*np.exp(.2j))]:
      f=blocks(u,v,w)
      for ext in [(),(1,),(3,)]:
        h=sum(ext)/2;x=S[nn.index(ext)];left=x*u**(er-h);right=x*w**(er-h)
        for parity in [0,1]:
          jj=np.array([len(n)%2==parity for n in nn]);val=(S[jj]@left)@(v**(en[jj]-h)*(S[jj]@right))
          if ext==():idx=parity;base=u**(1/16)*w**(1/16)*v**(parity/2)
          elif ext==(1,):idx=2+1-parity;base=u**(-7/16)*w**(-7/16)*v**((parity-1)/2)
          else:idx=4+1-parity;base=u**(-23/16)*w**(-23/16)*v**((parity-3)/2)
          err=float(abs(val-base*f[idx]));rel=err/max(1,float(abs(val)))
          rows.append(dict(state=str(ext),parity=parity,absolute_error=err,scaled_error=rel,complex_arguments=bool(np.iscomplexobj(u))))
    assert max(x['scaled_error'] for x in rows)<1e-9
    return rows

def main():
    start=time.time();out={}
    for filename in ['checks.py','finite_shell_check.py','mixed_sequence.py','lowmemory.py']:
      print('CHECK',filename,flush=True)
      with open(ROOT/(filename+'.validation.log'),'w') as log:
        subprocess.run([sys.executable,str(ROOT/filename)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,env=dict(os.environ,OPENBLAS_NUM_THREADS='1'))
    d=json.loads((ROOT/'checks_results.json').read_text());out['finite_basis']=d
    d=json.loads((ROOT/'finite_shell_check.json').read_text());assert max(abs(x[k]) for x in d for k in ['difference_0chi','difference_2chi'])<1e-9;out['fourth_order_finite_shells']=d
    d=json.loads((ROOT/'mixed_sequence_checks.json').read_text());assert max(abs(x['error']) for x in d)<1e-9;out['mixed_convolution']=d
    d=json.loads((ROOT/'lowmemory_checks.json').read_text());assert max(d['filter_max_errors'])<1e-9;assert max(abs(x['error']) for x in d['sequence_checks'])<1e-8;out['low_memory_convolution']=d
    print('CHECK block generating functions',flush=True);out['complex_blocks']=block_test()
    from improved_regulator import planar_constants,curvature_thermal
    ct=[]
    for k in [1,2,3]:
      a=planar_constants(k,128);b=planar_constants(k,256);c=curvature_thermal(k,128);d=curvature_thermal(k,256)
      errs={key:abs(a[key]-b[key]) for key in ['ct','kappa']};errs['curvature']=abs(c['thermal_lambda_coefficient']-d['thermal_lambda_coefficient']);assert max(errs.values())<1e-8;ct.append(dict(order=k,quadrature_differences=errs))
    out['local_counterterms']=ct
    import scipy,sympy,mpmath
    out['environment']=dict(python=sys.version,numpy=np.__version__,scipy=scipy.__version__,sympy=sympy.__version__,mpmath=mpmath.__version__,platform=platform.platform())
    out['seconds']=time.time()-start;out['passed']=True
    (ROOT/'validation_results.json').write_text(json.dumps(out,indent=2));print('PASSED',out['seconds'],flush=True)
if __name__=='__main__':main()
