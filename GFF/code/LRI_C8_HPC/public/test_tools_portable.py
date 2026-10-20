#!/usr/bin/env python3
"""Portable form of tests/test_c8_tools.py (which ships verbatim and is run first by `make -f public.mk test`).

The original requires the NW=7 Jacobian to equal the archived C7 affine map BIT FOR BIT. That holds on the Mac
(numpy 1.23-1.24) but not on every platform: on a personal desktop (numpy 1.26.4, OpenBLAS) and on symmetry AMD nodes (anaconda numpy
1.24.3) one of the 112 loop-5 entries differs by one unit in the last place (1.1e-16 absolute, 3.0e-16 relative). This copy runs the same
three checks with the Jacobian compared to 1e-15 of the row scale; everything else is unchanged.
"""
import itertools, json, math, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'tools'))
from c8lib import coefficients, jacobian, NW
from campaign import tree_count
R = ROOT / 'reference'
v = {2: np.array(json.loads((R / 'records/coord_L2_N24.json').read_text())['batches'])[0],
     3: np.array(json.loads((R / 'records/coord_L3_N24.json').read_text())['batches'])[0],
     4: np.array(json.loads((R / 'records/trefexact_L4_N20.json').read_text())['batches'])[0]}
ref = json.loads((R / 'verification/full_affine_assembly.json').read_text())
K = coefficients(v, 7); assert np.allclose(K, ref['K'], rtol=1e-9, atol=1e-9), K
for L in (5, 6, 7):
    a = jacobian(v, L, 7); b = np.array(ref['loops'][str(L)]['J']); scale = np.abs(b).max(axis=1)
    zero = scale == 0; assert np.array_equal(a[zero], b[zero]), (L, 'rows that vanish in the archive must vanish exactly')
    d = float((np.abs(a - b)[~zero] / scale[~zero, None]).max()); assert d <= 1e-15, (L, d)
    print(f'J{L}: {int((a != b).sum())} of {a.size} entries differ in the last bits; max |diff| / row scale = {d:.2e}')
v8 = {L: np.concatenate([a[:7], [0.], a[7:], [0.]]) for L, a in v.items()}; j = jacobian(v8, 8)[8]
nz = [k for k in range(2 * NW) if abs(j[k]) > 1e-14 * abs(j).max()]; assert nz == [NW - 1, 2 * NW - 1] and abs(j[2 * NW - 1] / j[NW - 1] + 3) < 1e-9, (nz, j)
def shapes(n): return 1 if n == 1 else sum(shapes(k) * shapes(n - k) for k in range(1, n))
for L in range(2, 9):
    n = L + 1; orders = sum(1 for p in itertools.permutations(range(n)) if p[0] < p[-1]) if n <= 8 else math.factorial(n) // 2
    assert tree_count(L) == orders * shapes(n), (L, tree_count(L))
print('test_tools_portable: all checks passed')
