# Step 2, method 2: mpmath.meijerg at z=1 (mpmath's own residue/hypergeometric-series evaluation).
import mpmath as mp, sys, time, json, signal
from params import setup
from kernels import Glists
dps = int(sys.argv[1]) if len(sys.argv) > 1 else 20
names = sys.argv[2].split(',') if len(sys.argv) > 2 else ['G4', 'G6', 'G8', 'G7']
P = setup(dps)
mp.mp.dps = dps
L = Glists(P)
class TO(Exception): pass
def handler(sig, frm): raise TO()
signal.signal(signal.SIGALRM, handler)
res = {}
for nm in names:
    a, b, m, n = L[nm]
    t0 = time.time()
    signal.alarm(50)
    try:
        v = mp.meijerg([a[:n], a[n:]], [b[:m], b[m:]], 1)
        signal.alarm(0)
        print(nm, "meijerg:", mp.nstr(v, dps), f"({time.time()-t0:.1f}s)", flush=True)
        res[nm] = str(v)
    except TO:
        print(nm, "meijerg: timed out after 50 s", flush=True)
    except Exception as e:
        signal.alarm(0)
        print(nm, "meijerg failed:", repr(e)[:200], flush=True)
json.dump(res, open(f'gvals_meijerg_{dps}.json', 'w'), indent=1)
