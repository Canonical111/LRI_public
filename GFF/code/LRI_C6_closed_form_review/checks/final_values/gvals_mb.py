# Step 2: ordinary Meijer G values at 1 by direct Mellin-Barnes integration on Re s = 1/4
# (ds/(2 pi i), upward) using kernels built from the parameter lists.
import mpmath as mp, sys, time, json
from params import setup
from kernels import gkernel_log, Glists
dps = int(sys.argv[1]) if len(sys.argv) > 1 else 40
P = setup(dps + 10)
mp.mp.dps = dps + 10
L = Glists(P)
names = sys.argv[2].split(',') if len(sys.argv) > 2 else ['G4', 'G6', 'G8', 'G7']
res = {}
for nm in names:
    a, b, m, n = L[nm]
    f = lambda u: mp.re(mp.exp(gkernel_log(mp.mpc(0.25, u), a, b, m, n)))
    t0 = time.time()
    # (1/2pi) int_R K du = (1/pi) int_0^inf Re K du  (K(conj s) = conj K(s))
    v1 = mp.quad(f, [0, 1, 3, 8, 20, 60, mp.inf])/mp.pi
    t1 = time.time()
    v2 = mp.quad(f, [0, 0.5, 2, 5, 12, 40, 150, mp.inf])/mp.pi
    print(nm, mp.nstr(v1, dps), "| alt subdivision diff", mp.nstr(v1 - v2, 3), f"| {t1-t0:.1f}s", flush=True)
    res[nm] = [str(v1), str(v2)]
json.dump(res, open(f'gvals_mb_{dps}.json', 'w'), indent=1)
