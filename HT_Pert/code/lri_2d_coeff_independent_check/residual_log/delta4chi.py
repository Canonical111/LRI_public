#!/usr/bin/env python3
"""delta^(4)_chi(L): the eps^4 leg window calibrated on a chi line (WINDOW_SPEC Sec. 2.5b, README Sec. 12).

The window adds to D^(4) the term (1/2)[delta4chi(L) X_0 + delta^(3)(L) X_1] (X = M'^{+-}_nu of Sec. 2.5a).  On chi_aa its
first-order effect is 4a [w0 delta4chi + w1 delta^(3)], w(eps) = [(x)_a/a!]^2 = w0 + w1 eps + ...  The coefficient is fixed
by the chi_11 line: with the window, the charged chi_11 line must have the eps^4 self-energy of the same line with its
external legs budget-free (tagged, brute_desc_tag4.py --nu 0,0).  Hence

    delta4chi(L) = [ (Rbf_4(L) - R_4^Wcs(L)) / (4a) - w1 delta^(3)(L) ] / w0        (a = 1),

with Rbf_4 the budget-free residual (exact, tagged) and R_4^Wcs the ce_wc scheme-Wcs residual (exact).  With --a 2 or 3
the same formula gives the coefficient the chi_22 / chi_33 lines would require (linearity test).
usage: python3 delta4chi.py [--a 1] [--runs]   (--runs prints 'L:delta3:delta4chi' for jobs/run_ce_wcs4.sbatch)"""
import argparse
import glob
import json
import os
from fractions import Fraction as Fr

import delta3 as d3

HERE = os.path.dirname(os.path.abspath(__file__))
D3_SMALL = {2: Fr(-73, 7776), 4: Fr(-15071, 1105920)}


def wcoef(a):
    """w_aa(eps) = [(x)_a/a!]^2, x = 1/2 - eps/4: (w0, w1)."""
    p = [Fr(1), Fr(0)]
    for i in range(a):
        f = [Fr(2 * i + 1, 2 * (i + 1)), Fr(-1, 4 * (i + 1))]
        p = [p[0] * f[0], p[0] * f[1] + p[1] * f[0]]
    return p[0] ** 2, 2 * p[0] * p[1]


def delta3_table():
    out = dict(D3_SMALL)
    for f in glob.glob(os.path.join(HERE, "results", "tag", "tag_L*_a1_phi2_2_real.json")):
        j = json.load(open(f))
        out[j["L"]] = d3.delta_from(j, 1)
    return out


def ce_R(L, dn, n, scheme="Wcs", dirs=("ce_wc/out_wcs",)):
    for d in dirs:
        for f in glob.glob(os.path.join(HERE, d, "*.json")):
            j = json.load(open(f))
            if j["meta"]["args"]["L"] != L or scheme not in j["schemes"]:
                continue
            v = j["schemes"][scheme]["values"]
            a = int(dn[-1])
            prim = 1 if dn.startswith("odd") else 2
            k = f"Ed|{dn}|{n}"
            if v.get(k) is None:
                return None
            return Fr(v[k]) - Fr(v[f"E|{prim}|{n}"]) - (2 * a if n == 0 else 0)
    return None


def bf_R4(L, a):
    for pat in (f"tag4bf_L{L}_a{a}.json", f"tag4_L{L}_a{a}.json"):
        f = os.path.join(HERE, "results", "tag", pat)
        if os.path.exists(f):
            j = json.load(open(f))
            if "nu0_0" in j:
                return Fr(j["nu0_0"]["R"][4])
    return None


def table(a):
    d3t = delta3_table()
    w0, w1 = wcoef(a)
    rows = []
    for L in range(2, 18, 2):
        bf, rw = bf_R4(L, a), ce_R(L, f"odd{a}", 4)
        if bf is None or rw is None or L not in d3t:
            continue
        d4 = ((bf - rw) / (4 * a) - w1 * d3t[L]) / w0
        rows.append((L, d3t[L], d4, bf, rw))
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", type=int, default=1)
    ap.add_argument("--runs", action="store_true")
    x = ap.parse_args()
    rows = table(x.a)
    if x.runs:
        print(" ".join(f"{L}:{d3v}:{d4}" for L, d3v, d4, bf, rw in rows))
    else:
        for L, d3v, d4, bf, rw in rows:
            print(f"L={L:2d}  delta3={float(d3v):+.7f}  delta4chi(a={x.a})={float(d4):+.7f}  Rbf_4={float(bf):+.7f}  "
                  f"R4_Wcs={float(rw):+.7f}")
