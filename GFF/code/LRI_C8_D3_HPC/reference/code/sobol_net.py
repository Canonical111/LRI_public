"""Frozen independently scrambled Sobol direction matrices with exact API checks."""
import struct
import numpy as np
import scipy
from scipy.stats import qmc
def make_net(path,B,dim,bits,seed):
 rng=np.random.default_rng(seed);matrices=[]
 for i in range(B):
  engine=qmc.Sobol(d=dim,scramble=True,bits=bits,seed=int(rng.integers(1,2**32-1)))
  mat=engine._sv.copy()
  state=engine._shift.copy();raw=[]
  for n in range(16):
   if n:state^=mat[:,(n&-n).bit_length()-1]
   raw.append(state.copy())
  expected=engine.random_base2(4)
  assert np.max(np.abs(np.array(raw,dtype=np.float64)/2**bits-expected))==0
  matrices.append(mat.astype('<u8'))
 with path.open('wb')as f:f.write(struct.pack('<III',B,dim,bits));np.array(matrices).tofile(f)
 return {'scipy':scipy.__version__,'replicates':B,'dimensions':dim,'bits':bits,'matrix_seed':seed,'gray_code_comparisons':B*16*dim,'max_abs_reconstruction_error':0}

