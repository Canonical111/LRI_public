"""Fresh residue sums and independent spectral quadrature, with varied cutoffs.
Euler acceleration is applied only to the alternating spin sum. No fitting to
known P5 values, no saved periods, and no changes to the mathematical terms.
"""
from pathlib import Path
import sys,time,json
import numpy as np
from scipy.special import roots_legendre, loggamma
sys.path.insert(0,str(Path(__file__).parent))
from primitive_series import terms,degeneracy
BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE))
from primitive_spectral import terms as spectral_terms,euler

def residue(d,N,spins=112,start=12,depth=88):
 a=terms(d,np.arange(spins),np.arange(N)).sum(axis=1)*(-1.)**np.arange(spins)
 if d==1:return float(a[0]-a[1])
 return euler(a,start,depth)

def spectral2(nodes,spins=128):
 xx,ww=roots_legendre(nodes);u=(xx+1)/2;ww/=2
 l=np.arange(spins)[:,None];v=(l/2+.25)*u/(1-u);jac=(l/2+.25)/(1-u)**2
 logg=2*(loggamma(l/2+.25+1j*v)-loggamma(l/2+.75+1j*v)).real
 a=(np.exp(7*logg)*(l*l+4*v*v)*jac*ww).sum(axis=1)*degeneracy(2,np.arange(spins))/(2*np.pi)
 return euler(a,12,88)
rows=[]
for d in [1.,2.,2.6,3.]:
 ref=[]
 if d==1:
  rec=json.loads((Path(__file__).resolve().parents[2]/'verification/general_closed/identity_checks.json').read_text())
  target=float(rec['P5_d1_gamma_integral']);ref=[dict(method='fresh_60digit_gamma_integral',value=target)]
 else:
  for nodes in [224,352]:
   value=spectral2(nodes) if d==2 else euler(spectral_terms(d,[5],spins=128,nodes=nodes)[5],12,88)
   ref.append(dict(method='fresh_spectral_quadrature',nodes=nodes,value=value))
  target=ref[-1]['value']
 for N in [128,256,512,1024]:
  t=time.time();v=residue(d,N,2 if d==1 else 112)
  row=dict(d=d,N=N,spin_terms=2 if d==1 else 112,start=12,depth=88,value=v,residual=v-target,sec=time.time()-t)
  rows.append(row);print(row,flush=True)
 rows.append(dict(d=d,reference=ref))
out=dict(scope='Fresh period-level comparisons; raw radial truncation plus finite Euler acceleration of angular sum. Residuals are not certified error bounds.',rows=rows)
(Path(__file__).resolve().parents[2]/'verification/general_closed/primitive_sum_checks.json').write_text(json.dumps(out,indent=2))
