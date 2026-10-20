#!/usr/bin/env python3
"""Generate the task files for the production job (chains + weak coupling + N=16/20 stage)."""
import json
import os
import sys

base = sys.argv[1] if len(sys.argv) > 1 else "<SCRATCH>/lri_dressed/independent_check"
outdir = sys.argv[2] if len(sys.argv) > 2 else "tasks"
os.makedirs(outdir, exist_ok=True)

TARGETS = [0.249, 0.2, 0.1, 0.05, 0.025, 0.01]
WEAK = [0.24995, 0.2499, 0.2498, 0.2497, 0.2495, 0.2493, 0.249, 0.2485]
CHAIN = [0.24995, 0.2499, 0.2498, 0.2497, 0.2495, 0.2493, 0.249, 0.2485, 0.2475, 0.245, 0.24, 0.235, 0.23, 0.22,
         0.21, 0.2, 0.19, 0.18, 0.17, 0.16, 0.15, 0.14, 0.13, 0.12, 0.11, 0.1, 0.09, 0.08, 0.07, 0.06, 0.05,
         0.045, 0.04, 0.035, 0.03, 0.025, 0.0225, 0.02, 0.0175, 0.015, 0.0135, 0.012, 0.011, 0.01]


def write(name, points):
    with open(os.path.join(outdir, name + ".json"), "w") as fh:
        json.dump({"points": points}, fh, indent=1)


# N=12 continuation chains (verify grid at target and weak-coupling points)
for presc, last in (("raw", 0.01), ("consistent", 0.01), ("literal", 0.1)):
    pts = []
    for d in CHAIN:
        if d < last - 1e-12:
            break
        tgt = (d in TARGETS) or (d in WEAK and presc != "literal")
        pts.append(dict(delta=d, N=12, presc=presc, verify=bool(tgt)))
    write("chain_%s_N12" % presc, pts)

# weak-coupling chains at other cutoffs
for presc in ("raw", "consistent"):
    for N in (0, 2, 4, 8, 16):
        write("weak_%s_N%d" % (presc, N), [dict(delta=d, N=N, presc=presc, verify=True) for d in WEAK])

# N = 16 -> 20 at each target delta, seeded from the N=12 chain (waits for it)
for presc in ("raw", "consistent"):
    for d in TARGETS:
        src = os.path.join(base, "results", "chain_%s_N12.json" % presc)
        pts = [dict(delta=d, N=16, presc=presc, verify=True,
                    guess_from=dict(file=src, delta=d, N=12, presc=presc, wait=True)),
               dict(delta=d, N=20, presc=presc, verify=True)]
        write("hiN_%s_d%s" % (presc, ("%g" % d).replace(".", "p")), pts)
print("tasks written to", outdir)
