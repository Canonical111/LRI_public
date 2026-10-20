#!/usr/bin/env python3
"""Closed forms on the full production range (PLAN.md A5): Delta R4 (engine, cancellation-free) = H_odd(L-1)/2916
<= 1e-14 relative and Delta R5 engine (cancellation-free) vs closed form <= 1e-14 relative at every even L <= Lmax (default 2000), plus the
own g2D C4 window sum vs fast(L) <= 1e-12.  Only two- and three-vertex chains are evaluated (cluster job).
usage: python3 validate/v7_closed.py [--Lmax 2000]"""
import argparse
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "vendor"))
import assemble5                  # noqa: E402
import exact_fast                 # noqa: E402
import windows5 as w5             # noqa: E402
from lib5.common import FUNCTIONALS   # noqa: E402
from lib5.series import Series5   # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--Lmax", type=int, default=2000)
    a = ap.parse_args()
    Lmax = a.Lmax
    ser = Series5(Lmax)
    res = assemble5.compute(Lmax, 2, verbose=False)          # r2, g2 (outer couplings) only
    V0, V1 = ("V", 0), ("V", 1)
    de0 = w5.p_shells((V0, V0), ((1, 0),), Lmax, ser)[0]
    de1 = 2 * w5.p_shells((V1, V0), ((1, 0),), Lmax, ser)[0] - 0.25 * w5.p_shells((V0, V0), ((2, 1),), Lmax, ser)[0]
    hp = w5.p_shells((V0, V0), ((2, 0),), Lmax, ser)
    dR4 = w5.delta_R4_engine(de0, hp[0], Lmax)
    dR5c = w5.delta_R5_closed(res["g2"], Lmax)
    dR5e = w5.delta_R5_engine(Lmax, res, ser, de0, de1, hp[0])
    g2D = w5.window_functional(hp, de0, FUNCTIONALS["C"], Lmax)
    Ls = range(2, Lmax + 1, 2)
    e4 = max(abs(dR4[L] - w5.h_odd(L - 1) / 2916.0) / (w5.h_odd(L - 1) / 2916.0) for L in Ls)
    e5 = max(abs(dR5e[L] - dR5c[L]) / abs(dR5c[L]) for L in Ls)
    eg = max(abs(g2D[L] - exact_fast.fast(L)) for L in Ls)
    ok = len(dR4) == len(dR5c) == len(dR5e) == Lmax // 2 and e4 <= 1e-14 and e5 <= 1e-14 and eg <= 1e-12
    ok = ok and all(np.isfinite([dR4[L], dR5c[L], dR5e[L], g2D[L]]).all() for L in Ls)
    print(f"Delta R4 engine vs H_odd/2916 (L <= {Lmax}): max rel {e4:.2e}")
    print(f"Delta R5 engine vs closed form (L <= {Lmax}): max rel {e5:.2e}")
    print(f"own g2D C4 window vs fast(L) (L <= {Lmax}): max abs {eg:.2e}")
    print("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
