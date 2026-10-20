#!/usr/bin/env python3
"""The d = 3 identity of note Section 20.4 (gdr:special, the paragraph on d = 3; added for the public release):

    (2/(pi S^7)) D_L  =  Phat'  -  8 sqrt(2) N_b^4 c_{4,1}  +  32 N_b^4 c_{4,2}        at b = 3/2,

with S = sin(pi q), C = cos(pi q), q = 3/4 and the frozen-weight derivative of gdr:frozen,

    D_L = (1+C)^2 (1+2C) X_0' - (1-C)^2 (1-2C) X_{1/2}' - 2C X_T'.

Inputs (both shipped, nothing is recomputed from scratch):
  review/joint/numerics-end-to-end/samples_dps60.json  ["values"]["3"]: dX0, dXh, dXT, the b-derivatives at fixed weights
      of the samples X = N_b^4 Xi_4 (60 digits plus guard), written by dump_samples.py from L/L_general.py;
  specialize/L3_final_values.json ["values"]: Phat_prime, c1, c2 of LRI_C5_d3/wf_L3 (about 160 digits; byte-identical to
      LRI_C5_d3/wf_L3/L3_final_values.json). Phat is C63d's P(b) = -2 pi N(b) (4 c0 + 5 c2) + 6 sqrt2 pi N(b) c1 with the
      weights frozen at b = 3/2, N(b) = [Gamma(3/2 - b/2)/Gamma(b/2)]^4, and c_k are the unnormalized Fourier coefficients
      of Xi_4(t; 3/2). The normalization of the note's samples is N_b = Gamma(2q) Gamma(g)/Gamma(sigma) = Gamma(3/2) at
      b = 3/2 (sigma = g = 3/4), hence N_b^4 = Gamma(3/2)^4.
The note prints -1332.48 for the left side, Phat' = 274.55, and agreement to 1e-57 (RESULT.md: "Mac, 60 digits,
2026-10-03"; no record of that run was kept). This script is the record. Checked 2026-10-13 with mpmath 1.2.1: relative
difference 2.2e-65 (the samples carry about 65 digits).

usage: python3 public/check_DL_Phat.py [--json OUT]       (run from GFF/code/LRI_C5_general_d; well under 1 s)
"""
import argparse
import json
from pathlib import Path

import mpmath as mp

PKG = Path(__file__).resolve().parents[1]


def evaluate():
    mp.mp.dps = 80
    s = json.loads((PKG / 'review/joint/numerics-end-to-end/samples_dps60.json').read_text())['values']['3']
    v = json.loads((PKG / 'specialize/L3_final_values.json').read_text())['values']
    dX0, dXh, dXT = (mp.mpf(s[k]) for k in ('dX0', 'dXh', 'dXT'))
    q = mp.mpf(3) / 4
    S, C = mp.sin(mp.pi * q), mp.cos(mp.pi * q)
    DL = (1 + C) ** 2 * (1 + 2 * C) * dX0 - (1 - C) ** 2 * (1 - 2 * C) * dXh - 2 * C * dXT
    lhs = 2 / (mp.pi * S ** 7) * DL
    N4 = mp.gamma(mp.mpf(3) / 2) ** 4
    phat = mp.mpf(v['Phat_prime'])
    rhs = phat - 8 * mp.sqrt(2) * N4 * mp.mpf(v['c1']) + 32 * N4 * mp.mpf(v['c2'])
    rel = abs(lhs - rhs) / abs(rhs)
    return dict(lhs=mp.nstr(lhs, 40), rhs=mp.nstr(rhs, 40), rel=mp.nstr(rel, 3), Phat_prime=mp.nstr(phat, 40),
                D_L=mp.nstr(DL, 40))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--json')
    a = ap.parse_args()
    r = evaluate()
    for k, x in r.items():
        print('%-10s %s' % (k, x))
    if a.json:
        Path(a.json).write_text(json.dumps(r, indent=1) + '\n')
