#!/usr/bin/env python3
"""Regression tests of src/compare_engine.py --offset-fit (GLS version).  Local, ~1 minute.

  1. exact synthetic two-kink series (tests/synthetic_engine*.json): PASS, offsets ~ 0
  2. phase-1 injections (tests/perturbed_engine.json): A3_v [eps^0 l^1] +1e-6 and Q4 [eps^0 l^0] +1e-4 -> OFFSET,
     recovered shifts -1e-6 / -1e-4
  3. the reviewer's injections into the engine's complete validation series (review/perturbed_engine_n5n6.json):
     A5 +1e-3, A5_v +1e-2, Q6 +0.1 -> OFFSET (the phase-1 tool returned OK for all); Z6 (K = 0) +1 -> not PASS
  4. the reviewer's deliberately wrong A7_v / Q8 series (review/synthetic_q8_a7.json) -> not PASS
     (the phase-1 tool returned OK with chi2/dof = 8.9e25)
  5. corrupted complete series (validation_d): an exact higher-log coefficient of A5 off by 1e-3 relative, and
     all coefficients of Q6 scaled by 1.001 -> MODEL-FAIL
  6. partial engine series (pilot5 format) -> INCONCLUSIVE or UNTESTABLE, never PASS/OFFSET
  7. injection linearity: an injection delta into c00 moves d0 by exactly -delta and leaves chi2 unchanged
"""
import copy
import json
import os
import sys

import mpmath as mp

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '..', 'src')
sys.path.insert(0, SRC)
import compare_engine as ce  # noqa: E402

ENG = os.path.join(HERE, '..', '..', 'engine')
mp.mp.dps = 50
TAB = json.load(open(os.path.join(HERE, '..', 'results', 'direct_table.json')))
FAILS = []


def check(cond, msg):
    print(('PASS  ' if cond else 'FAIL  ') + msg)
    if not cond:
        FAILS.append(msg)


def run(path_or_eng, name, merge=False):
    eng = ce.load_engine([path_or_eng], merge=merge) if isinstance(path_or_eng, str) else path_or_eng
    return ce.offset_test(TAB, name, eng[name])


def main():
    # 1
    for f in ('synthetic_engine.json', 'synthetic_engine2.json'):
        eng = ce.load_engine([os.path.join(HERE, f)])
        for nm in eng:
            r = ce.offset_test(TAB, nm, eng[nm])
            check(r['verdict'] == 'PASS', '%s %s: exact series -> %s (d0 = %.2e)' % (f, nm, r['verdict'],
                                                                                    float(r['central']['d0'])))
    # 2
    r = run(os.path.join(HERE, 'perturbed_engine.json'), 'A3_v')
    c = r['central']
    check(r['verdict'] == 'OFFSET' and abs(float(c['d1']) + 1e-6) < 1e-8,
          'A3_v c01 +1e-6 -> %s, d1 = %.4e +- %.1e' % (r['verdict'], float(c['d1']), float(c['u1'])))
    r = run(os.path.join(HERE, 'perturbed_engine.json'), 'Q4_base')
    c = r['central']
    check(r['verdict'] == 'OFFSET' and abs(float(c['d0']) + 1e-4) < 1e-5,
          'Q4 c00 +1e-4 -> %s, d0 = %.4e +- %.1e' % (r['verdict'], float(c['d0']), float(c['u0'])))
    # 3
    pert = os.path.join(HERE, '..', 'review', 'perturbed_engine_n5n6.json')
    for nm, want in (('A5_base', 'OFFSET'), ('A5_v', 'OFFSET'), ('Q6_base', 'OFFSET')):
        r = run(pert, nm)
        c = r['central']
        check(r['verdict'] == want, 'reviewer injection %s -> %s (pull0 %.1f, X2 %.3g)' % (
            nm, r['verdict'], float(c['pull0']), float(c['joint_X2'])))
    r = run(pert, 'Z6_base')
    check(r['verdict'] != 'PASS', 'reviewer injection Z6_base +1 (K = 0) -> %s' % r['verdict'])
    # 4
    syn = os.path.join(HERE, '..', 'review', 'synthetic_q8_a7.json')
    for nm in ('A7_v', 'Q8_base'):
        r = run(syn, nm)
        check(r['verdict'] != 'PASS', 'reviewer garbage series %s -> %s' % (nm, r['verdict']))
    # 5
    vd = ce.load_engine([os.path.join(ENG, 'results', 'validation_d_inputs.json')])
    e = copy.deepcopy(vd['A5_base'])
    c, err = e['terms'][(0, 4)]
    e['terms'][(0, 4)] = (c * (1 + mp.mpf('1e-3')), err)
    r = ce.offset_test(TAB, 'A5_base', e)
    check(r['verdict'] == 'MODEL-FAIL', 'A5 exact [eps^0 l^4] x (1 + 1e-3) -> %s' % r['verdict'])
    e = copy.deepcopy(vd['Q6_base'])
    e['terms'] = {t: (c * mp.mpf('1.001'), er) for t, (c, er) in e['terms'].items()}
    r = ce.offset_test(TAB, 'Q6_base', e)
    check(r['verdict'] == 'MODEL-FAIL', 'Q6 all coefficients x 1.001 -> %s' % r['verdict'])
    # 6
    p5 = ce.load_engine([os.path.join(ENG, 'runs', 'pilot5', 'results.json')])
    for nm in ('A5_base', 'EQ6_base', 'A7_base', 'A7_v', 'Q8_base', 'Z6_base'):
        r = ce.offset_test(TAB, nm, p5[nm])
        check(r['verdict'] in ('INCONCLUSIVE', 'UNTESTABLE'), 'pilot5 partial %s -> %s' % (nm, r['verdict']))
    # 7
    e0 = vd['A5_v']
    r0 = ce.offset_test(TAB, 'A5_v', e0)
    e1 = copy.deepcopy(e0)
    c, err = e1['terms'][(0, 0)]
    e1['terms'][(0, 0)] = (c + mp.mpf('0.0123'), err)
    r1 = ce.offset_test(TAB, 'A5_v', e1)
    sh = r1['central']['d0'] - r0['central']['d0']
    check(abs(sh + mp.mpf('0.0123')) < mp.mpf('1e-30') and abs(r1['central']['chi2_dof'] - r0['central']['chi2_dof'])
          < mp.mpf('1e-30'), 'linearity: d0 shift %s for delta 0.0123' % mp.nstr(sh, 20))
    print('\n%d failures' % len(FAILS))
    sys.exit(1 if FAILS else 0)


if __name__ == '__main__':
    main()
