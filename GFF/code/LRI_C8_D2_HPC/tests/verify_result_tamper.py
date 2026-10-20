#!/usr/bin/env python3
"""A-ASM-7 on synthetic data: tools/verify_result.py rejects a tampered value, a deleted gates block and an added
key, and accepts an untouched result (also its test-only form); the checkpoint-review cases (O10): power_free_se or
power_free_correction_covariance changed alone (the variance identity), a key added to or deleted from test_partial,
and for combinations (final, partial and test-only, made by tools/combine.combine_batches) a changed chi-square, dof,
count or per-batch value, a key added to or deleted from the batches block, a deleted combination field, a flipped
final and a changed status, each against its untouched counterpart that verifies; X16 (Stage-6 fix round 1): a result,
a test-only result and combinations labelled with another dimension (3, or "2" as a string), epsilon (2s-3) or
assembly.half_d (1.5, or 1.0 as a float); Y11 (Stage-6 fix round 2, S6D-R2-03): coordinated tampers where a copied
field is made huge to widen the tolerance of a changed C8_full (the finding's scope = 1e30 with C8_full + 1, in a
result, a test-only result and combinations; a metadata number in backend or design; power_correction_se and
power_difference_errors[8] made huge with power_free_correction_covariance cancelling them in the variance identity and
every derived field recomputed), and copied fields of the wrong type (a campaign C8 as text, a NaN in the bootstrap, a
boolean or NaN in a mean vector, a negative power_free_se); tools/assemble.coverage_guard refuses a non-test
campaign with one L8 group removed, one graph removed from a group, a nonpositive count, or one counts file of the
design bundle altered, and accepts the complete one. The campaign groups are built on tests/fixtures/inputs_mini's
inventory (every L3..L7 graph and the 8 smallest L8 graphs per sector). The end-to-end refusals of `assemble` and
`combine` on real campaign directories are Stage 3 (tests/test_pipeline.py).
F6 (Stage 5), rounding-level leaves on any BLAS kernel family: four real test results assembled on AMD EPYC 7543
nodes (tests/fixtures/verify_result_cross_machine/, from the Stage-5 symmetry evidence; design_chain_k2_partial.json,
the design chain's test-only partial combination, failed on the Mac before R3) verify on this machine, with the
largest residual spread recorded in units of eps M_k; a result assembled with its matrix products summed in another
order (compensated, as another kernel family would) verifies; a stored linear_response_residual moved by 8 eps M_k
(above the old 1e-12 tolerance) verifies, one moved by 2 x the bound or by 1e-6 |C_8| is rejected, also in the
test-only form; and a power-null-check value at rounding level matches to the 1e-12 floor, while the same change of a
mean, or a change of 5e-12 there, is rejected.
R3 (Stage-6 residual after fix round 2), pulls: verify_result.pull_bound covers every point of the input box (400
random rows, brute force); in a result and its test-only form, the power null rows 1 and 4, the top row and the
lower-order rows 0 and 3 (with its secondary): inputs (delta or estimate, se) moved by up to 0.99 of their own
tolerance with the pull consistent, as on another machine, verify (the pre-R3 verifier refused them: the pull moved
beyond REL x the row scale); an input moved by 1.5 x its tolerance, a pull changed alone by half its derived bound
(passed by the comparison, refused because it is not the pull of its stored inputs) or by twice it, and a secondary
pull changed alone are rejected.
Z8 (Stage-6 fix round 3, S6D-R3-01), the covariance: rejected in a result, a test-only result and both combinations
(each verified before the fix): covariance[3][8] = 1e30 with covariance[8][3] unchanged (the finding), covariance[3][4]
moved alone by 1e-6 of sqrt(c33 c44) (asymmetric at its own scale, a 1e-9-scale entry), symmetric correlations 0.9,
0.9, -0.9 among orders 6, 7 and 8 (each |rho| <= 1, the matrix indefinite); in a result and its test-only form, a
covariance between the zero-variance order 0 and order 8, and a negative variance covariance[3][3] with its standard
error and lower-order check recomputed; the same class: a negative campaign sampling_se, bootstrap full_se or
correction_se, and an error_by_loop variance at -1e-6 Var(C8) with the sum and shares consistent (a negative
power_difference_errors entry, refused before by the recomputation, as a regression guard). Accepted: an off-diagonal
element moved alone by 0.5 COV_REL sqrt(c_ii c_jj) (refused at 2 COV_REL), at orders (5, 7) and (3, 4); the
cross-machine fixtures' asymmetry (at most a few eps) 1e3 x inside COV_REL; covariance_problems on constructed matrices
(zero rows and variances 1e-9..1e6): a singular PSD matrix and a correlation 1 + 0.5 m COV_REL accepted, 1 + 2 m COV_REL
and 1.5 refused, a zero variance at -0.5 COV_REL EPS D accepted and at -2 refused, an asymmetry of 0.5 COV_REL at the
1e-9 variance accepted and of 2 refused, an all-zero matrix accepted, an off-diagonal element without any variance
refused.
Usage: python3 -B tests/verify_result_tamper.py [--output FILE]"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import sys
import tempfile
from pathlib import Path
from unittest import mock

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))
import assemble as asm  # noqa: E402
import combine  # noqa: E402
import verify_result as vr  # noqa: E402
from assembly_checks import synthetic_ar  # noqa: E402


def _blk(x: dict) -> dict:
    """the block holding a result's physical fields (test_partial for a test-only result)"""
    return x['test_partial'] if isinstance(x.get('test_partial'), dict) else x


