import os, sys, time, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine as eg
N = int(sys.argv[1]) if len(sys.argv) > 1 else 150
shape = (N + 1,) * 4
rng = np.random.default_rng(1)
X = rng.random(shape)
f = rng.random(N + 1)
shp = np.array(shape, dtype=np.int64)
for (lo, hi) in ((0, 2), (1, 3), (2, 4), (0, 3), (1, 4)):
    t = time.time(); Y1 = eg._diag_conv_par(X.reshape(-1), shp, lo, hi, f).reshape(shape); t1 = time.time() - t
    t = time.time(); Y2 = eg._diag_conv4(X, lo, hi, f); t2 = time.time() - t
    t = time.time(); Y2 = eg._diag_conv4(X, lo, hi, f); t3 = time.time() - t
    print(f"span {lo}..{hi - 1}: par {t1:.2f}s  box(first) {t2:.2f}s  box {t3:.2f}s  max|diff| {np.abs(Y1 - Y2).max():.1e}", flush=True)
t = time.time(); Z = eg.conv_axis_c(X, f, 1); print(f"conv_axis_c axis 1: {time.time() - t:.2f}s", flush=True)
t = time.time(); Z = eg.cumsum_axis_c(X, 1); print(f"cumsum_axis_c axis 1: {time.time() - t:.2f}s", flush=True)
