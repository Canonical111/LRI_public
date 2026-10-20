"""compare Bloch h3 windows (diagrammatic, bloch.py) with brute_W5 Wb h3 at small L."""
import sys, os
sys.path.insert(0, os.path.abspath(".."))
import math
import numpy as np
import brute_W5 as bw
import engine as eg
import prod5 as pr
L = int(sys.argv[1]) if len(sys.argv) > 1 else 4
bw.run(L, ["Wb"], verbose=False)
h3b = bw.LAST_H3
r, g = bw.LAST_RG
N = L // 2
modes = eg.Modes(N, 3)
inn = pr.inner(N, modes, bloch_too=True)
H3 = inn["H3"]
sym = {"r2": float(r[2]), "g2": float(g[2])}
for (zp, z), d in sorted(H3.items(), key=lambda t: (t[0][1], t[0][0])):
    arr = np.zeros(N + 1)
    for kap, a in d.items():
        c = 1.0
        for s in kap:
            c *= sym[s]
        arr = arr + c * a
    nf = math.sqrt(math.factorial(z) / math.factorial(zp))
    da = [nf * (arr[i] - arr[0]) for i in range(N + 1)]
    db = [float(h3b[(zp, z, 2 * i)] - h3b[(zp, z, 0)]) for i in range(N + 1)]
    diff = max(abs(x - y) for x, y in zip(da, db))
    if diff > 1e-12:
        print(f"z={z} z'={zp}: diag {np.round(da, 8)} brute {np.round(db, 8)}  maxdiff {diff:.2e}")
print("done")