def _sd(b: dict) -> np.ndarray:
    return np.sqrt(np.maximum(np.diag(np.asarray(b['covariance'], float)), 0.))


def z8_cases(r: dict, to: dict, fin: dict, tfin: dict) -> list:
    """Z8 (S6D-R3-01) rejections: (name, tampered result). Off-diagonal covariance elements feed nothing the verifier
    recomputes, so every case below verified before the fix (except the negative power_difference_errors entry, which
    the recomputation's power_null_checks already refused: a regression guard). Where a tamper changes a recomputed
    field's input (a diagonal element, an error_by_loop variance), the derived fields are recomputed as the assembler
    would, so only the new checks can refuse it."""
    out = []
    forms = (('a result', r), ('a test-only result', to), ('a final combination', fin), ('a test-only combination', tfin))
    for name, x in forms:
        t = copy.deepcopy(x)
        _blk(t)['covariance'][3][8] = 1e30
        out.append((f'Z8: {name} with covariance[3][8] = 1e30 and covariance[8][3] unchanged (the finding)', t))
        t = copy.deepcopy(x)
        b = _blk(t)
        s = _sd(b)
        b['covariance'][3][4] += 1e-6 * s[3] * s[4]
        out.append((f'Z8: {name} with covariance[3][4] moved alone by 1e-6 sqrt(c33 c44) (asymmetric at its own scale)', t))
        t = copy.deepcopy(x)
        b = _blk(t)
        s = _sd(b)
        for (i, j), rho in (((6, 7), .9), ((6, 8), .9), ((7, 8), -.9)):  # every |correlation| <= 1, the block indefinite
            b['covariance'][i][j] = b['covariance'][j][i] = rho * s[i] * s[j]
        out.append((f'Z8: {name} with symmetric correlations 0.9, 0.9, -0.9 among orders 6, 7, 8 (indefinite)', t))
    for name, x in forms[:2]:
        t = copy.deepcopy(x)
        b = _blk(t)
        s = _sd(b)
        b['covariance'][0][8] = b['covariance'][8][0] = 1e-3 * s[8]
        out.append((f'Z8: {name} with a covariance between the zero-variance order 0 and order 8 (indefinite)', t))
        t = copy.deepcopy(x)
        b = _blk(t)
        b['covariance'][3][3] = -b['covariance'][3][3]
        b['standard_errors'][3] = 0.
        b['lower_order_checks'] = json.loads(json.dumps(asm.lower_order_checks(np.asarray(b['coefficients'], float),
                                                                               np.asarray(b['standard_errors'], float), 8)))
        out.append((f'Z8: {name} with a negative variance covariance[3][3] (its standard error and lower-order check recomputed)', t))
    t = copy.deepcopy(r)
    t['campaigns']['a']['sampling_se'] = -t['campaigns']['a']['sampling_se']
    out.append(('Z8 class: a negative campaign sampling_se', t))
    t = copy.deepcopy(to)
    t['test_partial']['bootstrap']['full_se'][5] = -abs(t['test_partial']['bootstrap']['full_se'][5]) - 1.
    out.append(('Z8 class: a negative bootstrap full_se (test-only)', t))
    t = copy.deepcopy(r)
    t['bootstrap']['correction_se'][8] = -abs(t['bootstrap']['correction_se'][8]) - 1.
    out.append(('Z8 class: a negative bootstrap correction_se', t))
    t = copy.deepcopy(r)
    var = t['covariance'][8][8]
    e = t['error_by_loop']['free']
    x7 = e['7']['variance'] + 1e-6 * var  # free L7 becomes -1e-6 Var(C8), free L8 takes the difference: the sum holds
    for L, v in (('7', e['7']['variance'] - x7), ('8', e['8']['variance'] + x7)):
        e[L] = dict(variance=v, share=v / var, se=math.sqrt(max(0., v)))
    out.append(('Z8 class: a negative error_by_loop variance (free L7 at -1e-6 Var(C8), the sum and shares consistent)', t))
    t = copy.deepcopy(r)
    t['power_difference_errors'][5] = -t['power_difference_errors'][5] - 1.
    out.append(('Z8 class (regression guard, refused before by the recomputation): a negative power_difference_errors entry', t))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--output', type=Path)
    a = ap.parse_args()
    results, failed = [], []

    def check(name: str, ok: bool, detail='') -> None:
        detail = detail if isinstance(detail, str) else json.dumps(detail, default=str)
        results.append(dict(check=name, passed=bool(ok), detail=detail[-800:]))
        if not ok:
            failed.append(name)
        print(('PASS ' if ok else 'FAIL ') + name + (f': {detail[-400:]}' if detail and not ok else ''), flush=True)

    r = json.loads(json.dumps(asm.combine(synthetic_ar(np.random.default_rng(777), R=6), 8, bootstrap=8)))
    check('an untouched result verifies', vr.verify(r) == [], vr.verify(r)[:5])
    to = json.loads(json.dumps(asm.test_only_view(r)))
    check('its test-only form verifies', vr.verify(to) == [], vr.verify(to)[:5])
    cases = []
    t = copy.deepcopy(r)
    t['C8_full'] *= 1 + 1e-6
    cases.append(('a tampered C8_full (relative 1e-6)', t))
    t = copy.deepcopy(r)
    t['coefficients'][5] += 1e-6 * abs(t['coefficients'][5])
    cases.append(('a tampered coefficient', t))
    t = copy.deepcopy(r)
    t['means']['free']['3'][0] *= 1.001
    cases.append(('a tampered loop-3 mean (the stored coefficients no longer follow)', t))
    t = copy.deepcopy(r)
    t['lower_order_checks'][2]['pull'] += 0.01
    cases.append(('a tampered stored pull', t))
    t = copy.deepcopy(r)
    t['power_null_checks']['null_rows'][2]['flag'] = 'not proved zero'
    cases.append(('a forged null-row flag', t))
    t = copy.deepcopy(r)
    t['gates']['top_slot']['rows'][0]['dC_db'] *= 1.001
    cases.append(('a tampered gate value', t))
    t = copy.deepcopy(r)
    del t['gates']
    cases.append(('a deleted gates block', t))
    t = copy.deepcopy(r)
    del t['gates']['loop7']
    cases.append(('a deleted gate inside the gates block', t))
    t = copy.deepcopy(r)
    t['extra'] = 1
    cases.append(('an added top-level key', t))
    t = copy.deepcopy(r)
    t['power_protocol']['note'] = 'x'
    cases.append(('an added key inside a block', t))
    t = copy.deepcopy(r)
    t['error_by_loop']['free']['8']['variance'] *= 2
    cases.append(('error_by_loop no longer summing to Var(C8)', t))
    t = copy.deepcopy(to)
    t['C8_full'] = t['test_partial']['C8_full']
    cases.append(('a test-only result with a physical value at the top level', t))
    t = copy.deepcopy(to)
    t['test_partial']['coefficients'][8] += 1.
    cases.append(('a tampered test-only partial value', t))
    # O10: the variance identity (fields the result holds no statistics to recompute) and the closed test_partial schema
    t = copy.deepcopy(r)
    t['power_free_se'] *= 1.01
    cases.append(('power_free_se changed alone (variance identity)', t))
    t = copy.deepcopy(r)
    t['power_free_correction_covariance'] += 0.05 * abs(t['covariance'][8][8])
    cases.append(('power_free_correction_covariance changed alone (variance identity)', t))
    t = copy.deepcopy(to)
    t['test_partial']['power_free_se'] *= 1.01
    cases.append(('a test-only power_free_se changed alone', t))
    t = copy.deepcopy(to)
    t['test_partial']['extra'] = 1
    cases.append(('a key added to test_partial', t))
    t = copy.deepcopy(to)
    del t['test_partial']['power_free_correction_covariance']
    cases.append(('a key deleted from test_partial', t))
    # combinations (combine.py): final, partial and test-only, the untouched ones verify
    def batch(label, seed, seeds):
        return dict(label=label, design_sha256='d' * 64, inputs_manifest_sha256='i' * 64, numerics='exact', rates_identity='default',
                    seeds=seeds, ar=synthetic_ar(np.random.default_rng(seed), R=6))
    b1, b2 = batch('sym', 11, list(range(24))), batch('exp', 22, list(range(100, 124)))
    fin = json.loads(json.dumps(combine.combine_batches([b1, b2], planned=2, bootstrap=0)))
    par = json.loads(json.dumps(combine.combine_batches([b1], planned=2, partial=True, bootstrap=0)))
    tfin = json.loads(json.dumps(combine.combine_batches([b1, b2], planned=2, bootstrap=0, test_only=True)))
    for name, x in (('a final combination', fin), ('a partial combination', par), ('a test-only combination', tfin)):
        check(f'{name} verifies', vr.verify(x) == [], vr.verify(x)[:5])
    check('the stored chi-square is the hand value', abs(fin['batches']['chi2_about_combined'] - sum(
        (x['C8_full'] - fin['C8_full']) ** 2 / x['sampling_se'] ** 2 for x in fin['batches']['per_batch'])) <= 1e-12 * fin['batches']['chi2_about_combined'])
    edits = (('chi2_about_combined changed', lambda b: b['batches'].__setitem__('chi2_about_combined', b['batches']['chi2_about_combined'] * 1.01)),
             ('dof changed', lambda b: b['batches'].__setitem__('dof', 2)),
             ('count changed', lambda b: b['batches'].__setitem__('count', 3)),
             ('a per-batch C8 changed (the chi-square no longer follows)', lambda b: b['batches']['per_batch'][0].__setitem__('C8_full', b['batches']['per_batch'][0]['C8_full'] + 1.)),
             ('a key added to the batches block', lambda b: b['batches'].__setitem__('note', 'x')),
             ('a key added to a per-batch entry', lambda b: b['batches']['per_batch'][1].__setitem__('seed', 1)),
             ('a per-batch label deleted', lambda b: b['batches']['per_batch'][0].pop('label')),
             ('final flipped', lambda b: b.__setitem__('final', not b['final'])),
             ('the status changed', lambda b: b.__setitem__('status', 'final combination')),
             ('a combination field deleted (design)', lambda b: b.pop('design')))
    for name, f in edits:
        t = copy.deepcopy(fin)
        f(t)
        cases.append((f'a final combination with {name}', t))
        t = copy.deepcopy(tfin)
        f(t['test_partial'])
        cases.append((f'a test-only combination with {name}', t))
    t = copy.deepcopy(par)
    t['final'] = True
    cases.append(('a partial combination marked final', t))
    t = copy.deepcopy(tfin)
    t['batches'] = t['test_partial']['batches']
    cases.append(('a test-only combination with its batches at the top level', t))
    t = copy.deepcopy(r)
    t['final'] = False
    cases.append(('an assembled non-test result marked not final', t))
    # X16 (Stage-6 fix round 1): the fixed labels dimension, epsilon and assembly.half_d (the recomputation runs at d = 2)
    for name, edit in (('dimension 3', lambda b: b.__setitem__('dimension', 3)), ('dimension "2" (a string)', lambda b: b.__setitem__('dimension', '2')),
                       ('epsilon 2s-3', lambda b: b.__setitem__('epsilon', '2s-3')),
                       ('assembly.half_d 1.5', lambda b: b['assembly'].__setitem__('half_d', 1.5)),
                       ('assembly.half_d 1.0 (a float)', lambda b: b['assembly'].__setitem__('half_d', 1.0))):
        t = copy.deepcopy(r)
        edit(t)
        cases.append((f'X16: a result labelled {name}', t))
    for name, edit in (('dimension 3', lambda x: x.__setitem__('dimension', 3)), ('epsilon 2s-3', lambda x: x.__setitem__('epsilon', '2s-3')),
                       ('assembly.half_d 1.5', lambda x: x['test_partial']['assembly'].__setitem__('half_d', 1.5))):
        t = copy.deepcopy(to)
        edit(t)
        cases.append((f'X16: a test-only result labelled {name}', t))
    for name, x in (('a final combination', fin), ('a test-only combination', tfin)):
        t = copy.deepcopy(x)
        (t['test_partial'] if 'test_partial' in t else t)['assembly']['half_d'] = 1.5
        cases.append((f'X16: {name} labelled assembly.half_d 1.5', t))
        t = copy.deepcopy(x)
        t['dimension'] = 3
        cases.append((f'X16: {name} labelled dimension 3', t))
    # Y11 (Stage-6 fix round 2): a copied field must never widen the tolerance of a recomputed one, and field types are
    # validated before anything is recomputed
    for name, x, top in (('a result', r, None), ('a test-only result', to, 'test_partial'), ('a final combination', fin, None),
                         ('a test-only combination', tfin, 'test_partial')):
        for field, val in (('scope', 1e30), ('backend', 1e30), ('design', 1e30)):
            if field == 'design' and 'batches' not in (x[top] if top else x):
                continue
            t = copy.deepcopy(x)
            holder = t[top] if top and field not in asm.META else t
            holder[field] = val
            (t[top] if top else t)['C8_full'] += 1.
            cases.append((f'Y11: {name} with {field} = {val:g} and C8_full + 1 (the finding\'s coordinated tamper)', t))
        t = copy.deepcopy(x)
        (t[top] if top and 'scope' not in asm.META else t)['scope'] = 1e30
        cases.append((f'Y11: {name} with scope = 1e30 alone (a metadata number)', t))

    def inflated(x: dict, top) -> dict:
        """power_difference_errors[8] and power_correction_se 1e15, power_free_correction_covariance cancelling them in the
        variance identity, every derived field recomputed from the tampered inputs, then C8_full + 1"""
        t = copy.deepcopy(x)
        blk = t[top] if top else t
        blk['power_difference_errors'][8] = 1e15
        var, pfse = blk['covariance'][8][8], blk['power_free_se']
        blk['power_free_correction_covariance'] = (var - pfse * pfse - 1e30) / 2
        # the fields derived from power_difference_errors, as the recomputation derives them
        blk['power_correction_se'] = 1e15
        blk['power_null_checks'] = json.loads(json.dumps(asm.power_null_checks(np.asarray(blk['power_differences'], float),
                                                                               np.asarray(blk['power_difference_errors'], float), 8)))
        blk['C8_full'] += 1.
        return t
    for name, x, top in (('a result', r, None), ('a test-only result', to, 'test_partial'), ('a final combination', fin, None)):
        cases.append((f'Y11: {name} with power_correction_se 1e15, a cancelling covariance and C8_full + 1', inflated(x, top)))
    t = copy.deepcopy(r)
    t['campaigns']['a']['C8'] = str(t['campaigns']['a']['C8'])
    cases.append(('Y11: a campaign C8 stored as text', t))
    t = copy.deepcopy(r)
    t['bootstrap']['full_se'][3] = float('nan')
    cases.append(('Y11: a NaN in the bootstrap block', t))
    t = copy.deepcopy(to)
    t['test_partial']['bootstrap']['bias'][2] = 'x'
    cases.append(('Y11: a test-only bootstrap bias stored as text', t))
    t = copy.deepcopy(r)
    t['means']['free']['3'][0] = float('nan')
    cases.append(('Y11: a NaN in a mean vector', t))
    t = copy.deepcopy(r)
    t['power_free_se'] = -t['power_free_se']
    cases.append(('Y11: a negative power_free_se (no standard error)', t))
    t = copy.deepcopy(fin)
    t['numerics'] = 0
    cases.append(('Y11: a combination with numerics stored as a number', t))
    # Z8 (Stage-6 fix round 3, S6D-R3-01): a covariance that is not one (asymmetric, a negative variance, indefinite),
    # and the copied statistics that cannot be negative; each tamper leaves every recomputed field consistent
    cases += z8_cases(r, to, fin, tfin)
    for name, t in cases:
        p = vr.verify(t)
        check(f'rejects {name}', bool(p), 'accepted')
    # F6: rounding-level leaves on any BLAS kernel family
    res_path = '/gates/affinity/linear_response_residual[8]'
    for f in sorted((ROOT / 'tests/fixtures/verify_result_cross_machine').glob('*.json')):
        x = json.loads(f.read_bytes())
        blk = dict(x['test_partial'], **{k: x[k] for k in asm.META if k in x})
        exp, bounds = vr._recompute(blk)
        stored, recomputed = blk['gates']['affinity']['linear_response_residual'], exp['gates']['affinity']['linear_response_residual']
        units = max(abs(p - q) / (bounds[f'/gates/affinity/linear_response_residual[{k}]'] / vr.RESIDUAL_ULPS)
                    for k, (p, q) in enumerate(zip(stored, recomputed)))
        check(f'F6: {f.stem}, assembled on an AMD node, verifies here (residual spread {units:.3f} eps M_k)',
              vr.verify(x) == [] and units <= vr.RESIDUAL_ULPS, vr.verify(x)[:3])
    oa = asm.vendored()

    class OtherOrder(np.ndarray):
        """matrix-vector products summed in another order (compensated), as another BLAS kernel family would"""
        def __matmul__(self, v):
            A, v = np.asarray(self), np.asarray(v)
            if A.ndim == 2 and v.ndim == 1:
                return np.array([math.fsum(A[i, j] * v[j] for j in range(A.shape[1])) for i in range(A.shape[0])])
            return A @ v
    real_jac = oa.jacobians
    with mock.patch.object(oa, 'jacobians', side_effect=lambda *a_, **k_: {L: np.asarray(v).view(OtherOrder) for L, v in real_jac(*a_, **k_).items()}):
        other = json.loads(json.dumps(asm.combine(synthetic_ar(np.random.default_rng(777), R=6), 8, bootstrap=8)))
    check('F6: a result assembled with its products summed in another order verifies', vr.verify(other) == [], vr.verify(other)[:3])
    _, bounds = vr._recompute(r)
    eight = 8 * bounds[res_path] / vr.RESIDUAL_ULPS
    check('F6: the 8 eps M_8 case exceeds the old tolerance (1e-12)', eight > 1e-12, f'{eight}')
    for form, base, path in (('', r, ('gates',)), ('test-only ', to, ('test_partial', 'gates'))):
        def moved(by):
            t = copy.deepcopy(base)
            node = t
            for k in path:
                node = node[k]
            node['affinity']['linear_response_residual'][8] += by
            return t
        t = moved(eight)
        check(f'F6: a {form}residual[8] moved by 8 eps M_8 verifies', vr.verify(t) == [], vr.verify(t)[:3])
        for name, by in (('2 x the bound', 2 * bounds[res_path]), ('1e-6 |C8|', 1e-6 * abs(r['C8_full']))):
            check(f'F6: rejects a {form}residual[8] moved by {name}', bool(vr.verify(moved(by))), 'accepted')
    pnull = '/power_null_checks/null_rows[0]/delta'
    for path, change, want in ((pnull, 5e-13, True), ('/test_partial' + pnull, 5e-13, True), (pnull, 5e-12, False),
                               ('/means/free/3[0]', 5e-13, False)):
        probs: list = []
        vr.compare(1e-16 + change, 1e-16, path, probs, 1e-16)
        check(f'F6: a rounding-level value changed by {change:g} at {path} is {"accepted" if want else "rejected"}', (not probs) == want, probs)
    # R3 (Stage-6 residual after fix round 2): a pull's tolerance follows from its inputs' tolerances (pull_bound), and
    # every stored pull is the pull of its own stored inputs (pull_problems). Each check stands alone: an exception (a
    # verifier without the R3 helpers) is that check's failure.
    def attempt(name: str, fn) -> None:
        try:
            ok, detail = fn()
        except Exception as e:  # noqa: BLE001
            ok, detail = False, f'{type(e).__name__}: {e}'
        check(name, ok, detail)

    def bound_box() -> tuple:
        rng = np.random.default_rng(2026_10_06)
        worst = 0.
        for _ in range(400):
            x, s, t = rng.normal() * 10 ** rng.uniform(-6, 3), 10 ** rng.uniform(-7, 1), (0. if rng.random() < .5 else 10 ** rng.uniform(-7, 1))
            r0 = rng.normal() * abs(x) if t else 0.
            tx, ts = abs(x) * 10 ** rng.uniform(-12, -6), s * 10 ** rng.uniform(-12, -1)
            p = (x - r0) / math.hypot(s, t)
            bound = vr.pull_bound(p, tx, s, ts, t)
            for dx in (-tx, -tx / 3, 0., tx / 2, tx):
                for ds in (-ts, -ts / 2, 0., ts / 3, ts):
                    q = (x + dx - r0) / math.hypot(s + ds, t)
                    # less the floating-point error of evaluating the two pulls (a few ulps each)
                    worst = max(worst, (abs(q - p) - 8 * vr.EPS * (abs(p) + abs(q))) / bound)
        return worst <= 1, f'largest (|dp| - rounding) / bound {worst:.6f}'
    attempt('R3: pull_bound covers every corner and interior point of the input box (400 random rows, t = 0 and t > 0)', bound_box)

    def pull_row(blk: dict, where):
        """(row, path, {input: (key, the vector holding the same number at index order)}) of a pull's row"""
        kind, i = where
        if kind == 'null':
            return (blk['power_null_checks']['null_rows'][i], f'/power_null_checks/null_rows[{i}]',
                    {'x': ('delta', 'power_differences'), 's': ('se', 'power_difference_errors')})
        if kind == 'top':  # its se is also power_correction_se, held by the variance identity: x only
            return blk['power_null_checks']['top'], '/power_null_checks/top', {'x': ('delta', 'power_differences')}
        return (blk['lower_order_checks'][i], f'/lower_order_checks[{i}]',
                {'x': ('estimate', 'coefficients'), 's': ('sampling_se', 'standard_errors')})

    def tolerance(row: dict, path: str) -> float:
        """the comparison's tolerance of a float of a gates, lower-order or power-null row (restated here, independently
        of verify_result): REL x the row's largest |float|, at least the 1e-2 floor inside power_null_checks"""
        floats = [abs(v) for v in row.values() if isinstance(v, float) and math.isfinite(v)]
        return vr.REL * max(floats + [vr.GATE_SCALE_FLOOR if path.startswith('/power_null_checks') else 0.])

    def repull(blk: dict, where) -> None:
        """the stored pulls of a row recomputed from its stored inputs, as the assembler computes them"""
        row = pull_row(blk, where)[0]
        if where[0] in ('null', 'top'):
            row['pull'] = row['delta'] / row['se']
        else:
            row['pull'] = asm.pull(row['estimate'], row['sampling_se'], row['reference'], row['reference_se'])
            if isinstance(row.get('secondary'), dict):
                sec = row['secondary']
                sec['pull'] = asm.pull(row['estimate'], row['sampling_se'], sec['reference'], sec['reference_se'])

    def moved(x: dict, top, where, key_frac: dict, pull_shift: float = 0., secondary_shift: float = 0.) -> dict:
        """x with the inputs of a pull moved by a fraction of their tolerance (key_frac: {'x' or 's': frac}), as another
        machine's rounding moves them (the copy in power_differences, power_difference_errors, coefficients or
        standard_errors moved alike), the pulls recomputed from the stored inputs, then shifted"""
        t = copy.deepcopy(x)
        blk = t[top] if top else t
        row, path, inputs = pull_row(blk, where)
        for which, frac in key_frac.items():
            key, vec = inputs[which]
            # the tolerance of the number: its row leaf's and its vector copy's (REL x the vector's largest |element|)
            tol = min(tolerance(row, path), vr.REL * max(abs(v) for v in blk[vec]))
            row[key] += frac * tol
            blk[vec][row['order']] = row[key]
        repull(blk, where)
        row['pull'] += pull_shift
        if secondary_shift:
            row['secondary']['pull'] += secondary_shift
        return t

    def bound_of(x: dict, top, where, secondary: bool = False) -> float:
        blk = dict(x[top], **{k: x[k] for k in asm.META if k in x}) if top else x
        path = pull_row(blk, where)[1] + ('/secondary' if secondary else '')
        return vr._recompute(blk)[1][f'{path}/pull']

    def accepted(t: dict) -> tuple:
        p = vr.verify(t)
        return p == [], p[:3]

    def rejected(t: dict, only_inconsistent: bool = False) -> tuple:
        p = vr.verify(t)
        ok = bool(p) and (not only_inconsistent or all('is not the pull of its stored inputs' in q for q in p))
        return ok, p[:3] or 'accepted'

    wheres = (('null', 1), ('null', 4), ('top', None), ('lower', 0), ('lower', 3))
    for form, x, top in (('', r, None), ('test-only ', to, 'test_partial')):
        for where in wheres:
            name = f'{where[0]} row {where[1]}' if where[1] is not None else 'top row'
            # accepted: inputs moved within their own tolerance, the pull consistent with them (as on another machine)
            for frac in (({'x': .5}, {'x': -.99}) if where[0] == 'top' else ({'x': .5}, {'x': -.99}, {'s': .5}, {'x': .5, 's': -.5})):
                attempt(f'R3: a {form}{name} with its inputs moved by {frac} of their tolerance and its pull consistent verifies',
                        lambda: accepted(moved(x, top, where, frac)))
            # rejected: an input beyond its tolerance (pull consistent); a pull changed alone, inside and beyond its bound
            attempt(f'R3: rejects a {form}{name} whose input moved by 1.5 x its tolerance (pull consistent)',
                    lambda: rejected(moved(x, top, where, {'x': 1.5})))
            attempt(f'R3: rejects a {form}{name} pull changed alone by 0.5 x its derived bound (passed by the comparison, refused as inconsistent)',
                    lambda: rejected(moved(x, top, where, {}, pull_shift=.5 * bound_of(x, top, where)), only_inconsistent=True))
            attempt(f'R3: rejects a {form}{name} pull changed alone by 2 x its derived bound',
                    lambda: rejected(moved(x, top, where, {}, pull_shift=2 * bound_of(x, top, where))))
            if where == ('lower', 3):
                attempt(f'R3: rejects a {form}{name} secondary pull changed alone by 0.5 x its derived bound',
                        lambda: rejected(moved(x, top, where, {}, secondary_shift=.5 * bound_of(x, top, where, secondary=True))))

    # the old rule's failure, reproduced on any machine: a null row's delta moved by half its own tolerance moves the
    # consistent pull by far more than REL x the row's scale
    def old_rule() -> tuple:
        t = moved(r, None, ('null', 1), {'x': .5})
        row = t['power_null_checks']['null_rows'][1]
        old_tol = vr.REL * max(abs(row['delta']), abs(row['se']), abs(row['pull']), vr.GATE_SCALE_FLOOR)
        shift = abs(row['pull'] - r['power_null_checks']['null_rows'][1]['pull'])
        return shift > old_tol, f'shift {shift:.3e}, old tolerance {old_tol:.3e}'
    attempt('R3: that pull moved beyond the pre-R3 tolerance (REL x the row scale), so the old verifier refused a consistent result', old_rule)
    # Z8 (Stage-6 fix round 3): the covariance's rounding tolerance, per element at its own scale. Each check stands
    # alone (an exception, e.g. a verifier without covariance_problems, is that check's failure).
    def moved_cov(x: dict, i: int, j: int, frac: float) -> dict:
        """x with covariance[i][j] alone moved by frac x COV_REL sqrt(c_ii c_jj)"""
        t = copy.deepcopy(x)
        b = _blk(t)
        s = _sd(b)
        b['covariance'][i][j] += frac * vr.COV_REL * s[i] * s[j]
        return t
    for form, x in (('', r), ('test-only ', to)):
        for (i, j) in ((5, 7), (3, 4)):
            attempt(f'Z8: a {form}result with covariance[{i}][{j}] alone moved by 0.5 COV_REL sqrt(c_ii c_jj) (rounding) verifies',
                    lambda: accepted(moved_cov(x, i, j, .5)))
            attempt(f'Z8: rejects a {form}result with covariance[{i}][{j}] alone moved by 2 COV_REL sqrt(c_ii c_jj)',
                    lambda: rejected(moved_cov(x, i, j, 2.)))

    def spread() -> tuple:
        """the asymmetry of every stored cross-machine fixture, in eps of sqrt(c_ii c_jj) (verified above by F6), far
        inside COV_REL"""
        worst = 0.
        for f in sorted((ROOT / 'tests/fixtures/verify_result_cross_machine').glob('*.json')):
            C = np.asarray(_blk(json.loads(f.read_bytes()))['covariance'], float)
            s = np.sqrt(np.maximum(np.diag(C), 0.))
            S = np.outer(s, s)
            A = np.abs(C - C.T)
            if (A[S == 0] != 0).any():
                return False, f'{f.name}: an asymmetric zero-variance row'
            worst = max(worst, float((A[S > 0] / S[S > 0]).max()) / vr.EPS)
        return worst * vr.EPS < vr.COV_REL / 1e3, f'largest asymmetry {worst:.2f} eps of sqrt(c_ii c_jj); COV_REL = {vr.COV_REL / vr.EPS:.3g} eps'
    attempt('Z8: the cross-machine fixtures are symmetric to rounding, 1e3 x inside COV_REL', spread)

    def unit() -> tuple:
        """covariance_problems on constructed matrices: zero rows (orders 0..2) and orders 3..8 of variances 1e-9..1e6
        (the stored results' range), uncorrelated but for a correlation rho between orders 7 and 8; the correlation
        matrix's smallest eigenvalue is then 1 - rho"""
        m = 9
        var = np.array([0., 0., 0., 1e-9, 1e-6, 1e-3, 1., 1e3, 1e6])

        def mat(rho=0., diag3=None, asym=0.):
            C = np.diag(var.copy())
            C[7, 8] = C[8, 7] = rho * math.sqrt(var[7] * var[8])
            C[3, 4] += asym * math.sqrt(var[3] * var[4])
            if diag3 is not None:
                C[0, 0] = diag3
            return C.tolist()
        D, out = var.max(), {}
        tests = (('PSD, zero rows', mat(), True), ('correlation 1 (singular, PSD)', mat(1.), True),
                 ('correlation 1 + 0.5 m COV_REL', mat(1 + .5 * m * vr.COV_REL), True), ('correlation 1 + 2 m COV_REL', mat(1 + 2 * m * vr.COV_REL), False),
                 ('correlation 1.5', mat(1.5), False), ('a zero variance at -0.5 COV_REL EPS D', mat(diag3=-.5 * vr.COV_REL * vr.EPS * D), True),
                 ('a zero variance at -2 COV_REL EPS D', mat(diag3=-2 * vr.COV_REL * vr.EPS * D), False),
                 ('c34 - c43 = 0.5 COV_REL sqrt(c33 c44) (1e-9 and 1e-6 variances)', mat(asym=.5 * vr.COV_REL), True),
                 ('c34 - c43 = 2 COV_REL sqrt(c33 c44)', mat(asym=2 * vr.COV_REL), False),
                 ('all zero', np.zeros((m, m)).tolist(), True), ('all-zero variances, one covariance', (np.eye(m, k=1) * 1e-300).tolist(), False))
        for name, C, want in tests:
            got = vr.covariance_problems(C)
            out[name] = (not got) == want
        return all(out.values()), out
    attempt('Z8: covariance_problems on constructed matrices (PSD edge, a negative zero variance, asymmetry at a 1e-9 variance)', unit)
    # the coverage guard
    inv = json.loads((ROOT / 'tests/fixtures/inputs_mini/inventory.json').read_bytes())
    groups = {(c, s, L): {int(row['id']): 4096 for row in inv[s][str(L)]} for c in 'ab' for s in ('free', 'power') for L in range(3, 9)}
    check('the coverage guard accepts the complete campaign (24 groups)', asm.coverage_guard(groups, inv)['groups'] == 24)

    def refuses(name: str, g: dict, bundle=None, s=None) -> None:
        try:
            asm.coverage_guard(g, inv, 8, bundle, s)
            check(f'the coverage guard refuses {name}', False, 'accepted')
        except ValueError as e:
            check(f'the coverage guard refuses {name}', True, str(e))

    g = dict(groups)
    del g[('a', 'free', 8)]
    refuses('a campaign with one L8 group removed', g)
    g = copy.deepcopy(groups)
    g[('b', 'power', 8)].pop(next(iter(g[('b', 'power', 8)])))
    refuses('a group with one graph removed', g)
    g = copy.deepcopy(groups)
    g[('a', 'power', 5)][next(iter(g[('a', 'power', 5)]))] = 0
    refuses('a graph with no points', g)
    with tempfile.TemporaryDirectory(prefix='c8d2_bundle_') as td:
        b = Path(td)
        (b / 'counts').mkdir()
        digests = {}
        for (c, s, L), counts in groups.items():
            name = f'counts/{c}_{s}_L{L}.txt'
            data = ''.join(f'{k} {v // 4}\n' for k, v in sorted(counts.items())).encode()
            (b / name).write_bytes(data)
            digests[name] = hashlib.sha256(data).hexdigest()
        (b / 'design_meta.json').write_text(json.dumps(dict(counts_sha256=digests)))
        check('the coverage guard accepts counts equal to the bundle counts x s', asm.coverage_guard(groups, inv, 8, b, 4)['groups'] == 24)
        refuses('counts that are not the bundle counts x s', groups, b, 2)
        p = b / 'counts/a_free_L8.txt'
        p.write_bytes(p.read_bytes().replace(b' 1024\n', b' 2048\n', 1))
        refuses('a bundle counts file altered after the freeze (its digest)', groups, b, 4)
    rec = dict(schema='c8-d2-gate-1', gate='A-ASM-7 verify_result_tamper', passed=not failed, failed=failed, checks=results)
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(rec, indent=1) + '\n')
    print(f'verify_result_tamper: {len(results) - len(failed)}/{len(results)} checks passed')
    return 0 if not failed else 1


if __name__ == '__main__':
    sys.exit(main())
