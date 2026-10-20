#!/usr/bin/env python3
"""tools/combine.py's core on synthetic batches (Stage 2b wiring; A-ASM-6 on real campaigns is test_pipeline.py in
Stage 3): two batches of one design combine into the assembly of the concatenated replicates, with the per-batch C8
and the chi-square about the combination equal to hand values, and the combined result verifies; one batch of two
gives a partial result (final false); and combine refuses a different bundle, inputs manifest, numerics profile or
rates identity, a repeated group seed, a repeated label, fewer batches than the bundle without --partial, and
--partial with the full count. Z8 (Stage-6 fix round 3): combine refuses (verify_result, before publication) an
assembly whose combined covariance is asymmetric or indefinite, and accepts the same combination untouched.
Usage: python3 -B tests/combine_core.py [--output FILE]"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from unittest import mock

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))
import assemble as asm  # noqa: E402
import combine  # noqa: E402
from assembly_checks import synthetic_ar  # noqa: E402


def batch(label: str, seed: int, seeds: list[int], **kw) -> dict:
    b = dict(label=label, design_sha256='d' * 64, inputs_manifest_sha256='i' * 64, numerics='exact', rates_identity='default',
             seeds=seeds, ar=synthetic_ar(np.random.default_rng(seed), R=6))
    b.update(kw)
    return b


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--output', type=Path)
    a = ap.parse_args()
    results, failed = [], []

    def check(name: str, ok: bool, detail='') -> None:
        detail = detail if isinstance(detail, str) else json.dumps(detail, default=str)
        results.append(dict(check=name, passed=bool(ok), detail=detail[-600:]))
        if not ok:
            failed.append(name)
        print(('PASS ' if ok else 'FAIL ') + name + (f': {detail[-300:]}' if detail and not ok else ''), flush=True)

    b1, b2 = batch('sym', 11, list(range(24))), batch('exp', 22, list(range(100, 124)))
    r = combine.combine_batches([b1, b2], planned=2, bootstrap=8)
    cat = {s: {t: {L: np.concatenate([b1['ar'][s][t][L], b2['ar'][s][t][L]]) for L in range(3, 9)} for t in 'ab'} for s in ('free', 'power')}
    ref = asm.combine(cat, 8, 8)
    per = [asm.combine(b['ar'], 8, 0) for b in (b1, b2)]
    chi2 = sum((x['C8_full'] - ref['C8_full']) ** 2 / x['sampling_standard_error'] ** 2 for x in per)
    check('two batches combine into the assembly of the concatenated replicates', r['C8_full'] == ref['C8_full']
          and r['coefficients'] == ref['coefficients'] and r['final'] is True and r['batches']['count'] == 2)
    check('per-batch C8 and the chi-square about the combination equal hand values',
          [x['C8_full'] for x in r['batches']['per_batch']] == [x['C8_full'] for x in per]
          and abs(r['batches']['chi2_about_combined'] - chi2) <= 1e-12 * max(1, chi2) and r['batches']['dof'] == 1)
    p = combine.combine_batches([b1], planned=2, partial=True, bootstrap=0)
    check('one batch of two gives a partial result (final false)', p['final'] is False and p['status'].startswith('PARTIAL'))

    def refuses(name: str, bs: list, planned: int = 2, partial: bool = False) -> None:
        try:
            combine.combine_batches(bs, planned=planned, partial=partial, bootstrap=0)
            check(f'refuses {name}', False, 'accepted')
        except ValueError as e:
            check(f'refuses {name}', True, str(e))

    refuses('a different design bundle', [b1, dict(b2, design_sha256='e' * 64)])
    refuses('a different inputs manifest', [b1, dict(b2, inputs_manifest_sha256='j' * 64)])
    refuses('a different numerics profile', [b1, dict(b2, numerics='dd')])
    refuses('a different rates identity', [b1, dict(b2, rates_identity='f' * 64)])
    refuses('a repeated group seed', [b1, dict(b2, seeds=[0] + b2['seeds'][1:])])
    refuses('a repeated label', [b1, dict(b2, label='sym')])
    refuses('fewer batches than the bundle without --partial', [b1])
    refuses('--partial with the full batch count', [b1, b2], partial=True)
    # Z8 (Stage-6 fix round 3): combine verifies before publishing, and verify_result now refuses a covariance that is not
    # one: an assembly whose combined covariance is asymmetric (covariance[3][8] = 1e30, the finding) or indefinite
    # (correlations 0.9, 0.9, -0.9 among orders 6..8) is refused (ArithmeticError), the untouched one accepted
    real = asm.combine

    def tampered(edit):
        def f(ar, order=8, bootstrap=1024):
            res = real(ar, order, bootstrap)
            if bootstrap:  # the combined assembly (the per-batch ones run with bootstrap 0)
                edit(res['covariance'])
            return res
        return f

    def asym(c):
        c[3][8] = 1e30

    def indefinite(c):
        s = np.sqrt(np.maximum(np.diag(np.asarray(c, float)), 0.))
        for (i, j), rho in (((6, 7), .9), ((6, 8), .9), ((7, 8), -.9)):
            c[i][j] = c[j][i] = rho * s[i] * s[j]
    for name, edit in (('asymmetric', asym), ('indefinite', indefinite)):
        try:
            with mock.patch.object(asm, 'combine', tampered(edit)):
                combine.combine_batches([b1, b2], planned=2, bootstrap=8)
            check(f'Z8: refuses a combination whose covariance is {name}', False, 'accepted')
        except ArithmeticError as e:
            check(f'Z8: refuses a combination whose covariance is {name}', 'Z8' in str(e), str(e))
    with mock.patch.object(asm, 'combine', tampered(lambda c: None)):
        check('Z8: the same combination with its covariance untouched is accepted', bool(combine.combine_batches([b1, b2], planned=2, bootstrap=8)))
    rec = dict(schema='c8-d2-gate-1', gate='combine core (synthetic)', passed=not failed, failed=failed, checks=results)
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(rec, indent=1) + '\n')
    print(f'combine_core: {len(results) - len(failed)}/{len(results)} checks passed')
    return 0 if not failed else 1


if __name__ == '__main__':
    sys.exit(main())
