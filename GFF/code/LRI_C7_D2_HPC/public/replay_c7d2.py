#!/usr/bin/env python3
"""Replay of the full seventh-order coefficient C7(2) (note Section 28, Section 1 tables, Section 33) from its merged records.

Run from the package folder (GFF/code/LRI_C7_D2_HPC, git commit fb64c47) as `make -f public.mk replay`. Nothing is
integrated. The production's own assembly, tools/assemble.py `evaluate()` at the commit that ran (its hash is pinned by the
production plan and checked below), recombines the 20 per-group merged records of the 2026 production with the same
bootstrap (4,096 resamples, fixed seed). The result is compared field by field with the published C7_result.json. Then
every number that the note (and the paper's number macros) quotes for C7(2) is recomputed and compared at its printed digits.
Finally the package's own tools/reassemble_reference.py re-assembles the previous calculation (-3950 +- 310) from the
archived records under reference/.

Inputs (relative to the package folder):
  ../../data/C7_2/run1-20260930-m4096/   manifest.json, cost_model.json, groups/<g>/{config,merged}.json (20 groups)
  ../../results/C7_2/C7_result.json      the published result (canonical cross-package path)
  ../../results/C7_2/evidence/           build and test records of the production host (symmetry job 566254)
  ../../results/C6_2/C6_result.json      the C6(2) production, reference of the sixth-order by-product check
  reference/                             the previous calculation, its coverage and check records (shipped in this package)

Not read (hosted, see DATA.md): groups/*/graph_replicates.csv (pinned by each merged.json; the delivered evaluate() checks
its hash, here that one check is skipped and reported), the checkpoints, tasks.sqlite and sobol.bin of every group, and
the production executable bin/c7d2_gmp (sha256 7e3c8c92..., pinned by the plan and checked by the delivered verify_base();
the replay needs no executable, so that check is reported as SKIP unless a matching binary is present).

Tolerances. Same records, same code: the recombination is deterministic numpy arithmetic (complex-step Jacobians, small
matrix products, a PCG64 bootstrap with seed 70530413), so differences come only from the summation order of numpy
reductions, which changes between numpy versions and platforms. Checked on 2026-10-13 against the record written on the
production host (Linux x86-64, Python 3.11, numpy 2.3.5): macOS arm64 with numpy 1.23.5 (Python 3.10), 1.26.3 (3.11) and
2.4.4 (3.14). Observed: C7 within 2.8e-12 absolute (7e-16 relative), every headline field within 4e-15 relative,
bootstrap SEs within 6e-14 relative, every cancellation-limited field within 1.8e-12 absolute (the power correction
differs by 3.2e-11 relative, because it is the difference of two values of size 3876).
  - Headline fields (C7_full, sampling_standard_error, coefficients, standard_errors, power_free_C7, power_free_se,
    campaigns, half_streams, means, error_by_loop, and estimate/sampling_se/reference of lower_order_checks):
    |delta| <= 1e-12 |ref| where |ref| > 1e-9, else |delta| <= 1e-12 (for C7 this is 1e-12 |C7|).
    Every other float field (e.g. shared_reference_se) is held to the same tier.
  - Cancellation-limited fields (power_correction and its SE, power_differences, power_difference_errors, the
    covariances, power_free_correction_covariance, bootstrap): relative 1e-7 where |ref| > 1e-9, or |delta| <= 1e-12 |C7|
    = 3.9e-9.
  - Integers, schemas, hashes, strings, booleans and nulls: exact.
  - Quoted numbers: equal after rounding to the digits the note prints. The 17-digit estimator of Section 1 is compared
    with the record exactly and with the recomputation within the headline tolerance.
Output: a PASS/FAIL/SKIP table on stdout, public/out/replay.json; exit status 1 on any FAIL. SKIP rows are not failures.
"""
import argparse, hashlib, json, math, os, re, subprocess, sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / 'tools'))
import numpy as np  # noqa: E402
import assemble  # noqa: E402  (fb64c47 tools/assemble.py: the assembly that wrote C7_result.json)
import production  # noqa: E402
from common import object_hash  # noqa: E402

