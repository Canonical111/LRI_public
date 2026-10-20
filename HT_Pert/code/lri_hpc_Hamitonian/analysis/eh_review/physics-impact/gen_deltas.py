#!/usr/bin/env python3
"""Generate delta_C with the copied lri_eh solver (numerics.compute) for a list of cutoffs.
Usage: gen_deltas.py DEGREE OUT.json L1 L2 ...   (appends/merges records keyed by cutoff)"""
import sys, json, os, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'pkg'))
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
from numba import set_num_threads
from lri_eh.numerics import compute
deg = int(sys.argv[1]); out = Path(sys.argv[2]); Ls = [int(x) for x in sys.argv[3:]]
set_num_threads(int(os.environ.get('NTH', '4')))
recs = json.loads(out.read_text()) if out.exists() else {}
for L in Ls:
    if str(L) in recs: continue
    t = time.time()
    r = compute(L, deg, float(os.environ.get('MEMLIM', '12')))
    recs[str(L)] = dict(cutoff=L, degree=deg, delta_C=r['delta_C'], delta_r=r['delta_r'], delta_g=r['delta_g'],
                        validation=r['validation'], basis_dimension=r['basis_dimension'], seconds=time.time() - t)
    out.write_text(json.dumps(recs, indent=1))
    print(L, deg, r['basis_dimension'], ['%.13g' % x for x in r['delta_C'][4:]], r['validation'], '%.1fs' % (time.time() - t), flush=True)
