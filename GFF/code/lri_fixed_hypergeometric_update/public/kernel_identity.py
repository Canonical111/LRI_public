#!/usr/bin/env python3
"""Exact check of the Barnes kernel identity, note Section 10, eq. (fp:eq:kernel) (new check, 2026-10-13).

With C = csc(pi s), D = cot(pi s) and
    S(s) = tan(pi s + pi/4) {[1 - cot(pi s/2)]^7 - [1 + tan(pi s/2)]^7},
the note states
    R(s) = S(s) - 16 sqrt2 csc[pi(s - 1/4)]
         = -128C + 160C^3 + 192C^5 - 128C^7 - 16DC - 400DC^3 + 192DC^5,
and that 'the accompanying SymPy code verifies this exactly after replacing tan(pi s/2) by an indeterminate'.
That code is not in the research bundle; this script is a fresh implementation of the same check. With
u = tan(pi s/2): sin(pi s) = 2u/(1+u^2), cos(pi s) = (1-u^2)/(1+u^2), and
csc[pi(s - 1/4)] = sqrt2/(sin(pi s) - cos(pi s)). Both sides become rational functions of u (times sqrt2
constants), and their difference must cancel identically. Usage: kernel_identity.py OUT.json. About 1 s.
"""
import json
import sys
from pathlib import Path

import sympy as sp


def main():
    u = sp.symbols('u')
    sin, cos = 2 * u / (1 + u ** 2), (1 - u ** 2) / (1 + u ** 2)
    tan = sin / cos
    C, D = 1 / sin, cos / sin
    S = (tan + 1) / (1 - tan) * ((1 - 1 / u) ** 7 - (1 + u) ** 7)
    R = S - 16 * sp.sqrt(2) * sp.sqrt(2) / (sin - cos)
    target = -128 * C + 160 * C ** 3 + 192 * C ** 5 - 128 * C ** 7 - 16 * D * C - 400 * D * C ** 3 + 192 * D * C ** 5
    diff = sp.cancel(sp.together(R - target))
    out = {'identity': 'R(s) = S(s) - 16 sqrt2 csc[pi(s-1/4)] = -128C+160C^3+192C^5-128C^7-16DC-400DC^3+192DC^5',
           'substitution': 'u = tan(pi s/2)', 'difference': str(diff), 'exact': diff == 0}
    Path(sys.argv[1]).write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps(out, indent=2))
    sys.exit(0 if diff == 0 else 1)


if __name__ == '__main__':
    main()
