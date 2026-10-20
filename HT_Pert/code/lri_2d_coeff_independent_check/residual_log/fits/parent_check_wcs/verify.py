"""Parent-side check of the Wcs claims (README Sec. 11) from the exact output files only."""
import glob, json, os, sys
from fractions import Fraction as Fr
import numpy as np
R = sys.argv[1]
def load(pattern, scheme):
    out = {}
    for f in glob.glob(os.path.join(R, pattern)):
        j = json.load(open(f))
        if scheme not in j["schemes"]:
            continue
        L = j["meta"]["args"]["L"]
        v = {k: Fr(x) for k, x in j["schemes"][scheme]["values"].items() if x is not None}
        out.setdefault(L, {}).update(v)
        out[L]["_bad"] = j["schemes"][scheme]["bad"]
        if "delta3" in j["meta"]["args"] and j["meta"]["args"]["delta3"] is not None:
            out[L]["_delta3"] = Fr(j["meta"]["args"]["delta3"])
    return out
wcs = load("ce_wc/out_wcs/*.json", "Wcs")
wc = load("ce_wc/out_local/*.json", "Wc")
print("Wcs L:", sorted(wcs), " Wc L:", sorted(wc))
# A. delta^(3)(L) recomputed from tagged-phi files (own code), vs the value the Wcs run used; r, g consistency
print("\n# A. delta3 from tagged phi vs run input; r,g of tag run vs Wc")
dl = {}
for f in sorted(glob.glob(os.path.join(R, "results/tag/tag_L*_a1_phi2_2_real.json"))):
    d = json.load(open(f)); L = int(d["L"])
    c13 = [Fr(x) for x in d["c1_3"]]
    r3 = Fr(d["r"][3])
    tag3 = Fr(d["phi2_2_real"]["c1tag"][3]) - 2 * r3
    delta = (c13[(L - 2) // 2] - tag3) / 4
    dl[L] = delta
    same_rg = None
    if L in wc:
        same_rg = all(Fr(d["r"][k]) == wc[L][f"r|{k}"] and Fr(d["g"][k]) == wc[L][f"g|{k}"] for k in range(4))
    used = wcs.get(L, {}).get("_delta3")
    print(f"L={L:2d} delta3={float(delta):+.7f} used_in_Wcs_run={'n/a' if used is None else used == delta}  r,g(0..3)==Wc: {same_rg}")
# B. T1
print("\n# B. T1: C0..C4, r1..3, g1..3 identical Wcs vs Wc")
for L in sorted(wcs):
    if L not in wc: print(L, "no Wc"); continue
    keys = [f"C|{n}" for n in range(5)] + [f"r|{k}" for k in range(1, 4)] + [f"g|{k}" for k in range(1, 4)]
    print(f"L={L:2d}", all(wcs[L][k] == wc[L][k] for k in keys), " r4 same?", wcs[L]["r|4"] == wc[L]["r|4"])
# C. T2 shift
print("\n# C. C5^Wcs - C5^Wc vs delta3(L) S(L)")
S = np.load(os.path.join(R, "results/legw/legw_L1000.npz"))
Smap = dict(zip(S["L"].tolist(), S["S"].tolist()))
for L in sorted(wcs):
    if L not in wc or L not in Smap: continue
    dC5 = float(wcs[L]["C|5"] - wc[L]["C|5"])
    pred = float(wcs[L]["_delta3"]) * Smap[L] if "_delta3" in wcs[L] else float("nan")
    print(f"L={L:2d} dC5={dC5:+.12e} delta*S={pred:+.12e} diff={dC5-pred:+.2e}  dC6={float(wcs[L]['C|6']-wc[L]['C|6']):+.5f}")
# D. T3 residuals
print("\n# D. R_n = [eps^n](E_desc - E_prim) - 2a delta_n0 ; Wcs [Wc]")
def res(v, dn, n):
    a = int(dn[-1]); prim = 1 if dn.startswith("odd") else 2
    k = f"Ed|{dn}|{n}"
    if k not in v or k in v["_bad"]: return None
    return float(v[k] - v[f"E|{prim}|{n}"])
for dn in ("odd1", "odd2", "odd3", "even1", "even2"):
    for L in sorted(wcs):
        r = [res(wcs[L], dn, n) for n in (2, 3, 4)]
        w = [res(wc.get(L, {"_bad": []}), dn, n) if L in wc else None for n in (2, 3, 4)]
        if r[1] is None: continue
        f = lambda x: "   n/a    " if x is None else f"{x:+.6f}"
        print(f"{dn} L={L:2d}  R2={f(r[0])} R3={f(r[1])} [{f(w[1])}]  R4={f(r[2])} [{f(w[2])}]")
    print()
# even1 shift ratio
print("# even1 R3 shift / delta3:", [ (L, round(float((wcs[L]['Ed|even1|3']-wc[L]['Ed|even1|3'])/wcs[L]['_delta3']),6)) for L in sorted(wcs) if L in wc and 'Ed|even1|3' in wcs[L] and '_delta3' in wcs[L]])
