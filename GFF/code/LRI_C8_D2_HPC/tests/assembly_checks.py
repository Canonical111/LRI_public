#!/usr/bin/env python3
"""The order-8 assembly through the vendored module (PLAN component E, F; G2b on the Mac, J-VAL-3 on a cluster).

A-ASM-2, order-7 regression: the vendored coefficients(vals, B2, 7, 1) is np.array_equal to C7(2)'s
  reference/c7d2_hpc_a55958f/tools/assemble.py:coefficients and to reference/LRI_C7_d2_progress/code/analyze.py on 96
  synthetic jet sets (seed 51892) and on the 2026 production means, with B2 given as 6 or 7 entries; the Jacobians
  are equal.
A-ASM-4, order-8 gates, on the 2026 production means extended by synthetic new slots and at 16 random points:
  top_slot_gate ((-1, +3)/3^(L+1) to 1e-12, L = 3..8, no lower-order dependence), loop7_gate ((-16A, 42A)/19683 with
  A = -B2[0]/6 = 4 log 2, to 1e-12), the float affinity_gate of loops 5..8 (1e-10), and a test that loops=[4,5] fails;
  Fraction mode: the 210 exact second differences over loops 5..8 vanish, coefficients equals ms8_value in 16 random
  constant-coefficient cases and reproduces C4, C5, c6:RGassembly and ms7 (C7(2)'s check_assembly.py), and ms8_rows
  equals the RECON section 1.1 polynomial embedded below. tools/assemble.py evaluates the gates as hard gates on
  synthetic data built on the production means, and an injected violation (a monkeypatched coefficients) raises.
  --exact: the vendored exact_check.py with LRI_ROOT = the pinned fixture tree; every key of
  tests/fixtures/exact_check_keys.json classed exact is present and equal to exact_check_results.json, every float
  diagnostic meets its bound, provenance keys are written to --provenance and not compared, and an unclassified or
  new key fails (R09).
A-ASM-5, reporting on synthetic data with injected values: the lower-order pulls C3..C7 with both SEs, the power null
  rows 3..7 and the reported order 8 (POWER_PROTOCOL PP1-PP10, one test each), error_by_loop summing to Var(C8), the
  half streams and the bootstrap against hand values, an injected 4-sigma C7 deviation printing a FLAG line, and a
  test-only result holding no physical number.
Usage: python3 -B tests/assembly_checks.py [--exact] [--output FILE] [--provenance FILE]"""
from __future__ import annotations

import argparse
import ast
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from fractions import Fraction as F
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import assemble as asm  # noqa: E402
import verify_result as vr  # noqa: E402

PROD = ROOT / 'reference/c7d2_production_2026'
KEYS = ROOT / 'tests/fixtures/exact_check_keys.json'
# RECON.md section 1.1 (LRI_C8_D2_HPC_loop/RECON.md:91-95, 2026-10-03): C62d's sympy derivation, embedded here.
RECON_MS8 = """3c8 - b8 + 42A c7 - 16A b7 + 324A^2 c6 - 144A^2 b6 + 3b3 b6 - 6b3 c6 - 3b6 c3
 + 1800A^3 c5 - 960A^3 b5 + 54A b3 b5 - 90A b3 c5 - 54A b5 c3 + 3b4 b5 - 5b4 c5 - 4b5 c4
 + 82368A^7 - 25344A^5 b3 + 28512A^5 c3 - 5280A^4 b4 + 7920A^4 c4 + 1980A^3 b3^2
 - 3960A^3 b3 c3 + 540A^2 b3 b4 - 720A^2 b3 c4 - 540A^2 b4 c3 - (100/3)A b3^3 + 90A b3^2 c3
 + 27A b4^2 - 72A b4 c4 - 5b3^2 b4 + 6b3^2 c4 + 9b3 b4 c3"""


def load_reference(path: Path, name: str, extra_path: Path | None = None):
    """Import a delivered C7(2) module from its source without writing bytecode; its own `common` is used."""
    import importlib.util
    sys.dont_write_bytecode = True
    saved = sys.modules.pop('common', None)
    if extra_path:
        sys.path.insert(0, str(extra_path))
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        if extra_path:
            sys.path.remove(str(extra_path))
        sys.modules.pop('common', None)
        if saved is not None:
            sys.modules['common'] = saved
    return mod