HEADLINE = ('C7_full', 'sampling_standard_error', 'coefficients', 'standard_errors', 'power_free_C7', 'power_free_se',
            'campaigns', 'half_streams', 'means', 'error_by_loop')
HEADLINE_CHECK_LEAVES = ('estimate', 'sampling_se', 'reference')
CANCEL = ('power_correction', 'power_correction_se', 'power_differences', 'power_difference_errors', 'covariance',
          'power_free_correction_covariance', 'bootstrap')
RTOL_HEAD, ATOL_HEAD, RTOL_CANCEL, TINY = 1e-12, 1e-12, 1e-7, 1e-9
ROWS = []


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p): return json.loads(Path(p).read_text())


def row(name, got, want, ok, note=''):
    ROWS.append(dict(check=name, got=got, expected=want, status='PASS' if ok else 'FAIL', note=note))


def skip(name, note):
    ROWS.append(dict(check=name, got='-', expected='-', status='SKIP', note=note))


def quoted(name, value, text, note=''):
    """PASS when value, printed with as many decimals as the quoted text, equals the quoted text."""
    t = text.replace('+', '').replace(',', '')
    nd = len(t.split('.')[1]) if '.' in t else 0
    got = f'{value:.{nd}f}'
    if text.startswith('+') and not got.startswith('-'): got = '+' + got
    row(name, got, text, float(got) == float(t), note)


def flat(x, p=''):
    if isinstance(x, dict):
        for k, v in x.items(): yield from flat(v, f'{p}.{k}' if p else k)
    elif isinstance(x, list):
        for i, v in enumerate(x): yield from flat(v, f'{p}[{i}]')
    else: yield p, x


def compare_results(got, ref):
    G, F = dict(flat(got)), dict(flat(ref))
    c7 = abs(ref['C7_full']); worst_head = worst = 0.0; bad = []; n_float = 0
    for k, w in F.items():
        if k not in G: bad.append(f'{k}: missing'); continue
        g = G[k]
        if (isinstance(w, bool) or not isinstance(w, (int, float)) or not isinstance(g, (int, float)) or w is None
                or (isinstance(w, int) and isinstance(g, int))):
            if g != w or type(g) is not type(w): bad.append(f'{k}: {g!r} != {w!r}')
            continue
        n_float += 1; top = k.split('.')[0].split('[')[0]; d = abs(g - w)
        if top in CANCEL:
            rel = d / abs(w) if abs(w) > TINY else math.inf
            ok = rel <= RTOL_CANCEL or d <= 1e-12 * c7
            worst = max(worst, d)
        else:  # headline tier (HEADLINE, HEADLINE_CHECK_LEAVES and any other float field, e.g. shared_reference_se)
            ok = d <= (RTOL_HEAD * abs(w) if abs(w) > TINY else ATOL_HEAD)
            worst_head = max(worst_head, d / abs(w) if abs(w) > TINY else 0.0)
        if not ok: bad.append(f'{k}: {g!r} vs {w!r}')
    extra = sorted(set(G) - set(F))
    if extra: bad.append('extra fields: ' + ', '.join(extra[:5]))
    row(f'recombined result equals C7_result.json (all {len(F)} fields, {n_float} numeric)', f'{len(bad)} differences',
        '0 differences', not bad, f'max rel headline {worst_head:.1e}, max abs cancellation-limited {worst:.1e}'
        + ('; ' + '; '.join(bad[:4]) if bad else ''))


