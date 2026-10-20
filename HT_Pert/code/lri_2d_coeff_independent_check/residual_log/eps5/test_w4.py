import sys, json, numpy as np
import schemeW as sw
sw.run.__defaults__
res = sw.run(8, ["W2"], nmax=4, verbose=False)
for L in (2, 4, 6, 8):
    d = json.load(open(f"../brute/brute_W_L{L}.json"))
    from fractions import Fraction as Fr
    rW = [float(Fr(x)) for x in d["r_W_spec"]]; gW = [float(Fr(x)) for x in d["g_W_spec"]]
    i = L // 2
    print(L, "C4 %.15f vs brute %.15f" % (res["W2"]["C"][4][i], d["C4_W_spec"]),
          " r3 %.2e g3 %.2e" % (res["W2"]["r"][3][i] - rW[3], res["W2"]["g"][3][i] - gW[3]))
