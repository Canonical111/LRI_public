#!/usr/bin/env python3
"""Assemble C0..C8(2) from complete independent finite-scheme RG-jet campaigns (PLAN.md component E).

The arithmetic is C63d's vendored order-8 assembly, vendor/c8_assembly/order8_assembly.py, imported only after its
sha256 equals the pin of tools/VENDORED.json (the HANDOFF's; PLAN "One rule governs reads of vendor/"):
campaign_moments (equal campaign weights 1/2), sector_assembly (C = F(f+p), C_pf = F(f), Delta_p and their
propagated covariances, note eq. c7d2:covariance; POWER_PROTOCOL PP9) and power_null_rows. This file adds:
  * hard gates at the data means (ArithmeticError, nonzero exit): the top-slot rule for L = 3..order, the loop-7
    entry at order 8, and the float affinity of loops 5..order. Each asserts the full loop coverage first, because
    the vendored gates skip absent loops (H2 review);
  * the power-sector report of the HANDOFF's POWER_PROTOCOL.md (requirements PP1-PP10 of the H2 review, step 6):
    C8 = F8(f+p) (PP1); C8^pf, Delta_p C8 with SE sqrt(V_Delta[8,8]) and the cross term (PP2); the null rows 3..7 with
    pull Delta/SE (PP3), flagged 'not proved zero' when |pull| > 3 (PP4), order 3 at rounding level when |Delta| <
    1e-12 (PP5); flags never change an estimate (PP6); the top-order pull is a diagnostic with no flag (PP7); a flag at
    order 6, or order 5 at d=2, is marked 'must be investigated' (PP8, which the vendored rows do not provide); the
    covariances of sector_assembly (PP9); the protocol's sha256, pinned before any data (PP10). Non-finite inputs and
    nonpositive SEs of the null rows are refused or flagged explicitly (H2 review);
  * lower-order checks C3..C(order-1) against the references of D11 with pulls over both SEs (a diagnostic,
    |pull| > 3 flagged), error_by_loop (each (sector, L) variance contribution to Var(C_order) and its share; they sum
    to Var(C_order)), the two campaigns, the half streams and a bootstrap (seed 70530413), and the coverage guard of a
    non-test campaign (all 24 groups; every group's graphs equal the inputs inventory's; with a design bundle, the
    counts equal the bundle's counts x s, read from counts/* files verified against their digests).
combine(ar, order=7) is the order-7 assembly of the same module, kept for A-ASM-3 (the 2026 C7(2) production).
load_campaign/evaluate read a campaign through tools/production.py (verify_base with the vendored pins, the group configs
and the validated merged.json of every group); the design bundle of a non-test campaign through production.design_bundle
(X9: the campaign's pinned copy, or --bundle DIR, each verified against the campaign's design_meta.json sha256).
Stage-6 fix round 4 (W23): nothing checked is read again. The coverage guard parses design_meta.json from bytes verified
against the campaign's pinned sha256 (meta_sha256) and the counts files from bytes verified against that meta, with
design.parse_counts (the strict reader of plan and design.py); evaluate takes the inventory from the bytes the campaign's
inputs manifest pins (production.verified_inventory); two_loop() hashes the bytes it parses; the result records the
sha256 of the order-8 module bytes that were verified and imported.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

from common import ROOT, canon, digest, dump, replace_file

RESULT_SCHEMA = 'c8-d2-hpc-result-1'
HALF_D = 1  # d/2 at d=2
VENDOR = ROOT / 'vendor/c8_assembly'
SECTORS, CAMPAIGNS = ('free', 'power'), ('a', 'b')
FLAG_PULL = 3.0
BOOTSTRAP_SEED = 70530413
ARCHIVED = 'archived 13-digit closed form (reference/power_mass/code/assemble_full.py); not exact'
# Lower-order references (PLAN D11). C3-C5: the archived 13-digit values of the closed forms, reference SE 0 (their
# rounding, about 1e-12, is far below every SE). C6(2): the 2026 production M=8192 (secondary: the archived Monte Carlo
# value). C7(2): the 2026 symmetry production (Codex-approved).
REFERENCE_LOWER = {3: (-.8748500126526, 0., ARCHIVED), 4: (5.048868431355, 0., ARCHIVED), 5: (-38.83364589623, 0., ARCHIVED),
                   6: (362.36647176375726, 0.0007997306822612242, 'C6(2) production M=8192, 2026-09-28 (LRI_C6_D2_HPC)'),
                   7: (-3876.1260927949925, 0.5244496690956952, 'C7(2) symmetry production run1-20260930-m4096 (LRI_C7_D2_HPC)')}
SECONDARY = {6: (362.3489137997967, 0.15264446036381157, 'archived Monte Carlo estimate in the same scheme '
                 '(reference/LRI_C7_d2_progress/code/finalize.py)')}
PP8_ORDERS = {2: (5, 6), 3: (6,)}  # POWER_PROTOCOL.md section 2: a flag here contradicts an MS numerical zero
PP8_TEXT = ('must be investigated: a flag at this order contradicts the MS numerical zero (POWER_PROTOCOL.md section '
            '2, PP8); it does not change the estimate')
META = ('schema', 'dimension', 'order', 'epsilon', 'scope')


# ---- the vendored module ----------------------------------------------------------------------------------------
_OA = None
_OA_SHA = None


def vendored():
    """order8_assembly.py from vendor/, imported once, after its sha256 equals the VENDORED.json pin. W23's class
    (Stage-6 fix round 4): the module is executed from the very bytes whose sha256 was checked (compiled from them,
    never re-read through the import system), and that sha256 is what the result records (module_sha256)."""
    global _OA, _OA_SHA
    if _OA is None:
        v = json.loads((ROOT / 'tools/VENDORED.json').read_bytes())
        pin = next(f['sha256'] for f in v['files'] if f['path'] == 'order8_assembly.py')
        path = VENDOR / 'order8_assembly.py'
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != pin:
            raise ValueError(f'{path} is not at its pinned sha256 {pin} (tools/VENDORED.json)')
        sys.dont_write_bytecode = True
        spec = importlib.util.spec_from_file_location('c8_order8_assembly', path)
        mod = importlib.util.module_from_spec(spec)
        # compiled from the verified bytes as exec_module compiles a source (dont_inherit: none of this file's __future__
        # flags); spec.loader.exec_module(mod) would read the file again, or a cached .pyc of other bytes
        exec(compile(data, str(path), 'exec', dont_inherit=True), mod.__dict__)
        _OA, _OA_SHA = mod, pin
    return _OA


def two_loop() -> tuple[np.ndarray, str]:
    """B2 of inputs/two_loop.json and the sha256 of the very bytes parsed (W23's class: one read, not a parse and a
    separate digest of the file)."""
    data = (ROOT / 'inputs/two_loop.json').read_bytes()
    return np.asarray(json.loads(data)['B2'], float), hashlib.sha256(data).hexdigest()


def coefficients(vals: dict, order: int = 8):
    """C_0..C_order at d=2 from the loop jets, with the package's B2 (the vendored coefficients)."""
    return vendored().coefficients(vals, two_loop()[0], order, HALF_D)


