"""Validate consistent and zeromode C_n (n <= nmax) against ../rs_exact_results (consistent) and ../zeromode_results."""
import sys, json, time, numpy as np
import engine as eg, assemble as asm, windows5 as w5
Lmax = int(sys.argv[1]); nmax = int(sys.argv[2]); schemes = sys.argv[3].split(",") if len(sys.argv) > 3 else ["consistent", "zeromode"]
N = Lmax // 2
t = time.time()
modes = eg.Modes(N, 3)
words = asm.collect_words(nmax)
vals = asm.evaluate_words(words, nmax, N, modes, verbose=False)
raw = asm.assemble(words, vals, nmax, N)
print(f"raw words evaluated {time.time()-t:.1f}s", flush=True)
coup = {f"r{k}": raw["r"][k] for k in (2, 3)}; coup.update({f"g{k}": raw["g"][k] for k in (2, 3)})
Eraw = {j: raw["E"][j] if j > 1 else raw["E"][1] for j in (1, 2, 3)}
for scheme in schemes:
    extra = w5.window_extra(scheme, nmax, N, modes, coup, Eraw, prune=False, verbose=False)
    res = asm.assemble(words, vals, nmax, N, extra=extra)
    print(f"{scheme}: assembled {time.time()-t:.1f}s", flush=True)
    worst = {}
    for L in range(0, Lmax + 1, 2):
        f = f"../rs_exact_results/consistent_L{L}.json" if scheme == "consistent" else f"../zeromode_results/zeromode_L{L}.json"
        d = json.load(open(f))
        i = L // 2
        Cref = d["C_float"]
        line = []
        for n in range(2, nmax + 1):
            e = abs(res["C"][n][i] - Cref[n]) / max(1, abs(Cref[n])); worst[("C", n)] = max(worst.get(("C", n), 0), e)
            if "r_float" in d:
                for key in ("r", "g"):
                    ref = d[key + "_float"][n]; e = abs(res[key][n][i] - ref) / max(1, abs(ref))
                    worst[(key, n)] = max(worst.get((key, n), 0), e)
            line.append(f"C{n}={res['C'][n][i]:+.12f}/{Cref[n]:+.12f}")
        print(f"{scheme} L={L:3d} " + " ".join(line))
    print(scheme, "worst relative deviations:", {k: f"{v:.1e}" for k, v in sorted(worst.items())}, flush=True)
