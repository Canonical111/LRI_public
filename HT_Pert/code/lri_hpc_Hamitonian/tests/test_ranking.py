import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'reference'))
import numpy as np,numba
numba.set_num_threads(2)
from lri_hpc.basis import RankedBasis
from compute_phi6 import GapSpace
for L,pmax,qmax in [(2,15,12),(4,15,12),(8,14,8),(12,15,12),(16,14,8),(24,10,4),(300,6,1)]:
 a=RankedBasis(L,pmax,qmax);b=GapSpace(L,pmax=pmax,qmax=qmax,degree=1)
 assert a.global_dim==b.dim,(L,a.global_dim,b.dim)
 np.testing.assert_array_equal(a.P,b.P);np.testing.assert_array_equal(a.N,b.N)
 np.testing.assert_array_equal(a.creation.ptr,b.C[0].indptr)
 np.testing.assert_array_equal(a.creation.index,b.C[0].indices)
 for e,ref in [(a.creation,b.C[0]),(a.annihilation,b.B[0].tocsr())]:
  from scipy.sparse import csr_matrix
  from check_lri_hamiltonian import square_root_jets
  mat=csr_matrix((square_root_jets(L,1)[0,e.mode]*np.sqrt(e.occ.astype(float)),e.index,e.ptr),shape=(a.dim,a.dim))
  assert np.max(np.abs((mat-ref).data),initial=0)==0
 print('PASS',L,pmax,qmax,a.dim,flush=True)