def jacobians(means: dict, order: int = 8) -> dict:
    """Complex-step Jacobians at d=2 with the package's B2 (the vendored jacobians; design.py and validate.py)."""
    return vendored().jacobians(means, two_loop()[0], order, HALF_D)


def power_protocol_sha256() -> str:
    v = json.loads((ROOT / 'tools/VENDORED.json').read_bytes())
    return v['power_protocol']['sha256']


# ---- pieces of the result ---------------------------------------------------------------------------------------
def pull(estimate: float, se: float, reference: float, reference_se: float):
    s = math.sqrt(se * se + reference_se * reference_se)
    return (estimate - reference) / s if s > 0 else None


def lower_order_checks(mu, se, order: int) -> list:
    """C3..C(order-1) against D11's references; the pull uses both SEs; |pull| > 3 is flagged (a diagnostic)."""
    out = []
    for k in range(3, order):
        ref, rse, src = REFERENCE_LOWER[k]
        p = pull(float(mu[k]), float(se[k]), ref, rse)
        row = dict(order=k, estimate=float(mu[k]), sampling_se=float(se[k]), reference=ref, reference_se=rse,
                   reference_source=src, pull=p, flag=p is not None and abs(p) > FLAG_PULL)
        if k in SECONDARY:
            r2, s2, src2 = SECONDARY[k]
            q = pull(float(mu[k]), float(se[k]), r2, s2)
            row['secondary'] = dict(reference=r2, reference_se=s2, reference_source=src2, pull=q,
                                    flag=q is not None and abs(q) > FLAG_PULL)
        out.append(row)
    return out


