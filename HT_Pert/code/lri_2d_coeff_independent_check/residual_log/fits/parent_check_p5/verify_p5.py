"""Parent check of Phase 5 (README Sec. 12) from the exact output files only."""
import glob, json, os, sys
from fractions import Fraction as Fr
ROOT = sys.argv[1]
def load(d, scheme):
    out = {}
    for f in glob.glob(os.path.join(ROOT, d, "*.json")):
        j = json.load(open(f))
        if scheme not in j["schemes"]: continue
        L = j["meta"]["args"]["L"]
        out.setdefault(L, {}).update({k: Fr(x) for k, x in j["schemes"][scheme]["values"].items() if x is not None})
        out[L]["_bad"] = set(j["schemes"][scheme]["bad"])
    return out
wcs = load("ce_wc/out_wcs", "Wcs"); wc = load("ce_wc/out_local", "Wc")
X = load("ce_wc/out_wcs4x", "Wcs4X"); Xall = load("ce_wc/out_wcs4x", "Wcs4Xall"); A = load("ce_wc/out_wcs4c", "Wcs4")
def R(v, dn, n):
    prim = 1 if dn.startswith("odd") else 2; k = f"Ed|{dn}|{n}"
    if k not in v or k in v["_bad"]: return None
    return v[k] - v[f"E|{prim}|{n}"]
print("# invariance vs Wcs: C0..C5, r1..4, g1..4, E|p|0..4, R2,R3 of every desc; and whether r5,g5,C6 differ")
for name, S in (("Wcs4X", X), ("Wcs4Xall", Xall), ("A", A)):
    for L in sorted(S):
        if L not in wcs: print(name, L, "no Wcs"); continue
        keys = [f"C|{n}" for n in range(6)] + [f"r|{k}" for k in range(1, 5)] + [f"g|{k}" for k in range(1, 5)]
        keys += [f"E|{p}|{n}" for p in range(4) for n in range(5)]
        same = all(S[L][k] == wcs[L][k] for k in keys)
        dsame = all(R(S[L], dn, n) == R(wcs[L], dn, n) for dn in ("odd1","odd2","odd3","even1","even2") for n in (2, 3)
                    if R(wcs[L], dn, n) is not None)
        r5 = S[L]["r|5"] != wcs[L]["r|5"]; c6 = S[L]["C|6"] != wcs[L]["C|6"]
        r5u = S[L]["R5"] if False else None
        print(f"{name:8s} L={L:2d} C0-5,r,g<=4,E<=4 same: {same}  R2,R3 same: {dsame}  r5 differs: {r5}  C6 differs: {c6}")
def bf(L, a):
    for pat in (f"tag4bf_L{L}_a{a}.json", f"tag4_L{L}_a{a}.json", f"spec4_L{L}_a{a}.json"):
        f = os.path.join(ROOT, "results/tag", pat)
        if os.path.exists(f):
            j = json.load(open(f))
            if "nu0_0" in j and len(j["nu0_0"]["R"]) > 4: return Fr(j["nu0_0"]["R"][4]), pat
    return None, None
print("\n# R4: Wcs | Wcs4X | A | budget-free (source)")
for dn, a in (("odd1", 1), ("odd2", 2), ("odd3", 3)):
    for L in sorted(X):
        b, src = bf(L, a)
        f = lambda x: "    n/a  " if x is None else f"{float(x):+.5f}"
        r = [R(wcs.get(L, {"_bad": set()}), dn, 4), R(X[L], dn, 4), R(A.get(L, {"_bad": set()}), dn, 4) if L in A else None]
        gap = "" if (b is None or r[1] is None) else f"  gap X-bf {float(r[1]-b):+.5f}  closed {float((r[0]-r[1])/(r[0]-b)):.3f}"
        ex = "  (==bf exactly)" if (b is not None and r[1] == b) else ""
        print(f"{dn} L={L:2d} Wcs {f(r[0])} X {f(r[1])} A {f(r[2])} bf {f(b)} [{src}]{gap}{ex}")
print("\n# R4 phi^2 desc level 2 and R5(chi_11): Wcs vs Wcs4X")
for L in sorted(X):
    print(f"L={L:2d} even1 R4 Wcs {float(R(wcs[L],'even1',4)):+.4f} X {float(R(X[L],'even1',4)):+.4f} | odd1 R5 Wcs "
          f"{float(R(wcs[L],'odd1',5)):+.5f} X {float(R(X[L],'odd1',5)):+.5f} same {R(wcs[L],'odd1',5)==R(X[L],'odd1',5)}")
print("\n# C6: Wc | Wcs | A | Wcs4X | Wcs4Xall ; r5,g5 at L=16")
for L in sorted(X):
    row = [wc.get(L, {}).get("C|6"), wcs[L]["C|6"], A.get(L, {}).get("C|6"), X[L]["C|6"], Xall[L]["C|6"]]
    print(f"L={L:2d} " + "  ".join("   n/a    " if v is None else f"{float(v):.5f}" for v in row))
print("r5,g5 L=16: Wcs", float(wcs[16]["r|5"]), float(wcs[16]["g|5"]), " Wcs4X", float(X[16]["r|5"]), float(X[16]["g|5"]))
