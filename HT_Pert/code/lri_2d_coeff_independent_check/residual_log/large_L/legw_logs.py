#!/usr/bin/env python3
"""Log content of the C_5 response to the eps^3 leg window, by M' type (../results/legw/legw_L1000.npz, exact chain sums,
every even L <= 1000; nm_legw.py).  Shows which combinations of per-type coefficients are free of ln L.
Writes fits/legw_logs.txt.  Local fits of existing data."""
import os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
s = np.load(os.path.join(HERE, "..", "results", "legw", "legw_L1000.npz"))
L = s["L"].astype(float)


def B(n, L):
    l = np.log(L)
    return {"1": np.ones_like(L), "l": l, "l2": l * l, "l/L": l / L, "1/L": 1 / L, "l2/L": l * l / L, "l/L2": l / L ** 2,
            "1/L2": 1 / L ** 2, "l3/L": l ** 3 / L}[n]


def fit(y, names, Lmin):
    m = L >= Lmin
    X = np.column_stack([B(n, L[m]) for n in names]); sc = np.abs(X).max(0)
    c, *_ = np.linalg.lstsq(X / sc, y[m], rcond=None); c /= sc
    return dict(zip(names, c)), float(np.abs(y[m] - X @ c).max())


out = ["# legw_logs.py: ln L coefficient of each M' type of S(L) (C_5 response to (1/2) X at eps^3, signed X: s = +1 hops,"
       " -1 pairs); fits A + b ln L + tail, Lmin 200..400, tails (l/L,1/L,1/L2), (l2/L,l/L,1/L,l/L2,1/L2)"]
types = ["S_zchi_hop", "S_hop", "S_zchi_pair", "S_pair_c", "S_pair_a"]
combos = {"hop sector (zchi_hop + hop)": ["S_zchi_hop", "S_hop"],
          "pair sector (zchi_pair + pair_c + pair_a)": ["S_zchi_pair", "S_pair_c", "S_pair_a"],
          "Z-chi sector (zchi_hop + zchi_pair)": ["S_zchi_hop", "S_zchi_pair"],
          "chi-chi sector (hop + pair_c + pair_a)": ["S_hop", "S_pair_c", "S_pair_a"],
          "total S": types}
targets = {"S_zchi_hop": 1 / 16, "S_hop": -1 / 16, "S_zchi_pair": -1 / 16, "S_pair_c": 1 / 16 + 1 / 27, "S_pair_a": -1 / 27}
for nm in types + list(combos):
    y = s[nm] if nm in types else sum(s[k] for k in combos[nm])
    bs = []
    for tl in (["l/L", "1/L", "1/L2"], ["l2/L", "l/L", "1/L", "l/L2", "1/L2"]):
        for Lmin in (200, 300, 400):
            c, r = fit(y, ["1", "l"] + tl, Lmin)
            bs.append(c["l"])
    bs = np.array(bs)
    tgt = f"   (README: {targets[nm]:+.6f})" if nm in targets else ""
    out.append(f"  {nm:44s} b = {np.median(bs):+.8f}  [{bs.min():+.8f}, {bs.max():+.8f}]{tgt}")
out.append("Conclusion: the logs cancel within the hop sector and within the pair sector separately (and also within the Z-chi"
           " and chi-chi sectors).  A leg window with one coefficient per unit leg level for all hops and another for all pairs"
           " therefore gives no ln L in C_5 whatever the two coefficients are; only a coefficient that differs between Z-chi"
           " and chi-chi hops (or between pair types) could.")
txt = "\n".join(out)
print(txt)
os.makedirs(os.path.join(HERE, "fits"), exist_ok=True)
open(os.path.join(HERE, "fits", "legw_logs.txt"), "w").write(txt + "\n")