def power_null_checks(delta, dse, order: int, d: int = 2) -> dict:
    """The vendored null rows (PP3-PP5, PP7) with the package's guards and the PP8 marker."""
    delta, dse = np.asarray(delta, float), np.asarray(dse, float)
    if delta.shape != (order + 1,) or dse.shape != (order + 1,):
        raise ValueError(f'power_null_checks: need {order + 1} power differences and errors')
    if not (np.isfinite(delta).all() and np.isfinite(dse).all()) or (dse < 0).any():
        raise ArithmeticError('power_null_checks: non-finite power difference or negative SE')
    rows = vendored().power_null_rows(delta, dse, order)
    for r in rows['null_rows']:
        if r['order'] >= 4 and not r['se'] > 0:
            r['flag'] = 'SE not positive: pull undefined'
        r['investigate'] = PP8_TEXT if (r['order'] in PP8_ORDERS[d] and r['flag']) else None
    rows['flags'] = [r for r in rows['null_rows'] if r['flag']]
    rows['rule'] = ('POWER_PROTOCOL.md (vendored, sha256 in power_protocol_sha256): rows 3..order-1 are null rows, '
                    '|pull| > 3 flagged "not proved zero"; the top order is the reported correction with a diagnostic '
                    'pull and no flag; flags never change an estimate')
    return rows


def gates(means_total: dict, J: dict, B2, order: int) -> dict:
    """Hard gates at the data means (ArithmeticError on failure), each after asserting full loop coverage."""
    oa = vendored()
    want = list(range(3, order + 1))
    if sorted(J) != want or sorted(means_total) != want:
        raise ArithmeticError(f'gates: the Jacobians cover loops {sorted(J)}, need {want}')
    out = dict(top_slot=oa.top_slot_gate(J, order))
    if [r['L'] for r in out['top_slot']['rows']] != want:
        raise ArithmeticError('top-slot gate did not evaluate every loop')
    if order == 8:
        out['loop7'] = oa.loop7_gate(J, B2, order)
    aff = oa.affinity_gate(means_total, B2, order, HALF_D, loops=list(range(5, order + 1)))
    if aff['loops'] != list(range(5, order + 1)):
        raise ArithmeticError(f'affinity gate evaluated loops {aff["loops"]}')
    out['affinity'] = aff
    return out


def check_input(ar: dict, order: int) -> None:
    if set(ar) != set(SECTORS):
        raise ValueError('both sectors are required')
    for s in SECTORS:
        if set(ar[s]) != set(CAMPAIGNS):
            raise ValueError('need the two independent campaigns a and b')
        for t in CAMPAIGNS:
            if set(ar[s][t]) != set(range(3, order + 1)):
                raise ValueError(f'need all loops 3..{order} in {s}/{t}')
            for L, x in ar[s][t].items():
                x = np.asarray(x)
                if x.ndim != 2 or x.shape[1] != 2 * (order + 1 - L) or len(x) < 2 or not np.isfinite(x).all():
                    raise ValueError(f'invalid replicate data in {s}/{t}/L{L}')


