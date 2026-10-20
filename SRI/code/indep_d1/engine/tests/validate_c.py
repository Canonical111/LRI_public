#!/usr/bin/env python3
"""Validation ladder step (c): low moments with v/delta derivatives, computed by the engine.
Writes results/validation_c.json  {name: {"k,j": [value, err]}}"""
import sys, os, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'py'))
from lri_moments import moment
N = int(sys.argv[1]) if len(sys.argv) > 1 else 16001
out = {}
specs = [  # name, kind, n, nv, nd, powers
    ('A3_base', 'A', 3, 0, 0, (-1, 0, 1, 2)), ('A3_v', 'A', 3, 1, 0, (-1, 0, 1, 2)), ('A3_d', 'A', 3, 0, 1, (-1, 0, 1, 2)),
    ('A3_vd', 'A', 3, 1, 1, (-1, 0, 1, 2)), ('A3_vv', 'A', 3, 2, 0, (-1, 0, 1, 2)),
    ('Z4_base', 'Z', 4, 0, 0, (-2, -1, 0, 1)), ('Z4_v', 'Z', 4, 1, 0, (-2, -1, 0, 1)), ('Z4_d', 'Z', 4, 0, 1, (-2, -1, 0, 1)),
    ('Q4_base', 'Q', 4, 0, 0, (-1, 0, 1)), ('Q4_v', 'Q', 4, 1, 0, (-1, 0, 1)), ('Q4_d', 'Q', 4, 0, 1, (-1, 0, 1)),
    ('Q4_vd', 'Q', 4, 1, 1, (-1, 0, 1)), ('Q4_vv', 'Q', 4, 2, 0, (-1, 0, 1)),
    ('A5_base', 'A', 5, 0, 0, (-2, -1, 0)), ('A5_v', 'A', 5, 1, 0, (-2, -1, 0)), ('A5_d', 'A', 5, 0, 1, (-2, -1, 0)),
]
for name, kind, n, nv, nd, powers in specs:
    t = time.time()
    r, meta = moment(kind, n, nv, nd, 0, powers=powers, N=N, shifts=8, threads=8)
    out[name] = {f'{k},{j}': list(v) for (k, j), v in sorted(r.items())}
    print(name, 'done %.1fs' % (time.time() - t), flush=True)
    json.dump(out, open(os.path.join(HERE, '..', 'results', 'validation_c.json'), 'w'), indent=1)
