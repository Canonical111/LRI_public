import sys
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parents[1]/'reference')]
import numpy as np,numba
numba.set_num_threads(2)
from lri_hpc.operators import Space,quotient_components
from compute_phi6 import GapSpace
from check_lri_hamiltonian import quotient_components as original_q
rng=np.random.default_rng(102)
for L in [4,8,12,24]:
 a=Space(L,15,12,6);b=GapSpace(L,pmax=15,qmax=12,degree=6)
 psi=np.ascontiguousarray(rng.normal(size=(a.dim,4)))
 # The quotient shortcut assumes the source parity; auxiliary parities stay in ladder products.
 psi[~a.even]=0;psi[a.P%2==1]=0
 for deg in [0,1,3,6]:
  for creation in [False,True]:
   out=a.linear(psi,deg,creation);target=b.linear_series(psi.T,deg,creation)
   np.testing.assert_allclose(out.T,target,rtol=2e-13,atol=2e-12)
  m,v=a.vertices(psi,deg);mr,vr=b.vertices(psi.T,deg)
  np.testing.assert_allclose(m.T,mr,rtol=2e-12,atol=2e-11)
  np.testing.assert_allclose(v.T,vr,rtol=2e-12,atol=2e-10)
 f,m,v=quotient_components(a,psi,7);fr,mr,vr=original_q(b,psi.T,7)
 np.testing.assert_allclose([f,m,v],[fr,mr,vr],rtol=2e-11,atol=2e-10)
 print('operators PASS',L,flush=True)
