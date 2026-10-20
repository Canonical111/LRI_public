import sys, json, numpy as np, time
import engine as eg, assemble as asm
Lmax = int(sys.argv[1]); nmax = int(sys.argv[2])
N = Lmax // 2
t = time.time()
modes = eg.Modes(N, 3)
words = asm.collect_words(nmax)
vals = asm.evaluate_words(words, nmax, N, modes, verbose=False)
res = asm.assemble(words, vals, nmax, N)
print(f"evaluated in {time.time()-t:.1f}s")
worst = {}
for L in range(0, Lmax + 1, 2):
    d = json.load(open(f"../rs_exact_results/raw_L{L}.json"))
    i = L // 2
    for n in range(2, nmax + 1):
        for key, mine in (("C", res["C"][n][i]), ("r", res["r"][n][i]), ("g", res["g"][n][i])):
            ref = d[key + "_float"][n]
            e = abs(mine - ref) / max(1.0, abs(ref))
            worst[(key, n)] = max(worst.get((key, n), 0), e)
        for p in range(4):
            ref = d["E_float"][p][n] if isinstance(d["E_float"][p], list) else None
            if ref is not None:
                e = abs(res["E"][n][p][i] - ref) / max(1.0, abs(ref))
                worst[("E", n)] = max(worst.get(("E", n), 0), e)
    print(f"L={L:3d} " + " ".join(f"C{n}={res['C'][n][i]:+.12f}/{d['C_float'][n]:+.12f}" for n in range(2, nmax + 1)))
print("worst relative deviations:", {k: f"{v:.1e}" for k, v in sorted(worst.items())})