def combine(ar: dict, order: int = 8, bootstrap: int = 1024) -> dict:
    """The pure assembly of ar[sector][campaign][L] (replicates x 2(order+1-L): the b jet, then the c jet)."""
    oa = vendored()
    check_input(ar, order)
    B2, b2sha = two_loop()
    loops = range(3, order + 1)
    means, vc = oa.campaign_moments(ar, loops)
    r = oa.sector_assembly(means, vc, B2, order, HALF_D)
    if r['max_order'] != order:
        raise ValueError(f'sector_assembly reported max_order {r["max_order"]}, not {order}')
    mu, pf, delta = r['coefficients'], r['power_free_coefficients'], r['power_differences']
    cov, dcov, pcov, cross = r['covariance'], r['power_difference_covariance'], r['power_free_covariance'], r['cross']
    se, dse = r['standard_errors'], r['power_difference_errors']
    m = {L: means['free'][L] + means['power'][L] for L in loops}
    g = gates(m, r['J'], B2, order)
    contrib = {s: {str(L): float(r['contributions'][s][L][order, order]) for L in loops} for s in SECTORS}
    var = float(cov[order, order])
    ebl = {s: {L: dict(variance=v, share=v / var if var > 0 else None, se=math.sqrt(max(0., v)))
               for L, v in contrib[s].items()} for s in SECTORS}
    camps = {}
    for t in CAMPAIGNS:
        mm = {L: np.asarray(ar['free'][t][L]).mean(0) + np.asarray(ar['power'][t][L]).mean(0) for L in loops}
        jj = oa.jacobians(mm, B2, order, HALF_D)
        cc = oa.coefficients(mm, B2, order, HALF_D)
        cv = sum(jj[L] @ (np.cov(ar['free'][t][L], rowvar=False) / len(ar['free'][t][L])
                          + np.cov(ar['power'][t][L], rowvar=False) / len(ar['power'][t][L])) @ jj[L].T for L in loops)
        camps[t] = {f'C{order}': float(cc[order]), 'sampling_se': float(max(0, cv[order, order]) ** .5)}
    halves = []
    for h in (0, 1):
        mm = {L: sum(np.asarray(ar[s][t][L])[h * len(ar[s][t][L]) // 2:(h + 1) * len(ar[s][t][L]) // 2].mean(0)
                     for s in SECTORS for t in CAMPAIGNS) / 2 for L in loops}
        halves.append(oa.coefficients(mm, B2, order, HALF_D).tolist())
    boot = None
    if bootstrap:
        rng = np.random.default_rng(BOOTSTRAP_SEED)
        xs, dx = np.empty((bootstrap, order + 1)), np.empty((bootstrap, order + 1))
        for i in range(bootstrap):
            mm = {s: {L: sum(np.asarray(ar[s][t][L])[rng.integers(len(ar[s][t][L]), size=len(ar[s][t][L]))].mean(0)
                             for t in CAMPAIGNS) / 2 for L in loops} for s in SECTORS}
            f = oa.coefficients({L: mm['free'][L] + mm['power'][L] for L in loops}, B2, order, HALF_D)
            xs[i], dx[i] = f, f - oa.coefficients(mm['free'], B2, order, HALF_D)
        boot = dict(replicates=bootstrap, seed=BOOTSTRAP_SEED, full_se=xs.std(0, ddof=1).tolist(),
                    correction_se=dx.std(0, ddof=1).tolist(), bias=(xs.mean(0) - mu).tolist(), diagnostic_only=True)
    n = order
    return {
        'schema': RESULT_SCHEMA, 'dimension': 2, 'order': order, 'epsilon': '2s-2',
        f'C{n}_full': float(mu[n]), 'sampling_standard_error': float(se[n]),
        'coefficients': mu.tolist(), 'standard_errors': se.tolist(), 'covariance': cov.tolist(),
        f'power_free_C{n}': float(pf[n]), 'power_free_se': float(max(0, pcov[n, n]) ** .5),
        'power_correction': float(delta[n]), 'power_correction_se': float(dse[n]),
        'power_free_correction_covariance': float(cross[n, n]),
        'power_differences': delta.tolist(), 'power_difference_errors': dse.tolist(),
        'means': {s: {str(L): np.asarray(v).tolist() for L, v in means[s].items()} for s in SECTORS},
        'error_by_loop': ebl, 'campaigns': camps, 'half_streams': halves, 'bootstrap': boot,
        'lower_order_checks': lower_order_checks(mu, se, order),
        'power_null_checks': power_null_checks(delta, dse, order),
        'gates': g,
        'power_protocol': dict(sha256=power_protocol_sha256(), path='vendor/c8_assembly/POWER_PROTOCOL.md',
                               requirements='PP1-PP10 of the H2 review record (step 6), all reported here'),
        'assembly': dict(module='vendor/c8_assembly/order8_assembly.py', module_sha256=_OA_SHA,  # the bytes verified and executed (W23's class)
                         handoff_sha256=digest(VENDOR / 'HANDOFF_assembly.json'), two_loop_sha256=b2sha, half_d=HALF_D),
        'scope': ('Sampling precision only. Both sectors are integrated explicitly; C = F(f+p) is reported with the '
                  'power-free part and the measured power correction, which is never assumed zero and never a '
                  'gate. Lower-order pulls and power null rows are diagnostics; the top-slot, loop-7 and affinity '
                  'gates are hard.')}


def check_combination(r: dict) -> None:
    """Internal consistency of a combined result: the error_by_loop variances sum to Var(C_order)."""
    n = r['order']
    tot = sum(v['variance'] for s in r['error_by_loop'].values() for v in s.values())
    var = r['covariance'][n][n]
    if not abs(tot - var) <= 1e-10 * max(abs(var), 1e-300):
        raise ArithmeticError(f'error_by_loop sums to {tot}, not Var(C{n}) = {var}')


def test_only_view(r: dict) -> dict:
    """A test-only or partial result holds no physical number: every field but the metadata moves under
    test_partial, and the top-level fields are null (C7(2) A-L19; A-ASM-5)."""
    r = dict(r)
    part = {k: r.pop(k) for k in list(r) if k not in META}
    r.update({k: None for k in part})
    r['test_partial'] = part
    r['test_only'] = True
    r['scope'] = ('INCOMPLETE workflow test (--test-graphs or a test-only plan). Not a physical coefficient; '
                  'partial values only under test_partial.')
    return r


# ---- coverage of a non-test campaign ----------------------------------------------------------------------------
def bundle_meta(bundle: Path, meta_sha256: str | None) -> dict:
    """W23 (Stage-6 fix round 4): a design bundle's design_meta.json parsed from ONE read of its bytes, which must have
    `meta_sha256` (the campaign's pinned design_meta.json sha256) when it is given. production.design_bundle checked the
    file's digest when it resolved the bundle; parsing a second read of it (as the coverage guard did) could use another
    meta, with other counts digests, than the one checked."""
    data = (Path(bundle) / 'design_meta.json').read_bytes()
    if meta_sha256 is not None and hashlib.sha256(data).hexdigest() != meta_sha256:
        raise ValueError(f'coverage: {Path(bundle) / "design_meta.json"} differs from the design_meta.json the campaign was planned with '
                         f'(sha256 {meta_sha256}): it changed after the bundle was resolved, or it is not the campaign\'s bundle')
    return json.loads(data)


def bundle_counts(bundle: Path, meta: dict, name: str) -> dict:
    """W23: counts/<campaign>_<sector>_L<L>.txt of a bundle, read once, verified against `meta`'s counts_sha256 and
    parsed by design.parse_counts (the strict reader plan and design.py use: '<graph> <positive count>' lines, no sign,
    separator, repeated graph or unterminated line)."""
    import design
    data = (Path(bundle) / name).read_bytes()
    if hashlib.sha256(data).hexdigest() != (meta.get('counts_sha256') or {}).get(name):
        raise ValueError(f'coverage: {name} differs from the digest in design_meta.json')
    return design.parse_counts(Path(bundle) / name, data)


def coverage_guard(groups: dict, inventory: dict, order: int = 8, bundle: Path | None = None, s_multiplier=None,
                   meta_sha256: str | None = None) -> dict:
    """Refuse a non-test campaign unless every (campaign, sector, L) group is present and its graph set equals the
    inputs inventory's for (sector, L) with positive counts; with a design bundle, every count equals the bundle's
    count x s, read from counts/<campaign>_<sector>_L<L>.txt verified against the digests in its design_meta.json.
    s_multiplier: one integer for every graph, or {stratum: s} with the design strata (free_L3..free_L8, the free L8
    primitives 'free_L8_primitive', power_L3..power_L8; tools/production.stratum_of).
    groups: {(campaign, sector, L): {graph id: points}}; inventory: inputs/inventory.json.
    W23 (Stage-6 fix round 4): design_meta.json is read once (bundle_meta) and, with meta_sha256 (the campaign's pin,
    which evaluate and combine pass), must have that sha256; each counts file is parsed strictly from its verified bytes
    (bundle_counts)."""
    want = {(c, s, L) for c in CAMPAIGNS for s in SECTORS for L in range(3, order + 1)}
    if set(groups) != want:
        raise ValueError(f'coverage: groups missing {sorted(want - set(groups))[:4]}, unexpected {sorted(set(groups) - want)[:4]}')
    meta = None
    if bundle is not None:
        meta = bundle_meta(bundle, meta_sha256)
    for (c, s, L), counts in sorted(groups.items()):
        rows = {int(row['id']): row for row in inventory[s][str(L)]}
        expect = set(rows)
        if set(map(int, counts)) != expect:
            raise ValueError(f'coverage: group {c}_{s}_L{L} has {len(counts)} graphs, the inventory {len(expect)}')
        if any(int(v) <= 0 for v in counts.values()):
            raise ValueError(f'coverage: group {c}_{s}_L{L} has a graph with no points')
        if meta is not None:
            name = f'counts/{c}_{s}_L{L}.txt'
            frozen = bundle_counts(bundle, meta, name)

            def mult(g):
                if isinstance(s_multiplier, dict):
                    st = f'free_L8_primitive' if (s == 'free' and L == 8 and rows[g].get('primitive')) else f'{s}_L{L}'
                    return int(s_multiplier[st])
                return int(s_multiplier)
            if {int(k): int(v) for k, v in counts.items()} != {k: v * mult(k) for k, v in frozen.items()}:
                raise ValueError(f'coverage: group {c}_{s}_L{L} counts differ from the bundle counts x s')
    return dict(groups=len(groups), graphs=sum(len(v) for v in groups.values()), bundle=str(bundle) if bundle else None)


# ---- campaigns ---------------------------------------------------------------------------------------------------
def load_campaign(directory: Path, accept_tool_change: bool = False):
    from production import group_of, validate_merged, verify_base
    m, _, mh, changes = verify_base(directory, check_executable=False, accept_tool_change=accept_tool_change, vendored=True)
    order = m.get('order', 8)
    if m['campaign_weights'] != {'a': .5, 'b': .5}:
        raise ValueError('changed campaign weights')
    ar = {s: {t: {} for t in CAMPAIGNS} for s in SECTORS}
    hashes, groups, seen = {}, {}, set()
    for gr in m['groups']:
        p, cfg = group_of(directory, m, gr['name'])
        d = validate_merged(p, cfg, m, mh)
        key = (cfg['sector'], cfg['campaign'], cfg['L'])
        if key in seen:
            raise ValueError('duplicate group')
        seen.add(key)
        x = np.asarray(d['batches'], float)
        if x.shape != (cfg['replicates'], 2 * (order + 1 - cfg['L'])):
            raise ValueError('wrong data shape')
        ar[key[0]][key[1]][key[2]] = x
        hashes[gr['name']] = digest(p / 'merged.json')
        groups[(cfg['campaign'], cfg['sector'], cfg['L'])] = cfg.get('graph_points') or {}
    return m, mh, ar, hashes, changes, groups


def evaluate(directory: Path, bootstrap: int = 1024, accept_tool_change: bool = False, bundle_override: Path | None = None) -> dict:
    """The result of a complete campaign. The design bundle of a non-test campaign is resolved by
    production.design_bundle (X9): bundle_override (--bundle, a relocated copy), else the campaign's pinned copy, else
    the planned path; each must have the design_meta.json sha256 the campaign pinned."""
    from production import design_bundle, verified_inventory
    m, mh, ar, hashes, changes, groups = load_campaign(directory, accept_tool_change)
    order = m.get('order', 8)
    if not m['test_only']:
        bundle = design_bundle(directory, m, bundle_override)
        # W23: the bundle's design_meta.json against the campaign's pin (one read), the inventory from verified bytes
        coverage_guard(groups, verified_inventory(m), order, bundle, m['design']['s'] if m.get('design') else None,
                       meta_sha256=m['design']['meta_sha256'] if m.get('design') else None)
    r = combine(ar, order, bootstrap)
    check_combination(r)
    if m['test_only']:
        r = test_only_view(r)
    r.update(source_manifest_sha256=mh, merged_sha256=hashes, backend=m['backend'], build=m['build'],
             test_only=m['test_only'], allocation=m.get('allocation'), final=not m['test_only'],
             numerics=m.get('numerics', 'exact'), rates_identity=m.get('rates_identity', 'default'))
    if changes:
        r['accepted_tool_changes'] = changes
    return r


def default_output(directory: Path, result: dict) -> Path:
    n = result['order']
    return directory / (f'C{n}_test_result.json' if result.get('test_only') else f'C{n}_result.json')


# Provenance fields a recomputed result may change while its scientific content stays the same (F8, A-ORC-12):
# merged_sha256 holds the sha256 of each group's merged.json, which also records timing (integration and row seconds,
# max_rss_kb, the graph_costs.csv digest) that changes whenever a block is recomputed.
SUPERSEDABLE = ('merged_sha256',)


def publish_result(dest: Path, result: dict) -> str:
    """No-clobber and idempotent: an existing identical result is kept. An existing result that differs only in
    SUPERSEDABLE fields, its scientific content unchanged (a group re-merged after the recovery of a completed index:
    the same batches, other timings), is superseded: the old bytes are kept as <name>.superseded.<sha256[:12]>.json
    and the new result replaces the file atomically (F8). Any other difference is a real conflict and an error."""
    if dest.exists():
        data = dest.read_bytes()
        old, new = json.loads(data), json.loads(json.dumps(result, allow_nan=False))
        if canon(old) == canon(new):
            return 'identical result already present; kept'
        strip = lambda d: {k: v for k, v in d.items() if k not in SUPERSEDABLE}  # noqa: E731
        if not isinstance(old, dict) or canon(strip(old)) != canon(strip(new)):
            raise ValueError(f'{dest} exists and differs from the recomputed result; not overwritten')
        sha = hashlib.sha256(data).hexdigest()
        keep = dest.with_name(f'{dest.stem}.superseded.{sha[:12]}{dest.suffix}')
        try:
            os.link(dest, keep)
            created = True
        except FileExistsError:  # superseded before (the same old bytes)
            created = False
        if digest(keep) != sha:
            if not created:
                raise ValueError(f'{keep} exists and is not the result it names; {dest} not superseded')
            keep.unlink()  # dest changed between the read and the link: decide again on its current bytes
            return publish_result(dest, result)
        replace_file(dest, (json.dumps(result, indent=2, allow_nan=False) + '\n').encode())
        ms_old, ms_new = old.get('merged_sha256') or {}, new.get('merged_sha256') or {}
        changed = sorted(g for g in set(ms_old) | set(ms_new) if ms_old.get(g) != ms_new.get(g))
        return (f'superseded: scientific content unchanged, merged_sha256 changed for {", ".join(changed) or "no group"}; '
                f'previous result kept as {keep.name}')
    try:
        dump(dest, result)
        return 'written'
    except FileExistsError:
        return publish_result(dest, result)


def summary_lines(r: dict) -> list[str]:
    """Human-readable diagnostics; FLAG marks |pull| > 3 (a diagnostic, not a hard gate)."""
    src = r.get('test_partial') or r
    out = []
    f = lambda p: 'n/a' if p is None else f'{p:+.2f}'
    for c in src.get('lower_order_checks') or []:
        line = (f"C{c['order']}: {c['estimate']:.12g} +/- {c['sampling_se']:.3g} vs {c['reference']:.12g} +/- "
                f"{c['reference_se']:.3g}  pull {f(c['pull'])}")
        if 'secondary' in c:
            line += f"  (secondary {c['secondary']['reference']:.10g}: pull {f(c['secondary']['pull'])})"
        out.append(('FLAG |pull|>3 (diagnostic) ' if c['flag'] else '') + line)
    pn = src.get('power_null_checks') or {}
    for c in pn.get('null_rows', []):
        tail = c.get('note') or (f"pull {f(c['pull'])}")
        line = f"power_differences[{c['order']}]: {c['delta']:.3g} +/- {c['se']:.3g}  {tail}"
        out.append((f'FLAG {c["flag"]} ' if c['flag'] else '') + line + (f'  [{c["investigate"]}]' if c.get('investigate') else ''))
    if pn.get('top'):
        t = pn['top']
        out.append(f"power correction (order {t['order']}): {t['delta']:.6g} +/- {t['se']:.3g}  diagnostic pull {f(t['pull'])}")
    if r.get('test_only'):
        out = ['(test-only partial values)'] + out
    return out


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('directory', type=Path)
    p.add_argument('--bootstrap', type=int, default=1024)
    p.add_argument('--output', type=Path)
    p.add_argument('--accept-tool-change', action='store_true')
    p.add_argument('--bundle', type=Path, help='a relocated copy of the design bundle (its design_meta.json must have the sha256 the campaign '
                   'pinned); by default the campaign\'s pinned copy <campaign>/design_bundle, or the planned path')
    a = p.parse_args()
    if a.bootstrap < 0 or a.bootstrap == 1:
        raise ValueError('bootstrap must be zero or >= 2')
    r = evaluate(a.directory.resolve(), a.bootstrap, a.accept_tool_change, a.bundle)
    dest = a.output or default_output(a.directory, r)
    state = publish_result(dest, r)
    n = r['order']
    print(json.dumps({f'C{n}_full': r[f'C{n}_full'], 'sampling_standard_error': r['sampling_standard_error'],
                      'test_only': r['test_only'], 'numerics': r['numerics'], 'rates_identity': r['rates_identity'],
                      'output': str(dest), 'state': state}))
    for line in summary_lines(r):
        print(line)


if __name__ == '__main__':
    try:
        main()
    except ArithmeticError as e:
        print(f'assemble: hard gate failed: {e}', file=sys.stderr)
        sys.exit(3)