def verify_plan(run, ref):
    """The delivered production.verify_base() checks, except the executable; plus the record bindings."""
    m = load(run / 'manifest.json'); mh = sha(run / 'manifest.json')
    row('plan schema c7-d2-production-1, dimension 2, order 7', f"{m['schema']}, d={m['dimension']}, order {m['order']}",
        'c7-d2-production-1, d=2, order 7', (m['schema'], m['dimension'], m['order']) == ('c7-d2-production-1', 2, 7))
    row('manifest sha256 = C7_result.json source_manifest_sha256', mh[:16], ref['source_manifest_sha256'][:16],
        mh == ref['source_manifest_sha256'])
    diff = [n for n, h in m['tool_sha256'].items() if sha(PKG / 'tools' / n) != h]
    row(f'shipped tools/ equal the {len(m["tool_sha256"])} tools pinned by the plan (code is fb64c47)', f'{len(diff)} differ',
        '0 differ', not diff, ', '.join(diff))
    im = load(PKG / 'inputs/manifest.json')
    small = ('gamma_d2_7.txt', 'two_loop.json', 'primitive_reference.json', 'inventory.json')
    ok = sha(PKG / 'inputs/manifest.json') == m['inputs_manifest_sha256'] and all(sha(PKG / 'inputs' / n) == im['sha256'][n] for n in small)
    row('inputs/manifest.json and its four small inputs as pinned', 'match' if ok else 'mismatch', 'match', ok)
    ok = sha(run / 'cost_model.json') == m['cost_model_sha256']
    row('cost_model.json as pinned (task placement only)', 'match' if ok else 'mismatch', 'match', ok)
    exe = PKG / 'bin' / ('c7d2_gmp' if m['backend'] == 'gmp' else 'c7d2_decimal')
    if exe.exists() and sha(exe) == m['executable_sha256']:
        row('production executable as pinned', sha(exe)[:16], m['executable_sha256'][:16], True)
    else:
        skip(f'production executable sha256 {m["executable_sha256"][:12]}... (bin/c7d2_gmp)',
             'not needed by replay; byte-reproducible only with GCC 11.4, Boost 1.77 headers, GMP 6.2.1 on x86-64 (symmetry, D1)')
    bad = []; samples = 0
    for g in m['groups']:
        p = run / 'groups' / g['name']; cfg = load(p / 'config.json'); d = load(p / 'merged.json')
        if sha(p / 'config.json') != g['sha256']: bad.append(g['name'] + ' config')
        if sha(p / 'merged.json') != ref['merged_sha256'][g['name']]: bad.append(g['name'] + ' merged')
        if object_hash({k: v for k, v in d.items() if k != 'payload_sha256'}) != d['payload_sha256']: bad.append(g['name'] + ' payload')
        if (d['manifest_sha256'] != mh or d['config_hash'] != object_hash(cfg) or d.get('complete') is not True
                or d['schema'] != 'c7-d2-merged-1' or d['sector'] != cfg['sector'] or d['primitive_mode'] != m['primitive_mode']):
            bad.append(g['name'] + ' identity')
        if np.asarray(d['batches'], float).shape != (cfg['replicates'], 2 * (8 - cfg['L'])): bad.append(g['name'] + ' shape')
        samples += d['samples']
    row(f'{len(m["groups"])} group configs and merged records verify (hashes, identity, shape)', f'{len(bad)} bad', '0 bad',
        not bad and len(ref['merged_sha256']) == len(m['groups']) == 20, ', '.join(bad[:6]))
    skip('groups/*/graph_replicates.csv sha256 (pinned by each merged.json, checked by the delivered evaluate())',
         'hosted (23.5 MiB, DATA.md part b); the per-graph table is not used by the assembly')
    return m, im, samples


def campaign_mean_se(run, sector, L):
    """Combined campaign mean and its sampling SE for one sector and loop, as tools/assemble.calculate forms them."""
    xs = [np.asarray(load(run / 'groups' / f'{t}_{sector}_L{L}' / 'merged.json')['batches'], float) for t in 'ab']
    mean = sum(x.mean(0) for x in xs) / 2
    var = sum(np.diag(np.cov(x, rowvar=False, ddof=1)) / len(x) for x in xs) / 4
    return mean, np.sqrt(var)


