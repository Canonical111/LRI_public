import glob, json, os, sys
from fractions import Fraction as Fr
import numpy as np
R = sys.argv[1]
out = {}
for f in glob.glob(os.path.join(R, "ce_wc/out_wcs/*.json")):
    j = json.load(open(f)); L = j["meta"]["args"]["L"]
    out[L] = {k: Fr(x) for k, x in j["schemes"]["Wcs"]["values"].items() if x is not None}
for dn in ("odd1", "odd2", "odd3"):
    Ls = np.array([l for l in sorted(out) if l >= 6 and f"Ed|{dn}|3" in out[l]], float)
    y = np.array([float(out[int(l)][f"Ed|{dn}|3"] - out[int(l)]["E|1|3"]) for l in Ls])
    print(dn, dict(zip(Ls.astype(int), y)))
    # predict the last point from the others, free limit vs zero limit
    for name, cols in [("a+b/L+c/L2", lambda L: [L**0, 1/L, 1/L**2]), ("b/L+c/L2+d/L3 (a=0)", lambda L: [1/L, 1/L**2, 1/L**3]),
                       ("a+b/L2+c/L3", lambda L: [L**0, 1/L**2, 1/L**3]), ("b/L2+c/L3+d/L4 (a=0)", lambda L: [1/L**2, 1/L**3, 1/L**4])]:
        m = Ls < 14
        A = np.column_stack(cols(Ls[m])); p = np.linalg.lstsq(A, y[m], rcond=None)[0]
        pred = np.column_stack(cols(Ls[~m])) @ p
        print(f"   {name:22s} fit L=6..12 -> predicts L=14 {pred[0]:+.6f} (actual {y[~m][0]:+.6f}, miss {pred[0]-y[~m][0]:+.1e}); limit {p[0] if 'a=0' not in name else 0:+.6f}")