def parse_poly(text: str) -> dict:
    """{frozenset((symbol, power)): Fraction} of a RECON-style polynomial."""
    out = {}
    for sign, term in re.findall(r'([+-]?)\s*([^+-]+)', ' '.join(text.split())):
        term = term.strip()
        m = re.match(r'^\((\d+)/(\d+)\)|^(\d+)', term)
        if m and m.group(1):
            co, term = F(int(m.group(1)), int(m.group(2))), term[m.end():]
        elif m and m.group(3):
            co, term = F(int(m.group(3))), term[m.end():]
        else:
            co = F(1)
        mono = {}
        for s, p in re.findall(r'(A|[bc][2-8])(?:\^(\d+))?', term):
            mono[s] = mono.get(s, 0) + int(p or 1)
        if not mono or re.sub(r'(A|[bc][2-8])(?:\^\d+)?|\s', '', term):
            raise ValueError(f'cannot parse the term {term!r}')
        key = frozenset(mono.items())
        out[key] = out.get(key, F(0)) + (-co if sign == '-' else co)
    return out


def synthetic_ar(rng, R: int = 6, order: int = 8, noise: float = 1e-3) -> dict:
    """Replicates around the 2026 production means (order-8 vectors: the new top slots and loop 8 synthetic)."""
    res = json.loads((PROD / 'C7_result.json').read_bytes())
    ar = {s: {t: {} for t in 'ab'} for s in ('free', 'power')}
    for s in ('free', 'power'):
        for L in range(3, order + 1):
            if L <= 7:
                v = np.asarray(res['means'][s][str(L)], float)
                k7 = 8 - L
                top = max(1., np.max(np.abs(v)))
                v8 = np.concatenate([v[:k7], [rng.normal() * top], v[k7:], [rng.normal() * top]]) if order == 8 else v
            else:
                v8 = rng.normal(size=2) * 10.
            for t in 'ab':
                ar[s][t][L] = v8 + noise * (np.abs(v8) + 1) * rng.standard_normal((R, len(v8)))
    return ar


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--exact', action='store_true', help='also run the vendored exact_check.py (R09 gate)')
    ap.add_argument('--output', type=Path)
    ap.add_argument('--provenance', type=Path, help='--exact: where to write exact_check_provenance.json')
    a = ap.parse_args()
    results, failed = [], []

    def check(name: str, ok: bool, detail='') -> None:
        detail = detail if isinstance(detail, str) else json.dumps(detail, default=str)
        results.append(dict(check=name, passed=bool(ok), detail=detail[-1200:]))
        if not ok:
            failed.append(name)
        print(('PASS ' if ok else 'FAIL ') + name + (f': {detail[-500:]}' if detail and not ok else ''), flush=True)

    oa = asm.vendored()
    B2_7, _ = asm.two_loop()
    ref = load_reference(ROOT / 'reference/c7d2_hpc_a55958f/tools/assemble.py', 'c7d2_ref_assemble',
                         ROOT / 'reference/c7d2_hpc_a55958f/tools')
    ana = load_reference(ROOT / 'reference/LRI_C7_d2_progress/code/analyze.py', 'c7d2_ref_analyze')
    B2_6 = np.asarray(ref.B2, float)
    check('B2: the 7-entry inputs/two_loop.json extends C7(2)\'s 6 entries', np.array_equal(B2_7[:6], B2_6) and len(B2_7) == 7)
    # ---- A-ASM-2 -----------------------------------------------------------------------------------------------
    rng = np.random.default_rng(51892)
    sets = [{L: rng.normal(size=2 * (8 - L)) * 10 ** rng.uniform(-3, 3) for L in range(3, 8)} for _ in range(96)]
    res7 = json.loads((PROD / 'C7_result.json').read_bytes())
    prod = {L: np.asarray(res7['means']['free'][str(L)], float) + np.asarray(res7['means']['power'][str(L)], float)
            for L in range(3, 8)}
    bad_c, bad_j = [], []
    for i, vals in enumerate(sets + [prod]):
        r0, r1 = ref.coefficients(vals), ana.coefficients(vals)
        c6, c7 = oa.coefficients(vals, B2_6, 7, 1), oa.coefficients(vals, B2_7, 7, 1)
        if not (np.array_equal(r0, r1) and np.array_equal(r0, c6) and np.array_equal(r0, c7)):
            bad_c.append(i)
        if i % 8 == 0 or i == len(sets):
            J0, J1 = ref.jacobians(vals), ana.jacobians(vals)
            Jm = oa.jacobians(vals, B2_6, 7, 1)
            Jm7 = oa.jacobians(vals, B2_7, 7, 1)
            if not all(np.array_equal(J0[L], J1[L]) and np.array_equal(J0[L], Jm[L]) and np.array_equal(J0[L], Jm7[L]) for L in J0):
                bad_j.append(i)
    check('A-ASM-2: order-7 coefficients bitwise equal to C7(2)\'s assemble.py and analyze.py (96 sets and the 2026 '
          'production means, B2 with 6 or 7 entries)', not bad_c, bad_c)
    check('A-ASM-2: the Jacobians are equal (every 8th set and the production means)', not bad_j, bad_j)
    # ---- A-ASM-4 -----------------------------------------------------------------------------------------------
    A = -B2_7[0] / 6
    check('A = -B2[0]/6 = 4 log 2 to 1e-12', abs(A - 4 * math.log(2)) <= 1e-12 * 4 * math.log(2), A)
    ar0 = synthetic_ar(np.random.default_rng(97), R=2)  # the production means with synthetic new slots and loop 8
    pts = [{L: ar0['free']['a'][L].mean(0) + ar0['power']['a'][L].mean(0) for L in range(3, 9)}]
    prng = np.random.default_rng(16)
    pts += [{L: prng.normal(size=2 * (9 - L)) * 10 ** prng.uniform(-1, 2) for L in range(3, 9)} for _ in range(16)]
    worst_top, worst_l7, aff_fail = 0., 0., []
    for i, m in enumerate(pts):
        J = oa.jacobians(m, B2_7, 8, 1)
        try:
            t = oa.top_slot_gate(J, 8)
            worst_top = max([worst_top] + [r['rel_deviation'] for r in t['rows']])
            l7 = oa.loop7_gate(J, B2_7, 8)
            worst_l7 = max(worst_l7, l7['rel_deviation'])
            af = oa.affinity_gate(m, B2_7, 8, 1)
            if af['loops'] != [5, 6, 7, 8]:
                aff_fail.append((i, 'loops'))
        except ArithmeticError as e:
            aff_fail.append((i, str(e)[:120]))
    check('A-ASM-4: top-slot rule (-1,+3)/3^(L+1), L = 3..8, to 1e-12 with no lower-order dependence (17 points)',
          worst_top <= 1e-12 and not aff_fail, dict(worst=worst_top))
    check('A-ASM-4: loop-7 entry (-16A, 42A)/19683 to 1e-12', worst_l7 <= 1e-12, worst_l7)
    check('A-ASM-4: float affinity of loops 5..8 to 1e-10 at every point', not aff_fail, aff_fail)
    try:
        oa.affinity_gate(pts[1], B2_7, 8, 1, loops=[4, 5])
        check('A-ASM-4: the affinity gate fails when loop 4 is perturbed (loops=[4,5])', False, 'accepted')
    except ArithmeticError:
        check('A-ASM-4: the affinity gate fails when loop 4 is perturbed (loops=[4,5])', True)
    # Fraction mode
    frng = np.random.default_rng(210)
    exact_m = {L: np.array([F(int(x), int(y)) for x, y in zip(frng.integers(-9, 10, 2 * (9 - L)), frng.integers(1, 7, 2 * (9 - L)))],
                           dtype=object) for L in range(3, 9)}
    B2e = np.array([F(int(x), int(y)) for x, y in zip(frng.integers(-9, 10, 7), frng.integers(1, 7, 7))], dtype=object)
    af = oa.affinity_gate(exact_m, B2e, 8, F(1))
    check('A-ASM-4: Fraction mode, all 210 exact second differences over loops 5..8 vanish',
          af['mode'] == 'exact' and af['pairs'] == 210 and af['all_second_differences_zero'], af)
    ms7_src = (ROOT / 'reference/LRI_C7_d2_progress/code/check_assembly.py').read_text()
    fn = next(n for n in ast.parse(ms7_src).body if isinstance(n, ast.FunctionDef) and n.name == 'ms7')
    ns = {'Q': F}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), 'check_assembly.py', 'exec'), ns)
    import random
    crng = random.Random(161803)
    bad_ms = []
    for t in range(16):
        Av = F(crng.randrange(1, 10), crng.randrange(1, 7))
        bL = {L: F(crng.randrange(-10, 11), crng.randrange(1, 7)) for L in range(3, 9)}
        cL = {L: F(crng.randrange(-10, 11), crng.randrange(1, 7)) for L in range(3, 9)}
        vals8 = {L: np.array([bL[L]] + [F(0)] * (8 - L) + [cL[L]] + [F(0)] * (8 - L), dtype=object) for L in range(3, 9)}
        B2c = np.array([-6 * Av] + [F(0)] * 6, dtype=object)
        C = oa.coefficients(vals8, B2c, 8, F(1))
        env = {'A': Av, **{f'b{L}': bL[L] for L in range(3, 9)}, **{f'c{L}': cL[L] for L in range(3, 9)}}
        envg = {'b2': -6 * Av, 'c2': -Av, **{k: v for k, v in env.items() if k != 'A'}}
        A_, b3, b4, b5, b6, b7 = Av, bL[3], bL[4], bL[5], bL[6], bL[7]
        c3, c4, c5, c6, c7 = cL[3], cL[4], cL[5], cL[6], cL[7]
        C4 = (60 * A_ ** 3 - 8 * A_ * b3 + 18 * A_ * c3 + 3 * c4 - b4) / 243
        C5 = (336 * A_ ** 4 - 60 * A_ ** 2 * b3 + 108 * A_ ** 2 * c3 + b3 ** 2 - 3 * b3 * c3 - 10 * A_ * b4 + 24 * A_ * c4 + 3 * c5 - b5) / 729
        C6 = (3 * c6 - b6 + 2016 * A_ ** 5 - 448 * A_ ** 3 * b3 + 672 * A_ ** 3 * c3 - 84 * A_ ** 2 * b4 + 168 * A_ ** 2 * c4
              + F(49, 3) * A_ * b3 ** 2 - 42 * A_ * b3 * c3 - 12 * A_ * b5 + 30 * A_ * c5 + F(7, 3) * b3 * b4 - 4 * b3 * c4 - 3 * b4 * c3) / 2187
        C7 = ns['ms7'](Av, {L: [bL[L]] for L in range(3, 8)}, {L: [cL[L]] for L in range(3, 8)})
        ok = (C[8] == oa.ms8_value(env) == oa.ms8_value(envg, general=True) and C[4] == C4 and C[5] == C5 and C[6] == C6
              and C[7] == C7)
        if not ok:
            bad_ms.append(t)
    check('A-ASM-4: Fraction mode, coefficients = ms8_value (both forms) and reproduces C4, C5, c6:RGassembly and ms7 '
          '(16 constant-coefficient cases)', not bad_ms, bad_ms)
    recon = parse_poly(RECON_MS8)
    rows = {frozenset(m.items()): co for co, m in oa.ms8_rows()}
    check('A-ASM-4: ms8_rows equals the RECON section 1.1 polynomial (34 monomials)', rows == recon and len(rows) == 34,
          dict(only_vendored=len(set(rows) - set(recon)), only_recon=len(set(recon) - set(rows))))
    # hard gates in tools/assemble.py
    ar = synthetic_ar(np.random.default_rng(8008), R=8)
    r = asm.combine(ar, 8, bootstrap=16)
    check('A-ASM-4: tools/assemble.py evaluates the top-slot, loop-7 and affinity gates on synthetic data built on '
          'the production means', set(r['gates']) == {'top_slot', 'loop7', 'affinity'}
          and [x['L'] for x in r['gates']['top_slot']['rows']] == list(range(3, 9)) and r['gates']['affinity']['loops'] == [5, 6, 7, 8])
    real = oa.coefficients

    def broken(vals, B2, order, half_d):
        out = real(vals, B2, order, half_d)
        if order == 8 and 3 in vals:
            out = out.copy()
            out[8] = out[8] + 1e-3 * vals[3][5] * vals[3][5]
        return out

    oa.coefficients = broken
    try:
        asm.combine(ar, 8, bootstrap=0)
        check('A-ASM-4: an injected gate violation (monkeypatched coefficients) is a hard failure', False, 'accepted')
    except ArithmeticError as e:
        check('A-ASM-4: an injected gate violation (monkeypatched coefficients) is a hard failure', True, str(e)[:200])
    finally:
        oa.coefficients = real
    # ---- A-ASM-5 -----------------------------------------------------------------------------------------------
    means, vc = oa.campaign_moments(ar, range(3, 9))
    sa = oa.sector_assembly(means, vc, B2_7, 8, 1)
    tot = {L: sum(np.asarray(ar[s][t][L]).mean(0) for t in 'ab') / 2 for s in ('free',) for L in range(3, 9)}
    tot = {L: tot[L] + sum(np.asarray(ar['power'][t][L]).mean(0) for t in 'ab') / 2 for L in range(3, 9)}
    check('PP1: C8_full = F8(f+p)[8], recomputed by hand from the replicates',
          r['C8_full'] == float(oa.coefficients(tot, B2_7, 8, 1)[8]))
    check('PP2: C8^pf, Delta_p C8 = C8 - C8^pf with SE sqrt(V_Delta[8,8]), and the cross term',
          r['power_free_C8'] == float(sa['power_free_coefficients'][8]) and r['power_correction'] == float(sa['power_differences'][8])
          and r['power_correction'] == r['C8_full'] - r['power_free_C8']
          and r['power_correction_se'] == float(math.sqrt(max(0, sa['power_difference_covariance'][8, 8])))
          and r['power_free_correction_covariance'] == float(sa['cross'][8, 8]))
    dl = np.array([0, 0, 0, 5e-13, 2e-6, 9e-5, 1e-3, 0.2, 3.0])
    ds = np.array([0, 0, 0, 1e-14, 1e-6, 2e-5, 2e-3, 0.05, 1.0])
    pn = asm.power_null_checks(dl, ds, 8)
    nr = {x['order']: x for x in pn['null_rows']}
    check('PP3: null rows 3..7 with pull = Delta/SE (hand values)', [x['order'] for x in pn['null_rows']] == [3, 4, 5, 6, 7]
          and nr[4]['pull'] == 2.0 and abs(nr[5]['pull'] - 4.5) < 1e-12 and abs(nr[6]['pull'] - .5) < 1e-12 and nr[7]['pull'] == 4.0)
    check('PP4: |pull| > 3 is flagged "not proved zero"', nr[5]['flag'] == 'not proved zero' and nr[7]['flag'] == 'not proved zero'
          and nr[4]['flag'] is None and nr[6]['flag'] is None and [x['order'] for x in pn['flags']] == [5, 7])
    check('PP5: order 3 at rounding level (|Delta| < 1e-12), no pull', nr[3]['pull'] is None and 'rounding' in nr[3]['note'])
    check('PP7: the order-8 pull is a diagnostic with no flag', pn['top']['order'] == 8 and pn['top']['pull'] == 3.0
          and 'flag' not in pn['top'])
    dl6 = dl.copy()
    dl6[6] = 0.01
    pn6 = asm.power_null_checks(dl6, ds, 8)
    nr6 = {x['order']: x for x in pn6['null_rows']}
    check('PP8: a flag at order 6, or at order 5 (d=2), is marked "must be investigated"; order 7 is not',
          nr[5]['investigate'] and nr6[6]['investigate'] and not nr[7]['investigate'] and not nr[4]['investigate'])
    try:
        asm.power_null_checks(np.where(np.arange(9) == 6, np.nan, dl), ds, 8)
        check('guard: a non-finite power difference is refused', False)
    except ArithmeticError:
        check('guard: a non-finite power difference is refused', True)
    zse = ds.copy()
    zse[5] = 0.
    pz = {x['order']: x for x in asm.power_null_checks(dl, zse, 8)['null_rows']}
    check('guard: a null row with SE 0 is flagged explicitly', pz[5]['flag'] == 'SE not positive: pull undefined' and pz[5]['investigate'])
    keep = asm.power_null_checks

    def all_flagged(delta, dse, order, d=2):
        out = keep(delta, dse, order, d)
        for x in out['null_rows']:
            x['flag'] = 'not proved zero'
        out['flags'] = list(out['null_rows'])
        return out

    asm.power_null_checks = all_flagged
    try:
        r6 = asm.combine(ar, 8, bootstrap=16)
    finally:
        asm.power_null_checks = keep
    est = ('C8_full', 'sampling_standard_error', 'coefficients', 'standard_errors', 'covariance', 'power_free_C8',
           'power_free_se', 'power_correction', 'power_correction_se', 'power_free_correction_covariance', 'bootstrap',
           'campaigns', 'half_streams', 'error_by_loop')
    check('PP6: flags never change C8, C8^pf, Delta_p C8 or any uncertainty (every null row forced flagged)',
          all(json.dumps(r6[k], sort_keys=True) == json.dumps(r[k], sort_keys=True) for k in est)
          and len(r6['power_null_checks']['flags']) == 5)
    Vh = sum(sa['J'][L] @ (vc['free'][L] + vc['power'][L]) @ sa['J'][L].T for L in range(3, 9))
    check('PP9: V_C = sum_L J_L (V_f + V_p) J_L^T and V_C = V_pf + V_Delta + cross + cross^T',
          np.allclose(np.asarray(r['covariance']), Vh, rtol=1e-12, atol=1e-12 * np.max(np.abs(Vh)))
          and np.allclose(sa['covariance'], sa['power_free_covariance'] + sa['power_difference_covariance'] + sa['cross'] + sa['cross'].T,
                          rtol=1e-10, atol=1e-8))
    v = json.loads((ROOT / 'tools/VENDORED.json').read_bytes())
    pp_sha = v['power_protocol']['sha256']
    h = json.loads((ROOT / 'vendor/c8_assembly/HANDOFF_assembly.json').read_bytes())
    check('PP10: the result pins POWER_PROTOCOL.md at the HANDOFF sha256, recorded in docs/NUMERICS.md',
          r['power_protocol']['sha256'] == pp_sha == next(f['sha256'] for f in h['files'] if f['path'] == 'POWER_PROTOCOL.md')
          and pp_sha in (ROOT / 'docs/NUMERICS.md').read_text())
    mu, se = np.array(r['coefficients']), np.array(r['standard_errors'])
    inj = mu.copy()
    inj[7] = asm.REFERENCE_LOWER[7][0] + 4 * math.sqrt(se[7] ** 2 + asm.REFERENCE_LOWER[7][1] ** 2)
    for k in (3, 4, 5, 6):
        inj[k] = asm.REFERENCE_LOWER[k][0] + 0.5 * math.sqrt(se[k] ** 2 + asm.REFERENCE_LOWER[k][1] ** 2)
    lo = asm.lower_order_checks(inj, se, 8)
    check('A-ASM-5: lower-order pulls C3..C7 use both SEs (hand values), with the C6 secondary reference',
          [x['order'] for x in lo] == [3, 4, 5, 6, 7] and all(abs(x['pull'] - (4.0 if x['order'] == 7 else .5)) < 1e-9 for x in lo)
          and 'secondary' in lo[3] and lo[4]['flag'] and not any(x['flag'] for x in lo[:4]))
    rr = dict(r, lower_order_checks=lo)
    lines = asm.summary_lines(rr)
    check('A-ASM-5: an injected 4-sigma C7 deviation prints a FLAG line', any(l.startswith('FLAG') and l.split('FLAG |pull|>3 (diagnostic) ')[-1].startswith('C7:') for l in lines),
          lines[:6])
    tsum = sum(x['variance'] for s in r['error_by_loop'].values() for x in s.values())
    check('A-ASM-5: error_by_loop sums to Var(C8) and its shares to 1',
          abs(tsum - r['covariance'][8][8]) <= 1e-10 * r['covariance'][8][8]
          and abs(sum(x['share'] for s in r['error_by_loop'].values() for x in s.values()) - 1) < 1e-10)
    asm.check_combination(r)
    hs = []
    for hh in (0, 1):
        mm = {L: sum(np.asarray(ar[s][t][L])[hh * len(ar[s][t][L]) // 2:(hh + 1) * len(ar[s][t][L]) // 2].mean(0)
                     for s in ('free', 'power') for t in 'ab') / 2 for L in range(3, 9)}
        hs.append(oa.coefficients(mm, B2_7, 8, 1).tolist())
    check('A-ASM-5: the half streams equal hand values', hs == r['half_streams'])
    brng = np.random.default_rng(asm.BOOTSTRAP_SEED)
    xs = []
    for _ in range(16):
        mm = {s: {L: sum(np.asarray(ar[s][t][L])[brng.integers(len(ar[s][t][L]), size=len(ar[s][t][L]))].mean(0) for t in 'ab') / 2
                  for L in range(3, 9)} for s in ('free', 'power')}
        xs.append(oa.coefficients({L: mm['free'][L] + mm['power'][L] for L in range(3, 9)}, B2_7, 8, 1))
    check('A-ASM-5: the bootstrap (seed 70530413, 16 replicates) equals hand values',
          np.array(xs).std(0, ddof=1).tolist() == r['bootstrap']['full_se'])
    to = asm.test_only_view(r)
    phys = set(r) - set(asm.META)
    check('A-ASM-5: a test-only result holds no physical number (every field null at the top level, values under '
          'test_partial)', all(to[k] is None for k in phys) and to['test_partial']['C8_full'] == r['C8_full'] and to['test_only'] is True)
    check('A-ASM-5: verify_result accepts the synthetic result and its test-only form', not vr.verify(json.loads(json.dumps(r)))
          and not vr.verify(json.loads(json.dumps(to))), (vr.verify(json.loads(json.dumps(r))) + vr.verify(json.loads(json.dumps(to))))[:5])
    # ---- --exact (R09) -----------------------------------------------------------------------------------------
    rec_extra = {}
    if a.exact:
        keys = json.loads(KEYS.read_bytes())
        ref_res = json.loads((ROOT / 'vendor/c8_assembly/exact_check_results.json').read_bytes())
        with tempfile.TemporaryDirectory(prefix='c8d2_exact_') as td:
            env = {k: v for k, v in os.environ.items() if k not in ('PYTHONPYCACHEPREFIX',)}
            env.update(LRI_ROOT=str(ROOT / 'vendor/c8_assembly_fixtures'), PYTHONDONTWRITEBYTECODE='1')
            cp = subprocess.run([sys.executable, '-B', str(ROOT / 'vendor/c8_assembly/exact_check.py')], cwd=td, env=env,
                                capture_output=True, text=True)
        got = json.loads(cp.stdout) if cp.returncode == 0 else {}
        whole = re.compile(r'^(loop7_exact|affinity_order\d)$')

        def leaves(o, p=''):
            if isinstance(o, dict) and not whole.match(p):
                for k, x in o.items():
                    yield from leaves(x, f'{p}/{k}' if p else k)
            else:
                yield p, o
        g, rf = dict(leaves(got)), dict(leaves(ref_res))
        prov = [re.compile(x) for x in keys['provenance_patterns']]
        exact_bad = [k for k in keys['exact'] if k not in g or json.dumps(g[k], sort_keys=True) != json.dumps(rf.get(k), sort_keys=True)]
        float_bad = []
        for k, b in keys['float_diagnostics'].items():
            if k not in g:
                float_bad.append(f'{k} missing')
                continue
            x = float(g[k])
            ok = (abs(x) < b['bound'] if b['kind'] == 'abs_lt' else abs(x) < float(g[b['bound']]) if b['kind'] == 'abs_lt_key'
                  else abs(x - b['bound'][0]) < b['bound'][1])
            if not ok:
                float_bad.append(f'{k}={x}')
        provenance = {k: g[k] for k in g if any(pp.match(k) for pp in prov)}
        unknown = [k for k in g if k not in keys['exact'] and k not in keys['float_diagnostics'] and k not in provenance]
        check('--exact: exact_check.py completes with LRI_ROOT = the pinned fixtures', cp.returncode == 0, cp.stderr[-500:])
        check(f'--exact: every exact key ({len(keys["exact"])}) present and equal to exact_check_results.json', not exact_bad, exact_bad)
        check(f'--exact: every float diagnostic ({len(keys["float_diagnostics"])}) within its bound', not float_bad, float_bad)
        check('--exact: no unclassified or new key', not unknown, unknown)
        check('--exact: the provenance keys match their patterns and are recorded, not compared', len(provenance) == 1, list(provenance))
        rec_extra = dict(exact_check=dict(returncode=cp.returncode, float_values={k: g.get(k) for k in keys['float_diagnostics']},
                                          provenance=provenance))
        if a.provenance:
            a.provenance.parent.mkdir(parents=True, exist_ok=True)
            a.provenance.write_text(json.dumps(dict(schema='c8-d2-exact-check-provenance-1', provenance=provenance,
                                                    lri_root='vendor/c8_assembly_fixtures', python=sys.version.split()[0],
                                                    numpy=np.__version__, host=os.uname().nodename), indent=1) + '\n')
    rec = dict(schema='c8-d2-gate-1', gate='A-ASM-2/4/5 assembly_checks' + (' --exact' if a.exact else ''), passed=not failed,
               failed=failed, checks=results, numpy=np.__version__, python=sys.version.split()[0], host=os.uname().nodename,
               **rec_extra)
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(rec, indent=1, default=str) + '\n')
    print(f'assembly_checks: {len(results) - len(failed)}/{len(results)} checks passed')
    return 0 if not failed else 1


if __name__ == '__main__':
    sys.exit(main())
