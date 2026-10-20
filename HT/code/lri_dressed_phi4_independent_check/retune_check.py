#!/usr/bin/env python3
"""Full (non-linearized) grid check: retune a finished point on the 1.5x finer
and 1.5x wider DVR grids and compare Delta_eps with the production grid.
Usage: retune_check.py results.json delta N presc out.json"""
import json
import sys
import time

import numpy as np

import indep_ht as ih

fn, d, N, presc, out = sys.argv[1], float(sys.argv[2]), int(sys.argv[3]), sys.argv[4], sys.argv[5]
rec = [x for x in json.load(open(fn)) if abs(x["delta"] - d) < 1e-12 and x["N"] == N and x["presc"] == presc
       and "Delta_eps" in x][-1]
h, Q = rec["grid_hQ"]
bath = ih.Bath(d, N)
res = dict(delta=d, N=N, presc=presc, base=dict(h=rec["grid"]["h"], M=rec["grid"]["M"], Delta_eps=rec["Delta_eps"],
                                               r=rec["r"], g=rec["g"]))
for kind in ("fine", "wide"):
    t0 = time.time()
    hv, Mv = ih.grid_variant(h, Q, kind)
    prob = ih.Problem(d, N, hv, Mv, presc, bath=bath)
    th, ev = ih.tune(prob, rec["r"], rec["g"], tol=1e-12)
    res[kind] = dict(h=hv, M=Mv, Delta_eps=ih.delta_eps(ev), r=float(th[0]), g=float(th[1]),
                     F=ih.residuals(d, ev).tolist(), dDelta_eps=ih.delta_eps(ev) - rec["Delta_eps"],
                     lin_estimate=rec["grid_check"][kind]["dDelta_eps_tuned_lin"], time=time.time() - t0)
    print(kind, res[kind], flush=True)
json.dump(res, open(out, "w"), indent=1)
