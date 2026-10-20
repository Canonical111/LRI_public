"""Independent deterministic two-dimensional check of the first power graph.
Analytically integrates its three external Schwinger parameters and radial ratio.
No graph sampler, forest monomial input, or RG output is used on the reference side.
"""
from pathlib import Path
import json,math,time
from scipy.integrate import quad
W=Path(__file__).resolve().parents[1]
def evaluate(tol):
 def outer(x):
  t=x*x
  def inner(v):
   D=1+v+t*v;S=1+t+t*v
   logarithm=1.25*math.log(t)+math.log(v)-1.5*math.log(S)-.75*math.log(D)
   loghyper=3*(math.log(2)-math.log1p(math.sqrt(t*v/(S*D))))
   return (-1.5+logarithm+loghyper)/D**1.5
  return quad(inner,0,1,epsabs=tol*.1,epsrel=tol*.1,limit=150)[0]
 # Six symmetric simplex sectors and t=x^2 remove the algebraic corner singularity.
 v,e=quad(outer,0,1,epsabs=tol,epsrel=tol,limit=150)
 return dict(b3_0=-4.0,b3_1=-24/math.pi*v,quadrature_error_estimate=24/math.pi*e,tolerance=tol)
if __name__=='__main__':
 st=time.time();runs=[evaluate(2e-8),evaluate(2e-10)]
 out=dict(status='passed',reference='Analytically integrated external/radial variables, independent deterministic 2D simplex quadrature',runs=runs,difference=abs(runs[0]['b3_1']-runs[1]['b3_1']),seconds=time.time()-st)
 assert out['difference']<1e-7
 (W/'verification/three_loop_radial_check.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
