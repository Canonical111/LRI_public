#!/usr/bin/env python3
"""Combine K independent production batches of one frozen design into one C8(2) result (PLAN.md component E).

A batch is a complete campaign directory planned with `production.py plan --design BUNDLE`, for example a symmetry
batch and an Expanse batch. Every batch must share the design bundle (the sha256 of its design_meta.json), the inputs
manifest, the numerics profile and the rates identity ('default', or the same frozen-map sha256; R04); pass the
coverage guard (tools/assemble.coverage_guard: all 24 groups, every group's graphs equal the inputs inventory's, the
counts equal the bundle's counts x s); and every group seed must be distinct across the batches. The replicates of
each (sector, campaign, L) are concatenated over the batches and assembled by tools/assemble.combine, the vendored
order-8 module. C8 of every batch and the inter-batch chi-square about the combination are reported. --partial
publishes C8_partial.json (final: false) for fewer batches than the bundle's batch count; the final combination needs
exactly that count (C8(1) R23) and is published as C8_final.json. tools/verify_result.py checks the combined result
before it is published, and publication is no-clobber.

Campaign interface (tools/production.py): the manifest carries design = {bundle, meta_sha256, design_sha256, batches,
s (per stratum), r (per sector and loop)}, inputs_manifest_sha256, numerics, rates_identity and test_only; each group
config carries seed and graph_points. The bundle's design_meta.json must still have the sha256 the batch was planned
with. The bundle is read from each batch's pinned copy <batch>/design_bundle (plans since X9), so batches copied
between sites combine without the original bundle path; --bundle DIR names a relocated copy instead (needed for batches
planned before the pinned copy), always verified against each batch's pinned design_meta.json sha256.
combine_batches() is the pure core (unit-tested on synthetic batches, tests/combine_core.py); A-ASM-6 on real
campaign directories is tests/test_pipeline.py.
Stage-6 fix round 4 (W23): a batch's checked files are never read again. The coverage checks parse design_meta.json
from one read verified against the batch's pinned sha256 and each counts file strictly from its verified bytes; the
inventory comes from the bytes the batch's inputs manifest pins and each group seed from its verified config.
Usage: python3 -B tools/combine.py BATCH [BATCH ...] --output DIR [--partial] [--bootstrap N] [--bundle DIR]"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import assemble as asm  # noqa: E402
import verify_result as vr  # noqa: E402

SAME = ('design_sha256', 'inputs_manifest_sha256', 'numerics', 'rates_identity')


def combine_batches(batches: list[dict], planned: int, partial: bool = False, bootstrap: int = 1024, order: int = 8,
                    test_only: bool = False) -> dict:
    """batches: [{label, design_sha256, inputs_manifest_sha256, numerics, rates_identity, seeds, ar[, graphs]}], each
    complete. Refuses (ValueError) different bundles, inputs, numerics or rates identities, repeated labels or group seeds,
    different graph sets of a group (test-only batches), and a batch count that does not match the bundle (final) or is
    not below it (partial). test_only: the batches are test-only campaigns of a --test-only bundle; the result holds
    no physical number (every value under test_partial)."""
    if not batches:
        raise ValueError('no batch given')
    if test_only:
        sets = {json.dumps(b.get('graphs'), sort_keys=True) for b in batches}
        if len(sets) != 1:
            raise ValueError('the test-only batches integrate different graph sets in some group; they estimate different quantities')
    for key in SAME:
        vals = {json.dumps(b[key], sort_keys=True) for b in batches}
        if len(vals) != 1:
            raise ValueError(f'the batches differ in {key}: {sorted(vals)}; batches of different designs, inputs, numerics '
                             'or rates cannot be combined')
    labels = [b['label'] for b in batches]
    if len(set(labels)) != len(labels):
        raise ValueError('batch labels must be distinct')
    seeds = [s for b in batches for s in b['seeds']]
    if len(set(seeds)) != len(seeds):
        raise ValueError('a group seed repeats across the batches: the batches are not independent')
    K = len(batches)
    if partial and K >= planned:
        raise ValueError(f'--partial is for fewer batches than the bundle\'s {planned}')
    if not partial and K != planned:
        raise ValueError(f'the frozen design has {planned} batches; {K} given (use --partial for an interim combination)')
    cat = {s: {t: {L: np.concatenate([np.asarray(b['ar'][s][t][L], float) for b in batches])
                   for L in range(3, order + 1)} for t in asm.CAMPAIGNS} for s in asm.SECTORS}
    result = asm.combine(cat, order, bootstrap)
    asm.check_combination(result)
    per = []
    for b in batches:
        rb = asm.combine(b['ar'], order, 0)
        per.append({'label': b['label'], f'C{order}_full': rb[f'C{order}_full'], 'sampling_se': rb['sampling_standard_error']})
    c = result[f'C{order}_full']
    chi2 = sum((x[f'C{order}_full'] - c) ** 2 / x['sampling_se'] ** 2 for x in per) if K > 1 else None
    result['batches'] = dict(count=K, planned=planned, per_batch=per, chi2_about_combined=chi2, dof=K - 1)
    result['final'] = not partial
    result['status'] = vr.combination_status(K, planned)  # partial exactly when K < planned (both refused otherwise)
    for key in SAME:
        result[{'design_sha256': 'design', 'inputs_manifest_sha256': 'inputs_manifest_sha256', 'numerics': 'numerics',
                'rates_identity': 'rates_identity'}[key]] = batches[0][key]
    if test_only:
        result = asm.test_only_view(result)
        result['scope'] = ('TEST-ONLY combination of test-only batches (--test-graphs) of a --test-only design bundle: not a physical '
                           'coefficient; partial values only under test_partial.')
    problems = vr.verify(json.loads(json.dumps(result)))
    if problems:
        raise ArithmeticError(f'the combined result does not verify: {problems[:5]}')
    return result


def test_coverage(groups: dict, inventory: dict, bundle: Path, s_map: dict, order: int = 8, meta_sha256: str | None = None) -> None:
    """The test-only coverage check: all 24 groups present, every graph of a group in the inventory, and its count equal
    to the bundle count x s (the graph SET is the --test-graphs selection, compared across batches by combine_batches).
    W23 (Stage-6 fix round 4): design_meta.json is read once and, with meta_sha256 (the batch's pinned design_meta.json
    sha256, which load_batch passes), must have that sha256 (assemble.bundle_meta); each counts file is parsed strictly
    from its verified bytes (assemble.bundle_counts: design.parse_counts), a graph the bundle does not list refused."""
    meta = asm.bundle_meta(bundle, meta_sha256)
    want = {(c, s, L) for c in asm.CAMPAIGNS for s in asm.SECTORS for L in range(3, order + 1)}
    if set(groups) != want:
        raise ValueError(f'coverage: groups missing {sorted(want - set(groups))[:4]}')
    for (c, s, L), counts in groups.items():
        rows = {int(r['id']): r for r in inventory[s][str(L)]}
        if not set(map(int, counts)) <= set(rows):
            raise ValueError(f'coverage: group {c}_{s}_L{L} has graphs outside the inventory')
        name = f'counts/{c}_{s}_L{L}.txt'
        frozen = asm.bundle_counts(bundle, meta, name)
        for g, n in counts.items():
            st = 'free_L8_primitive' if (s == 'free' and L == 8 and rows[int(g)].get('primitive')) else f'{s}_L{L}'
            if int(g) not in frozen or int(n) != frozen[int(g)] * int(s_map[st]):
                raise ValueError(f'coverage: group {c}_{s}_L{L} graph {g} counts differ from the bundle counts x s')


def load_batch(directory: Path, test_only: bool = False, bundle_override: Path | None = None) -> dict:
    """A complete campaign of a design bundle, through assemble.load_campaign and the coverage guard (non-test), or a
    complete test-only campaign of a --test-only bundle with test_only. The bundle is resolved by
    production.design_bundle (X9): bundle_override (--bundle), else the batch's pinned copy, else its planned path, each
    verified against the batch's design_meta.json sha256 (the batch manifest is never rewritten)."""
    from production import design_bundle, group_of, verified_inventory
    m, mh, ar, hashes, changes, groups = asm.load_campaign(directory)
    if m.get('test_only') and not test_only:
        raise ValueError(f'{directory}: a test-only campaign is combined only with --test-only (and never into a physical result)')
    if test_only and not m.get('test_only'):
        raise ValueError(f'{directory}: --test-only combines test-only campaigns only')
    d = m.get('design') or {}
    if not d.get('meta_sha256') or not d.get('batches'):
        raise ValueError(f'{directory}: not planned against a design bundle')
    try:
        bundle = design_bundle(directory, m, bundle_override)
    except ValueError as e:
        raise ValueError(f'{directory}: {e}') from e
    # W23 (Stage-6 fix round 4): nothing checked is read again. The inventory from the bytes the batch's inputs manifest
    # pins, design_meta.json against the batch's pin (one read), and each group seed from its config verified against
    # the manifest (production.group_of), as load_campaign verified it (a plain re-read could carry another seed)
    inv = verified_inventory(m)
    if test_only:
        test_coverage(groups, inv, bundle, d['s'], m.get('order', 8), meta_sha256=d['meta_sha256'])
    else:
        asm.coverage_guard(groups, inv, m.get('order', 8), bundle, d['s'], meta_sha256=d['meta_sha256'])
    seeds = [group_of(directory, m, gr['name'])[1]['seed'] for gr in m['groups']]
    return dict(label=directory.name, design_sha256=d['meta_sha256'], planned=int(d['batches']),
                inputs_manifest_sha256=m['inputs_manifest_sha256'], numerics=m.get('numerics', 'exact'),
                rates_identity=m.get('rates_identity', 'default'), seeds=seeds, ar=ar, manifest_sha256=mh, merged=hashes,
                graphs={f'{c}_{s}_L{L}': sorted(map(int, v)) for (c, s, L), v in groups.items()})


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('batches', type=Path, nargs='+')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--partial', action='store_true')
    p.add_argument('--bootstrap', type=int, default=1024)
    p.add_argument('--test-only', action='store_true', help='combine test-only batches of a --test-only bundle (no physical value)')
    p.add_argument('--bundle', type=Path, help='a relocated copy of the batches\' design bundle, verified against each batch\'s pinned '
                   'design_meta.json sha256 (default: each batch\'s pinned copy <batch>/design_bundle, or its planned path)')
    a = p.parse_args()
    dirs = [b.resolve() for b in a.batches]
    if len(set(dirs)) != len(dirs):
        raise ValueError('a batch is listed twice')
    batches = [load_batch(d, a.test_only, a.bundle) for d in dirs]
    planned = {b['planned'] for b in batches}
    if len(planned) != 1:
        raise ValueError('the batches name different planned batch counts')
    r = combine_batches(batches, planned.pop(), a.partial, a.bootstrap, test_only=a.test_only)
    a.output.mkdir(parents=True, exist_ok=True)
    stem = 'C8_test_' if a.test_only else 'C8_'
    dest = a.output / (stem + ('partial.json' if a.partial else 'final.json'))
    state = asm.publish_result(dest, r)
    src = r.get('test_partial') or r
    print(json.dumps({'batches': r['batches']['count'] if 'batches' in r and r['batches'] else src['batches']['count'],
                      'C8_full': r['C8_full'], 'test_only': a.test_only, 'test_partial_C8': src.get('C8_full') if a.test_only else None,
                      'sampling_se': r['sampling_standard_error'], 'chi2': src['batches']['chi2_about_combined'], 'dof': src['batches']['dof'],
                      'final': r.get('final', src.get('final')), 'numerics': r.get('numerics', src.get('numerics')),
                      'rates_identity': r.get('rates_identity', src.get('rates_identity')), 'output': str(dest), 'state': state,
                      'sources': [str(d) for d in dirs]}, indent=1))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, ArithmeticError) as e:
        print('combine failed:', e, file=sys.stderr)
        sys.exit(2)
