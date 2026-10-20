#!/usr/bin/env python3
"""Exact check that the note's closed forms are mutually consistent under eq:conversion:
C7 = 4 D4 - T3 - T2^2 + C3 C5 / 2, with T3 = C6/4.  Uses only even-zeta reductions
z2^2 = 5/2 z4, z2*z4 = 7/4 z6, z2^3 = 35/8 z6 (exact)."""
import sympy as s, json
from pathlib import Path
z2, z3, z4, z5, z6 = s.symbols('z2 z3 z4 z5 z6')
R = s.Rational
C3 = R(39, 16) + 2 * z2
T2 = 2 - 2 * z2 - 4 * z3
D2 = R(5, 2) + 2 * z2
D3 = R(21, 4) - 13 * z2 + 11 * z3 + 11 * z4
C5 = R(11249, 1024) - R(361, 16) * z2 + 24 * z3 + R(49, 2) * z4
C6 = 26 - 38 * z2 + 104 * z3 - 80 * z4 - 272 * z5 + 112 * z2 * z3
D4 = 13 - R(179, 8) * z2 + R(47, 2) * z3 - R(493, 8) * z4 + 289 * z5 - 130 * z2 * z3 + R(499, 4) * z6 - 76 * z3**2
C7note = (R(1798583, 32768) - R(90637, 1024) * z2 + R(453, 4) * z3 - R(16835, 64) * z4 + 1224 * z5
          - 540 * z2 * z3 + R(4335, 8) * z6 - 320 * z3**2)
def red(ex):
    ex = s.expand(ex)
    ex = s.expand(ex.subs(z2**3, R(35, 8) * z6))
    ex = s.expand(ex.subs(z2**2, R(5, 2) * z4))
    ex = s.expand(ex.subs(z2 * z4, R(7, 4) * z6))
    return ex
res = {
 'C3 == D2-1/16': red(C3 - (D2 - R(1, 16))) == 0,
 'C5 == 2D3 - T2/2 + (D2-1/16)^2/4': red(C5 - (2 * D3 - T2 / 2 + (D2 - R(1, 16))**2 / 4)) == 0,
 'C7(note) == 4D4 - C6/4 - T2^2 + C3*C5/2': red(C7note - (4 * D4 - C6 / 4 - T2**2 + C3 * C5 / 2)) == 0,
 'C7 - 4 D4 (known additive)': str(red(C7note - 4 * D4)),
}
print(json.dumps(res, indent=1))
(Path(__file__).resolve().parent.parent / 'out' / 'closed_form_consistency.json').write_text(json.dumps(res, indent=1))
