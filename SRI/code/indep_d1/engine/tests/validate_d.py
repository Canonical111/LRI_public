#!/usr/bin/env python3
"""Validation ladder step (d): higher-logarithm predictions of the note (lines 719-731, 1051-1063) for the
normalized seven-kink response C7, its charge derivative d_v C7, and the eight-kink current response K8.
Input: results.json written by  py/campaign.py collect runs/pilot_logs
"""
import json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'py'))
from series import smul, sadd, Z2, Q2, show
import mpmath as mp

R = json.load(open(sys.argv[1]))['results']


def S(name):
    return {tuple(int(x) for x in k.split(',')): tuple(v) for k, v in R[name].items()}


z2 = float(mp.zeta(2))
A3, A5, A7 = S('A3_base'), S('A5_base'), S('A7_hl')
Z4, Z6 = S('Z4_base'), S('Z6_base')
A3v, A5v, A7v = S('A3_v'), S('A5_v'), S('A7_v_hl')
Z2v, Z4v, Z6v = S('Z2_v'), S('Z4_v'), S('Z6_v')
Q4, Q6 = S('Q4_base'), S('Q6_base')
Q8 = S('Q8_hl') if 'Q8_hl' in R else None

Z22 = smul(Z2, Z2, 5)
Z23 = smul(Z22, Z2, 5)
C7 = sadd((1, A7), (-1, smul(A5, Z2)), (1, smul(A3, sadd((1, Z22), (-1, Z4)), 0)), (-1, Z23), (2, smul(Z2, Z4)), (-1, Z6))
dC7 = sadd((1, A7v), (-1, smul(A5v, Z2)), (-1, smul(A5, Z2v)), (1, smul(A3v, sadd((1, Z22), (-1, Z4)))),
           (1, smul(A3, sadd((2, smul(Z2, Z2v, 5)), (-1, Z4v)))), (-3, smul(Z22, Z2v)), (2, smul(Z2v, Z4)),
           (2, smul(Z2, Z4v)), (-1, Z6v))
K8 = {} if Q8 is None else sadd((1, Q8), (-1, smul(Q6, Z2)), (1, smul(Q4, sadd((1, Z22), (-1, Z4)), 0)),
          (1, smul(Q2, sadd((-1, Z23), (2, smul(Z2, Z4, 5)), (-1, Z6)), 0)))

checks = [
    ('C7', C7, 6, 244 / 45), ('C7', C7, 5, 170 / 3), ('C7', C7, 4, 247 - 316 / 3 * z2),
    ('dvC7', dC7, 8, 0.0), ('dvC7', dC7, 7, -6416 / 315), ('dvC7', dC7, 6, -1622 / 9), ('dvC7', dC7, 5, (3848 * z2 - 8824) / 15),
    ('K8', K8, 7, -1088 / 315), ('K8', K8, 6, -664 / 15), ('K8', K8, 5, 96 * z2 - 3656 / 15),
]
allok = True
for name, ser, j, pred in checks:
    if not ser:
        print(f'[eps^0 log^{j}] {name:5s}: not available'); continue
    v, e = ser.get((0, j), (0.0, 0.0))
    ok = abs(v - pred) <= 5 * e + 1e-9 * max(1, abs(pred))
    allok &= ok
    print(f'[eps^0 log^{j}] {name:5s}: engine {v: .12f} +- {e:.1e}   note {pred: .12f}   diff {v - pred: .1e}  {"PASS" if ok else "FAIL"}')
print('ALL PASS' if allok else 'SOME FAIL')
