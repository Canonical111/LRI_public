"""RR-001: precision sensitivity of the inherited L2-L4 amplitudes (reference/lower_extended.py at degree N).
Usage: python lowercheck.py REFDIR MODE(ld|f64) N OUT.json
Same code as reference/lower_extended.py (one extra eps order), with the module's arithmetic type set to MODE."""
import os, sys, json, pickle, inspect
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import numpy as np
ref, mode, N, outp = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
sys.path.insert(0, ref + '/lri_numerical_resolution/verification/source')
import ising_five_loop as old
if mode == 'f64':
    old.LD = np.float64
src = inspect.getsource(old.qweights.__wrapped__)
src = src.replace('@lru_cache(None)\n', '').replace('4 if log else 5', '5 if log else 6').replace('(5,N+1)', '(6,N+1)').replace('range(5)', 'range(6)')
ns = old.__dict__; exec(src, ns); old.qweights = old.lru_cache(None)(ns['qweights'])
src = inspect.getsource(old.integrate).replace('(2,5)', '(2,6)').replace('maxp=5-L+p', 'maxp=6-L+p').replace('range(5)', 'range(6)')
exec(src, ns)
old.SECTOR_CACHE = {}
for n in [3, 4, 5]:
    old.SECTOR_CACHE[n] = old.sectors(n, old.graphs(n))
out = {}
for cut in ['maxgap', 'span']:
    out[cut] = {L: [{str(k): str(v) for k, v in a.items()} for a in old.integrate(L + 1, N, cut)] for L in [2, 3, 4]}
json.dump({'mode': mode, 'N': N, 'dtype': str(old.LD), 'result': out}, open(outp, 'w'), indent=1)
print('done', mode, N)
