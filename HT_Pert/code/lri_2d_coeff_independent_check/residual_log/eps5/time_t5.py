"""Timing of the 5-vertex chain at production sizes: a random sample of Pi-surviving patterns, one word (all R)."""
import sys, time, random, numpy as np
import engine as eg, chains as ch
N = int(sys.argv[1]); nsamp = int(sys.argv[2])
modes = eg.Modes(N, 3)
pats = eg.patterns(["V"] * 5, None, 6)
random.seed(1)
samp = random.sample(pats, nsamp)
t0 = time.time()
ncfg = 0
for n in samp:
    cyc = eg.cycle_bundles(n, 5)
    c = 1
    for b in cyc:
        c *= n[b] + 1
    ncfg += c
res = ch.eval_group(["V"] * 5, [0] * 5, [(((1, 0),) * 4, None)], N, modes, (0, 1, 2, 3),
                    pattern_filter=lambda n: n in samp)
dt = time.time() - t0
print(f"N={N} patterns={nsamp} configs={ncfg} time={dt:.1f}s per pattern {dt/nsamp:.3f}s per config {dt/ncfg:.4f}s; "
      f"extrapolated full Pi-surviving set ({len(pats)} patterns): {dt/nsamp*len(pats)/3600:.2f} h serial", flush=True)