def pull(a, sa, b, sb): return (a - b) / math.hypot(sa, sb)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--data', type=Path, default=PKG / '../../data/C7_2/run1-20260930-m4096')
    ap.add_argument('--results', type=Path, default=PKG / '../../results/C7_2')
    ap.add_argument('--c6', type=Path, default=PKG / '../../results/C6_2/C6_result.json')
    ap.add_argument('--out', type=Path, default=PKG / 'public/out')
    ap.add_argument('--skip-reference', action='store_true', help='do not run tools/reassemble_reference.py')
    a = ap.parse_args(); run, res = a.data.resolve(), a.results.resolve()
    ref = load(res / 'C7_result.json')
    m, im, samples = verify_plan(run, ref)

    # --- recombination with the delivered evaluate(): only the executable and graph_replicates.csv checks are bypassed
    skipped = []
    def checked(path, expected):
        if Path(path).name == 'graph_replicates.csv': skipped.append(path); return
        production.checked(Path(path), expected)
    assemble.checked = checked
    assemble.verify_base = lambda d: (m, im)  # verify_plan() above made the same checks, executable excepted
    try:
        r = assemble.evaluate(run, ref['bootstrap']['replicates'])
    except Exception as exc:  # the delivered evaluate() refuses corrupt or mismatched records: report it and stop
        row('recombination by the delivered evaluate()', f'{type(exc).__name__}: {exc}', 'a result', False)
        return finish(a.out)
    row('evaluate() bypassed exactly 20 graph_replicates.csv checks', len(skipped), 20, len(skipped) == 20)
    compare_results(r, ref)

    # --- Section 1 and abstract; the paper's macro \CsevenTwo
    C, s = r['C7_full'], r['sampling_standard_error']
    halfdev = max(abs(h[7] - C) for h in r['half_streams'])
    allow = math.ceil(round(max(4 * s, halfdev), 9) * 10) / 10
    row('reported C7(2) (abstract, Sec. 1, eq. c7d2:reported; \\CsevenTwo)', f'{C:.1f} +- {allow:.1f}', '-3876.1 +- 2.1',
        f'{C:.1f}' == '-3876.1' and f'{allow:.1f}' == '2.1', 'allowance = max(4 SE, half-stream deviations) rounded up to 0.1')
    row('Sec. 1 estimator -3876.1260927949925 (record, exact)', repr(ref['C7_full']), '-3876.1260927949925',
        repr(ref['C7_full']) == '-3876.1260927949925')
    row('Sec. 1 estimator recomputed (headline tolerance 1e-12 |C7|)', f'{C:.13f}', '-3876.1260927949925',
        abs(C - ref['C7_full']) <= 1e-12 * abs(ref['C7_full']), f'delta {C - ref["C7_full"]:.1e}')
    quoted('Sec. 1 sampling SE', s, '0.5244496691')
    # --- Section 28.1 table and allowance
    quoted('power-free coefficient', r['power_free_C7'], '-3876.0700590'); quoted('its SE', r['power_free_se'], '0.5224502')
    quoted('power correction', r['power_correction'], '-0.0560338'); quoted('its SE', r['power_correction_se'], '0.0458637')
    quoted('complete coefficient', C, '-3876.1260928'); quoted('its SE', s, '0.5244497')
    quoted('4 sampling SE', 4 * s, '2.098')
    for j in (0, 1): quoted(f'half-stream deviation {j + 1}', abs(r['half_streams'][j][7] - C), '0.36')
    prev = load(PKG / 'reference/RESULT.json')
    row('previous calculation reported (reference/RESULT.json)', prev['reported'], 'C7(2) = -3950 +/- 310',
        prev['reported'] == 'C7(2) = -3950 +/- 310')
    quoted('previous estimator', prev['full_C7_2'], '-3953.6336215'); quoted('previous SE', prev['sampling_standard_error'], '76.7310362')
    quoted('new estimator from the previous one (previous SE)', (C - prev['full_C7_2']) / prev['sampling_standard_error'], '1.01')
    # --- Section 28.3: three-loop power jet against the analytic values
    mean3, se3 = campaign_mean_se(run, 'power', 3)
    row('three-loop jet means equal the assembled means.power.3', 'equal' if np.allclose(mean3, r['means']['power']['3'], rtol=1e-14, atol=0) else 'differ',
        'equal', np.allclose(mean3, r['means']['power']['3'], rtol=1e-14, atol=0))
    rad = load(PKG / 'reference/power_mass/verification/three_loop_radial_check.json')
    zref = rad['runs'][1]['b3_1']
    quoted('[z]b3p reference (tighter of two quadratures)', zref, '18.6743207750')
    quoted('difference of the two quadratures (1e-10)', 1e10 * abs(rad['runs'][0]['b3_1'] - rad['runs'][1]['b3_1']), '4.6')
    row('b3p(0) reference is -4 in both quadratures', [x['b3_0'] for x in rad['runs']], [-4.0, -4.0], all(x['b3_0'] == -4.0 for x in rad['runs']))
    quoted('production b3p(0)', mean3[0], '-3.99999979')
    quoted('its SE (note prints 0.00000043: erratum, note_changes.md)', se3[0], '0.00000042')
    quoted('production [z]b3p', mean3[1], '18.6743200'); quoted('its SE', se3[1], '0.0000021')
    quoted('pull of b3p(0) against -4', (mean3[0] + 4) / se3[0], '+0.50')
    quoted('pull of [z]b3p against the quadrature', (mean3[1] - zref) / se3[1], '-0.36')
    # --- Section 28.5: production design and campaigns
    cfgs = {g['name']: load(run / 'groups' / g['name'] / 'config.json') for g in m['groups']}
    ok = sorted(cfgs) == sorted(f'{t}_{s_}_L{L}' for t in 'ab' for s_ in ('free', 'power') for L in range(3, 8)) and all(c['replicates'] == 64 for c in cfgs.values())
    row('two campaigns x two sectors x loops 3-7, 64 replicates each', f"{len(cfgs)} groups, replicates {sorted({c['replicates'] for c in cfgs.values()})}", '20 groups, replicates [64]', ok)
    bits = {t: sorted({c['net']['bits'] for c in cfgs.values() if c['campaign'] == t}) for t in 'ab'}
    rate = {t: sorted({c['rate'] for c in cfgs.values() if c['campaign'] == t}) for t in 'ab'}
    row('digital-net bits a/b', f"{bits['a']}/{bits['b']}", '[52]/[60]', bits == {'a': [52], 'b': [60]})
    row('importance-rate multipliers a/b', f"{rate['a']}/{rate['b']}", "['.8']/['.9']", rate == {'a': ['.8'], 'b': ['.9']})
    counts = [n for c in cfgs.values() for n in c['counts'].values()]
    row('allocation multiplier 2^12; every stratum >= 4 x 2^12 points, a power of two', f"x{m['allocation_multiplier']}, min {min(counts)}",
        'x4096, min >= 16384', m['allocation_multiplier'] == 2 ** 12 and min(counts) >= 4 * 2 ** 12 and all(n & (n - 1) == 0 for n in counts))
    inv = load(PKG / 'inputs/inventory.json'); prim = [str(x['id']) for x in inv['free']['7'] if x['primitive']]
    pc = {cfgs[f'{t}_free_L7']['counts'][i] for t in 'ab' for i in prim}
    row('44 primitive classes, 2^26 points each per replicate', f'{len(prim)} classes, {sorted(pc)}', f'44 classes, [{2 ** 26}]', len(prim) == 44 and pc == {2 ** 26})
    row('kernel samples (sum over the 20 merged records)', f'{samples:,}', '1,094,688,178,176', samples == 1094688178176 == sum(c['samples'] for c in cfgs.values()))
    row('fixed campaign weights 1/2, recompute mode, no shared retained input',
        f"{m['campaign_weights']}, {r['primitive_mode']}, {r['shared_primitive']}", "{'a': 0.5, 'b': 0.5}, recompute, None",
        m['campaign_weights'] == {'a': .5, 'b': .5} and r['primitive_mode'] == 'recompute' and r['shared_primitive'] is None and r['shared_reference_se'] == 0)
    row('final tier 350-digit GMP (build pinned by the plan)', f"{m['build']['mp_backend']}", 'gmp350', m['build']['mp_backend'] == 'gmp350' and m['build']['mp_digits10'] == 350)
    for t, v, e in (('a', '-3875.3202', '0.7266'), ('b', '-3876.9320', '0.7565')):
        quoted(f'campaign {t}', r['campaigns'][t]['C7'], v); quoted(f'campaign {t} SE', r['campaigns'][t]['sampling_se'], e)
    quoted('first half stream', r['half_streams'][0][7], '-3876.4894'); quoted('second half stream', r['half_streams'][1][7], '-3875.7627')
    quoted('combined (table)', C, '-3876.1261'); quoted('combined SE (table)', s, '0.5244')
    ca, cb = r['campaigns']['a'], r['campaigns']['b']
    quoted('campaigns differ by (combined SE)', abs(pull(ca['C7'], ca['sampling_se'], cb['C7'], cb['sampling_se'])), '1.54')
    for sec, vals in (('free', ('0.0007', '0.0047', '0.0200', '0.0590', '0.5187')), ('power', ('0.0000', '0.0001', '0.0013', '0.0130', '0.0440'))):
        for L, v in zip(range(3, 8), vals): quoted(f'error by loop, {sec} L{L}', r['error_by_loop'][str(L)][sec], v)
    # --- Section 28.6: checks
    c6 = load(a.c6.resolve())
    refs = {3: (-0.8748500126526, 0.0), 4: (5.048868431355, 0.0), 5: (-38.83364589623, 0.0), 6: (c6['C6'], c6['sampling_standard_error'])}
    want = {3: ('-0.8748513621', '1.25', '-1.08'), 4: ('5.0488792961', '3.01', '+0.36'), 5: ('-38.8344913344', '5.07', '-1.67'),
            6: ('362.3727456', '0.0085778', '+0.73')}
    for k, (v, e, p) in want.items():
        est, se = r['coefficients'][k], r['standard_errors'][k]
        quoted(f'C{k} by-product', est, v)
        if k < 6: quoted(f'C{k} SE (units 1e-{6 if k == 3 else 5 if k == 4 else 4})', se * (1e6 if k == 3 else 1e5 if k == 4 else 1e4), e)
        else: quoted('C6 SE', se, e)
        quoted(f'C{k} pull' + (' (against the C6(2) production, both SEs)' if k == 6 else ' (against the 13-digit exact value)'),
               pull(est, se, *refs[k]), p)
    row('C6(2) reference read from results/C6_2/C6_result.json', f"{c6['C6']!r} +- {c6['sampling_standard_error']!r}",
        '362.36647176375726 +- 0.0007997306822612242', (c6['C6'], c6['sampling_standard_error']) == (362.36647176375726, 0.0007997306822612242))
    quoted('C6(2) section: by-product', r['coefficients'][6], '362.3727'); quoted('C6(2) section: its SE', r['standard_errors'][6], '0.0086')
    rec6 = [c for c in ref['lower_order_checks'] if c['order'] == 6][0]
    row("record's own lower_order_checks: C6 reference is the stale archived 362.3489 (no SE, no pull)", rec6['reference'],
        362.3489137997967, rec6['reference'] == 362.3489137997967 and 'pull' not in rec6,
        'documented in results/C7_2/README.md; the quoted pulls are the ones recomputed here')
    row('largest |pull| of C3-C6 <= \\PTlowerPullMax 2.3 (numbers.tex; set by the C7(3) run)',
        f"{max(abs(pull(r['coefficients'][k], r['standard_errors'][k], *refs[k])) for k in refs):.2f}", '<= 2.3',
        max(abs(pull(r['coefficients'][k], r['standard_errors'][k], *refs[k])) for k in refs) <= 2.3)
    pd, pe = r['power_differences'], r['power_difference_errors']
    row('power difference at order 3 at the rounding level', f'{pd[3]:.1e}', '|x| < 1e-12', abs(pd[3]) < 1e-12)
    for k, sc, v, e in ((4, 1e8, '5.4', '15.1'), (5, 1e5, '1.10', '1.85'), (6, 1e4, '3.3', '11.8')):
        quoted(f'power difference order {k} (x1e{int(math.log10(sc))})', pd[k] * sc, v); quoted(f'  its SE', pe[k] * sc, e)
    quoted('seventh-order power correction', pd[7], '-0.056'); quoted('  its SE', pe[7], '0.046')
    quoted('bootstrap SE (4,096 resamples)', r['bootstrap']['full_se'][7], '0.52219')
    row('bootstrap resamples and seed', f"{r['bootstrap']['replicates']}, {r['bootstrap']['seed']}", '4096, 70530413',
        (r['bootstrap']['replicates'], r['bootstrap']['seed']) == (4096, 70530413))
    quoted('covariance-propagation SE (comparison)', s, '0.52445')
    quoted('previous power correction', prev['power_correction'], '1.750131'); quoted('  its SE', prev['power_correction_sampling_se'], '5.424390')
    quoted('new power correction from the previous one (previous SE)', (r['power_correction'] - prev['power_correction']) / prev['power_correction_sampling_se'], '-0.33')
    # --- Section 28.2: coverage, from the records of the method (reference/)
    cov = load(PKG / 'reference/power_mass/verification/full_graph_coverage.json')
    tab = [(x['loop'], x['classes'], x['power_classes'], x['new_nonzero_kernels'], x['new_sampled_classes']) for x in cov['loops']]
    want_tab = [(3, 8, 1, 1, 1), (4, 27, 5, 3, 3), (5, 129, 31, 20, 20), (6, 660, 173, 107, 107), (7, 3986, 1091, 709, 590)]
    row('coverage table (classes, power-containing, nonzero mixed kernels, integrated power) L3-L7', tab, want_tab, cov['status'] == 'passed' and tab == want_tab)
    part = cov['seventh_order_partition']
    want_part = dict(zero_channel_weight=459, zero_mixed_forest_kernel_at_nonzero_weight=639, retained_primitive=44,
                     retained_powerfree_nonprimitive=2254, new_power_containing=590)
    row('seven-loop partition: zero weight + zero map + primitive + power-free + power = 3986', list(part.values()), list(want_part.values()),
        part == want_part and sum(part.values()) == 3986)
    cnt = im['counts']
    row('integrated classes per loop (inputs/manifest.json): power-free L3-L7, power L3-L7',
        [cnt['free'][str(L)] for L in range(3, 8)] + [cnt['power'][str(L)] for L in range(3, 8)],
        [5, 16, 76, 395, 2298, 1, 3, 20, 107, 590],
        [cnt['free'][str(L)] for L in range(3, 8)] + [cnt['power'][str(L)] for L in range(3, 8)] == [5, 16, 76, 395, 2298, 1, 3, 20, 107, 590])
    ef = [load(PKG / f'reference/power_mass/verification/edge_forests_L{L}.json') for L in range(3, 8)]
    n_ef = sum(x['graphs'] for x in ef); f_ef = sum(x['failures'] for x in ef)
    row('edge-subgraph forest maps agree for all power-containing classes L3-L7', f'{n_ef} classes, {f_ef} failures', '1301 classes, 0 failures',
        n_ef == 1301 and f_ef == 0 and all(rr['matches_induced'] for x in ef for rr in x['rows']))
    kc = load(PKG / 'reference/power_mass/verification/kirchhoff_checks.json')
    row('rational Kirchhoff-determinant check: configurations, all exact, endpoint-scaled included',
        f"{kc['count']}, {all(c['exact_match'] for c in kc['checks'])}, {any(c['endpoint_scaled'] for c in kc['checks'])}", '66, True, True',
        kc['status'] == 'passed' and kc['count'] == 66 == len(kc['checks']) and all(c['exact_match'] for c in kc['checks']) and any(c['endpoint_scaled'] for c in kc['checks']))
    ac = load(PKG / 'reference/power_mass/verification/assembly_checks.json')
    row('Lagrange extraction: exact regulator-dependent cases, MS seventh-order cases', f"{ac['exact_regulator_dependent_cases']}, {ac['exact_constant_MS_cases']}", '24, 24',
        ac['status'] == 'passed' and ac['exact_regulator_dependent_cases'] == 24 == ac['exact_constant_MS_cases'])
    # --- Section 28.5: native checks on the production host (results/C7_2/evidence)
    ev = res / 'evidence'
    fv = load(ev / 'buildtest-566254/full_validation.json'); mt = [t for t in fv['tests'] if t['test'].startswith('matched')]
    ok = (fv['status'] == 'passed' and fv['total_graphs'] == 3511 and sum(t['graphs'] for t in mt) == 3511
          and all(t['max_normalized_difference'] == {'decimal': '0', 'gmp': '0'} and t['fallbacks_match'] for t in mt))
    row('both backends reproduce the original executable at all graph kernels (job 566254)', f"{fv['total_graphs']} kernels, max difference 0" if ok else 'mismatch',
        '3511 kernels, max difference 0, identical promotions', ok)
    cp = [json.loads(x) for x in (ev / 'buildtest-566254/check_points.log').read_text().split('\n') if x.strip()]
    row('independent high-precision point checks, both backends', [f"{c['backend']}: {c['status']}" for c in cp], ['decimal300: passed', 'gmp350: passed'],
        sorted(c['backend'] for c in cp) == ['decimal300', 'gmp350'] and all(c['status'] == 'passed' for c in cp))
    mtc = re.search(r'THREADCHECK rows=(\d+) mismatches=(\d+) quad=(\d+) mp=(\d+)', (ev / 'buildtest-566254.out').read_text())
    row('seven-loop rows identical at 64 and 16 threads, GMP promotions', f'{mtc[1]} rows, {mtc[2]} mismatches, {mtc[4]} promotions',
        '5776 rows, 0 mismatches, 31663 promotions', (mtc[1], mtc[2], mtc[4]) == ('5776', '0', '31663'))
    # --- the previous calculation, re-assembled by the package's own tool from the archived records in reference/
    if a.skip_reference:
        skip('tools/reassemble_reference.py (previous calculation)', '--skip-reference given')
    else:
        env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'OPENBLAS_NUM_THREADS': '1'}
        pr = subprocess.run([sys.executable, '-B', 'tools/reassemble_reference.py'], cwd=PKG, capture_output=True, text=True, env=env)
        try: out = json.loads(pr.stdout)
        except ValueError: out = {}
        row('tools/reassemble_reference.py (fb64c47): previous result reproduced from reference/ records (its own gate 2e-8)',
            out.get('status', f'exit {pr.returncode}'), 'passed', pr.returncode == 0 and out.get('status') == 'passed',
            f"max abs error {out.get('max_absolute_error', float('nan')):.1e}" if out else pr.stderr[-300:])
        if out:
            quoted('  previous estimator, re-assembled', out['result']['C7_full'], '-3953.6336215')
            quoted('  previous SE, re-assembled', out['result']['sampling_standard_error'], '76.7310362')
            quoted('  previous power correction, re-assembled', out['result']['power_correction'], '1.750131')
            quoted('  its SE, re-assembled', out['result']['power_correction_se'], '5.424390')

    return finish(a.out)


def finish(out):
    out.mkdir(parents=True, exist_ok=True)
    (out / 'replay.json').write_text(json.dumps(dict(numpy=np.__version__, python=sys.version.split()[0], rows=ROWS), indent=1, default=str) + '\n')
    w = max(len(x['check']) for x in ROWS)
    for x in ROWS: print(f"{x['status']:4}  {x['check']:<{w}}  {x['got']!s:>22}  (expected {x['expected']})" + (f"  {x['note']}" if x['note'] else ''))
    fails = sum(x['status'] == 'FAIL' for x in ROWS); skips = sum(x['status'] == 'SKIP' for x in ROWS)
    print(f'\n{len(ROWS) - fails - skips} PASS, {fails} FAIL, {skips} SKIP (numpy {np.__version__}, Python {sys.version.split()[0]})')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
