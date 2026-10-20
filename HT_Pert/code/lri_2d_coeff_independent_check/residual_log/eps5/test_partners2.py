import json, numpy as np
import engine as eg, windows5 as w5, partners as pt, assemble as asm
L = 4; N = L // 2
modes = eg.Modes(N, 3)
d = json.load(open(f"../zeromode_results/zeromode_L{L}.json"))
ez = d["E_z_float"]
r = d["r_float"]; g = d["g_float"]
parts3 = w5.channel_energy_parts(asm.collect_words(3), N, modes, 8)
dE, T = pt.dE3(modes, N)
for z in range(0, 8):
    ex = [ez[f"{z},{l}"][3] for l in (0, 2, 4)]
    mine = []
    for M in range(N + 1):
        v = sum(arr[M] * (1.0 if kap == () else (r[2] if kap == ('r2',) else g[2])) for kap, arr in parts3[(3, z)].items())
        mine.append(v)
    dd = dE.get(z, np.zeros(N + 1))
    print(z, "exact diffs (l=2-0, 4-0):", ["%+.10f" % (ex[1] - ex[0]), "%+.10f" % (ex[2] - ex[0])],
          " naive:", ["%+.10f" % (mine[1] - mine[0]), "%+.10f" % (mine[2] - mine[0])],
          " partner corr:", ["%+.10f" % (dd[1] - dd[0]), "%+.10f" % (dd[2] - dd[0])])
