#!/usr/bin/env python3
"""The degenerate-partner sets B used by zeromode_modular.py (states with level + (P - z)/2 = 0, other than |z>)
coincide with the reflection-even blocks of degeneracy.py, for every z <= 18 and l <= 10."""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import zeromode_modular as ZM
deg = json.load(open(os.path.join(HERE, 'results', 'degeneracy.json')))['blocks']
dims = {(b['z'], b['N']): b['n_even'] for b in deg}
L = 10
S = {par: ZM.Structure(L, par, 22 if par == 0 else 23, verbose=False) for par in (0, 1)}
ok = True
for z in range(0, 19):
    st = S[z % 2]
    for l in range(0, L + 1, 2):
        n = st.nl[l]
        lev, P = st.level[:n], st.P[:n]
        B = np.nonzero((lev + (P - z) // 2 == 0) & ~((lev == 0) & (P == z)))[0]
        byN = {}
        for i in B:
            byN[int(lev[i])] = byN.get(int(lev[i]), 0) + 1
        exp = {N: dims[(z, N)] for N in range(2, l + 1, 2) if (z, N) in dims}
        if byN != exp:
            ok = False
            print('MISMATCH', z, l, byN, exp)
print('partner sets == degeneracy.py reflection-even blocks for z <= 18, l <= 10:', ok)
