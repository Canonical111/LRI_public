"""X_n_{z'z}(L), n = 2, 3, without windows: brute DChannel vs open rs words (per word for diag)."""
import sys, os, math
sys.path.insert(0, os.path.abspath(".."))
from fractions import Fraction as Fr
import numpy as np
import brute_W5 as bw
import engine as eg
import windowsW as ww
import rs
import bloch
rf = bw.rf
L = int(sys.argv[1]); nord = int(sys.argv[2]); zsel = [int(x) for x in sys.argv[3].split(",")] if len(sys.argv) > 3 else None
K = 8
N = L // 2
r = [Fr(0)] * 6; g = [Fr(0)] * 6; g[1] = Fr(1, 3)
zero = lambda k, N: 0
res_b = {}
E2b = {}
for par in (0, 1):
    sp = rf.Space(L, par, bw.ZMAX + K)
    ctup = rf.ordered_creation_tuples(sp, 4)
    ops = {"M": rf.build_vertex(sp, 2, Fr(1), ctup), "V": rf.build_vertex(sp, 4, Fr(1, 12), ctup)}
    for z in range(par, 7, 2):
        c = bw.DChannel(f"z{z}", sp, ops, z, L, K, zero, drop_degenerate=True, bequation=False)
        for n in range(1, nord + 1):
            c.finish_order(n, c.rhs_without_new(n, r, g), r[n], g[n])
        for zp in range(par, 7, 2):
            res_b[(zp, z)] = c.psi[nord].get(sp.ref_index(zp), 0)
        E2b[z] = float(c.E[2]) if nord >= 2 else 0.0
modes = eg.Modes(N, 3)
E, psi = rs.unroll(nord, windows=False, return_psi=True)
words = []
for (c, sy, ops, pw) in psi[nord]:
    if any(s[0] in "rg" for s in sy): continue
    rr = bloch.decorate_open(ops, pw)
    if rr is None: continue
    variants, q, af = rr
    for var in variants:
        words.append((c, sy, var, q, af, ops, pw))
print(len(words), "words")
eg.DROP_ZERO_DEN = True
for z in range(7):
    for zp in range(z % 2, 7, 2):
        if zp == z: continue
        if zsel and (z, zp) != tuple(zsel): continue
        tot = 0.0
        per = []
        for (c, sy, (verts, slices, windows), q, af, ops, pw) in words:
            if len(verts) == 1:
                vals = None
                # single level-0 matrix element: <z'|V_j|z> (normalized)
                v0 = 0.0
                if verts[0][0] == "V":
                    for rs_, amp in eg.zero_mode_paths(z, [4], zp):
                        v0 += float(amp)
                    v0 /= 12.0
                    # V_j for j > 0: x-derivative pieces of V -- skip (handled by brute only)
                    if verts[0][1] != 0: v0 = 0.0
                else:
                    v0 = float("nan")
                fin = float((zp - z) ** q) * (2.0 / (z - zp)) ** af
                v = float(c) * fin * v0
            else:
                vals = ww.eval_decorated(verts, slices, windows, N, modes, None, ps=(z,), z_end={z: zp})
                if not vals:
                    continue
                fin = float((zp - z) ** q) * (2.0 / (z - zp)) ** af
                v = 0.0
                for kap, d in vals.items():
                    v += float(c) * fin * d[z][N]
            for s in sy:
                if s == "E1": v *= (1/3) * z * (z - 1) / 2
                elif s == "E2": v *= E2b[z]
                else: v = float("nan")
            per.append((ops, pw, sy, v))
            tot += v
        nf = math.sqrt(math.factorial(z) / math.factorial(zp))
        print(f"z={z} z'={zp}: diag {nf*tot:+.10f} brute {float(res_b[(zp,z)]):+.10f}")
        if zsel:
            for (ops, pw, sy, v) in per:
                print("   ", ops, pw, sy, f"{nf*v:+.10f}")
