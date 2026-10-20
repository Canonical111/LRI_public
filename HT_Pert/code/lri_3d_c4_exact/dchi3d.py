#!/usr/bin/env python3
"""Leading-order chi-attached sunset window of the 2D derivation (residual_log README Sec. 2.4, 4.1) applied to the
3D model, and its eps^4 shift of C_4 (diagnostic test only):

    D_chi = -(1/2) (dr2/dL) {N, M'},   M' = parts of M = <:phi^2:> with at least one chi leg,
    D(s -> s') = -(1/2) r2'(L) (N_s + N_s') <s'|M'|s>   (N = bath level operator).

It enters at eps^3 through 2 g1 <V R D> (shifts r3, g3; C3 must stay unchanged) and at eps^4 through
    g1^2 <V R D R V> + 2 g1 [g1 <V R V R D> - g1 V_pp <V R^2 D> - (1/4) <V R (P-p) R D>] + 2 g1 (dr3 <V R M> + dg3 <V R V>).
r2'(L) = (r2(L+2) - r2(L-2))/4 from the exact tuned r2 (one-sided at the ends).
In 3D r2 ~ L^(3/2), so the linear form is only the leading term in N/L (hard spectators are not treated exactly).

usage: python3 dchi3d.py --Lmax 200 --out results/dchi_L200.npz"""
import argparse
import os
from fractions import Fraction as Fr

import numpy as np

import c4lib3d as lib


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--Lmax", type=int, required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    B = lib.Basis(a.Lmax)
    S = a.Lmax // 2
    G = 1.0 / 3.0
    PI, R_OF, G_OF = lib.PI, lib.R_OF, lib.G_OF
    Vpp = lambda p: Fr(p * (p - 1), 2)
    def M_has_chi(kinds):
        iv = kinds.index("M")
        K = len(kinds)
        return lambda n: lib.legs_of(n, K)[iv] >= 1

    c = lambda kinds, ops, **kw: lib.chain_entries(B, kinds, ops, pattern_filter=M_has_chi(kinds) if "M" in kinds
                                                   else None, **kw)
    VV_R = lib.chain_entries(B, "VV", [(1, 0)])
    MV_R = lib.chain_entries(B, "MV", [(1, 0)])
    r2 = VV_R.proj(R_OF) * G * G
    rp = np.gradient(r2, 2.0 * np.arange(S + 1))         # dr2/dL per unit level
    k = -0.5 * rp
    VRD = c("MV", [(1, 0, 1)]).scale(k)                                         # <V R D>, D acts first on |p>
    dX3 = VRD.scale(2 * G)
    z = lambda v: v if v is not None else np.zeros(S + 1)          # an exactly vanishing projection
    dr3, dg3, dC3 = z(dX3.proj(R_OF)), z(dX3.proj(G_OF)), z(dX3.proj(PI))
    VRDRV = (c("VMV", [(1, 0, 1), (1, 0, 0)]) + c("VMV", [(1, 0, 0), (1, 0, 1)])).scale(k)
    VRVRD = c("MVV", [(1, 0, 1), (1, 0, 0)]).scale(k)
    VR2D = c("MV", [(2, 0, 1)]).scale(k)
    VRPRD = c("MV", [(2, 1, 1)]).scale(k)
    dX4 = (VRDRV.scale(G * G) + VRVRD.scale(2 * G * G) + VR2D.pfac(lambda p: -Vpp(p)).scale(2 * G * G)
           + VRPRD.scale(-0.5 * G) + MV_R.scale(2 * G * dr3) + VV_R.scale(2 * G * dg3))
    parts = dict(VRDRV=z(VRDRV.scale(G * G).proj(PI)), VRVRD=z(VRVRD.scale(2 * G * G).proj(PI)),
                 VR2D=z(VR2D.pfac(lambda p: -Vpp(p)).scale(2 * G * G).proj(PI)),
                 VRPRD=z(VRPRD.scale(-0.5 * G).proj(PI)),
                 retune=z((MV_R.scale(2 * G * dr3) + VV_R.scale(2 * G * dg3)).proj(PI)))
    dC4 = z(dX4.proj(PI))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    np.savez(a.out, L=2 * np.arange(S + 1), dC4chi=dC4, dC3chi=dC3, r2=r2, r2p=rp,
             **{"part_" + k_: v for k_, v in parts.items()})
    print("max |dC3| (must vanish): %.1e" % np.max(np.abs(dC3)))
    for j in list(range(0, S + 1, max(1, S // 15))):
        print(f"L={2 * j:5d} dC4chi={dC4[j]:+.12f} r2={r2[j]:.6f} r2'={rp[j]:.6f}  "
              + " ".join(f"{k_}={v[j]:+.5f}" for k_, v in parts.items()))


if __name__ == "__main__":
    main()
