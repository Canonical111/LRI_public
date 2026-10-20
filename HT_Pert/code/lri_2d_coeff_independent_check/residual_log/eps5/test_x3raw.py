"""X3_{z'z}(L) without windows: brute (DChannel, no D) vs bloch open words (comps empty)."""
import sys, os, math
sys.path.insert(0, os.path.abspath(".."))
from fractions import Fraction as Fr
import numpy as np
import brute_W5 as bw
import engine as eg
import windowsW as ww
import bloch
rf = bw.rf
L = int(sys.argv[1]) if len(sys.argv) > 1 else 4
K = 8
N = L // 2
r = [Fr(0)] * 6; g = [Fr(0)] * 6; g[1] = Fr(1, 3)
zero = lambda k, N: 0
res_b = {}
for par in (0, 1):
    sp = rf.Space(L, par, bw.ZMAX + K)
    ctup = rf.ordered_creation_tuples(sp, 4)
    ops = {"M": rf.build_vertex(sp, 2, Fr(1), ctup), "V": rf.build_vertex(sp, 4, Fr(1, 12), ctup)}
    for z in range(par, 7, 2):
        c = bw.DChannel(f"z{z}", sp, ops, z, L, K, zero, drop_degenerate=True, bequation=False)
        for n in (1, 2, 3):
            c.finish_order(n, c.rhs_without_new(n, r, g), r[n], g[n])
        for zp in range(par, 7, 2):
            res_b[(zp, z)] = c.psi[3].get(sp.ref_index(zp), 0)
modes = eg.Modes(N, 3)
words = bloch.X3_words({2: set(), 3: set()})
print(len(words), "words")
eg.DROP_ZERO_DEN = True
for z in range(7):
    for zp in range(z % 2, 7, 2):
        if zp == z: continue
        tot = 0.0
        for (c, sy, (verts, slices, windows), q, af) in words:
            if sy:   # E symbols only (r,g = 0)
                if any(s[0] != "E" for s in sy): continue
            vals = ww.eval_decorated(verts, slices, windows, N, modes, None, ps=(z,), z_end={z: zp})
            if not vals: continue
            fin = float((zp - z) ** q) * (2.0 / (z - zp)) ** af
            for kap, d in vals.items():
                v = float(c) * fin * d[z][N]
                for s in sy:
                    if s == "E1": v *= (1/3) * z * (z - 1) / 2
                    elif s == "E2": v = None; break
                if v is None: continue
                tot += v
        nf = math.sqrt(math.factorial(z) / math.factorial(zp))
        print(f"z={z} z'={zp}: diag {nf*tot:+.10f} brute {float(res_b[(zp,z)]):+.10f}")
