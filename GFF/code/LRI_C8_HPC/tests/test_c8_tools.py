#!/usr/bin/env python3
"""Fast local checks of the C8 Python tooling (no integrator needed).
1. c8lib.coefficients/jacobian with NW=7 reproduce the archived C7 affine map (K to 1e-9 relative, J exactly).
2. At NW=8 the top-loop channel rule holds: C8 depends on loop 8 only through 3*c8(0)-b8(0).
3. campaign.tree_count(L) equals an explicit enumeration of vertex orders (order[0]<order[n-1]) x binary shapes.
"""
import itertools, json, math, sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from c8lib import coefficients,jacobian,NW
from campaign import tree_count
R=ROOT/'reference'
v={2:np.array(json.loads((R/'records/coord_L2_N24.json').read_text())['batches'])[0],3:np.array(json.loads((R/'records/coord_L3_N24.json').read_text())['batches'])[0],4:np.array(json.loads((R/'records/trefexact_L4_N20.json').read_text())['batches'])[0]}
ref=json.loads((R/'verification/full_affine_assembly.json').read_text())
K=coefficients(v,7);assert np.allclose(K,ref['K'],rtol=1e-9,atol=1e-9),K
for L in (5,6,7):assert np.array_equal(jacobian(v,L,7),np.array(ref['loops'][str(L)]['J'])),L
v8={L:np.concatenate([a[:7],[0.],a[7:],[0.]]) for L,a in v.items()};j=jacobian(v8,8)[8]
nz=[k for k in range(2*NW) if abs(j[k])>1e-14*abs(j).max()];assert nz==[NW-1,2*NW-1] and abs(j[2*NW-1]/j[NW-1]+3)<1e-9,(nz,j)
def shapes(n):return 1 if n==1 else sum(shapes(k)*shapes(n-k) for k in range(1,n))
for L in range(2,9):
    n=L+1;orders=sum(1 for p in itertools.permutations(range(n)) if p[0]<p[-1]) if n<=8 else math.factorial(n)//2
    assert tree_count(L)==orders*shapes(n),(L,tree_count(L))
print('test_c8_tools: all checks passed')
