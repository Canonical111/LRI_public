#!/usr/bin/env python3
"""Replay every published C6(3) number from the shipped merged production records.

Public-release overlay (2026-10-13), not part of the production commit 1c6dfb3. It recomputes, with the package's own
code (tools/production.py for the record checks, tools/assemble.py for the estimator), every number that the condensed
note quotes for C6(3) (Section 1, Section "The three-dimensional production of September 2026" and the result, error
budget and final-check tables after it) and that CAMPAIGN.md states, and compares each with the quoted value.

Inputs (read only):
  --results   the production results folder: manifest.json, groups/<c>_L<L>/{config.json,merged.json,
              graph_replicates.csv} and C6_result.json (default ../../results/C6_3/results_run-20260929-m8192);
              the full run directory from the hosted tarball also works (its tasks.sqlite files are then checked too)
  reference/  the archived refinement and baseline records (a link to ../LRI_C6_D2_HPC/reference in the public layout)
  --c7-result optional C7(3) result whose sixth-order by-product is the note's independent comparison
Outputs: a PASS/FAIL table on stdout and in OUT/REPLAY_C6_3.md, the recomputed result in OUT/C6_result_replayed.json.
Exit status 1 if any row fails. Runtime about 10-30 s on one core (the 4096-draw bootstrap dominates).

With --remerge (full run directory only) the merged records are first rebuilt from the checkpoints with
`tools/production.py merge` in a scratch copy, and their SHA-256 must equal the production ones.
"""
from __future__ import annotations
import os
for _v in ('OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'OMP_NUM_THREADS'):  # as slurm/merge.sh: deterministic BLAS reductions
    os.environ.setdefault(_v, '1')
import argparse, decimal, json, math, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))
import numpy as np
import production
import assemble
from common import canon, checked, digest, load, object_hash
from prepare_inputs import PIDS

D = decimal.Decimal
ROWS: list[dict] = []
REL_FLOAT = 1e-12   # estimator and SE: float64 assembly, CPU/BLAS-dependent last bits (1 ulp measured on Apple arm64)
REL_RECORD = 1e-9   # every other float of C6_result.json (covariances, jets, bootstrap): same reason, smaller entries
ABS_RECORD = 1e-20
# Differences of two O(30) numbers: their rounding is absolute (about 1e-14), so they get an absolute tolerance.
ABS_FIELD = {'.bootstrap.mean_minus_estimate': 1e-12}


def row(group, what, quoted, replayed, ok, tol, source):
    status = ok if isinstance(ok, str) else ('PASS' if ok else 'FAIL')
    ROWS.append(dict(group=group, what=what, quoted=str(quoted), replayed=str(replayed), tol=tol, status=status, source=source))


def rounded(x, places):
    """Decimal rounding half-up of a float's shortest repr (how the quoted digits were written)."""
    return D(repr(float(x))).quantize(D(1).scaleb(-places), rounding=decimal.ROUND_HALF_UP)


def sig(x, n):
    return float(f'{x:.{n}g}')


def compare(a, b, path='', worst=None):
    """Compare two JSON trees: strings, ints, bools, None exactly; floats to REL_RECORD (ABS_RECORD floor)."""
    worst = worst if worst is not None else {'rel': 0.0, 'bad': []}
    if isinstance(b, dict):
        if not isinstance(a, dict) or set(a) != set(b):
            worst['bad'].append(f'{path}: keys differ')
            return worst
        for k in b:
            compare(a[k], b[k], f'{path}.{k}', worst)
    elif isinstance(b, list):
        if not isinstance(a, list) or len(a) != len(b):
            worst['bad'].append(f'{path}: length differs')
            return worst
        for i, (x, y) in enumerate(zip(a, b)):
            compare(x, y, f'{path}[{i}]', worst)
    elif isinstance(b, float) or (isinstance(a, float) and isinstance(b, int) and not isinstance(b, bool)):
        if not isinstance(a, (int, float)) or isinstance(a, bool):
            worst['bad'].append(f'{path}: type differs')
            return worst
        d = abs(a - b)
        if d > max(REL_RECORD * abs(b), ABS_FIELD.get(path, ABS_RECORD)):
            worst['bad'].append(f'{path}: {a!r} vs {b!r}')
        if b and path not in ABS_FIELD:
            worst['rel'] = max(worst['rel'], d / abs(b))
    elif a != b:
        worst['bad'].append(f'{path}: {a!r} vs {b!r}')
    return worst


def remerge(full: Path, work: Path) -> Path:
    """Rebuild every merged.json and graph_replicates.csv from the checkpoints in a scratch copy (package merge code)."""
    copy = work / 'remerge' / full.name
    if copy.exists():
        shutil.rmtree(copy)
    shutil.copytree(full, copy)
    for p in (copy / 'groups').iterdir():
        for name in ('merged.json', 'graph_replicates.csv'):
            if (p / name).exists():
                (p / name).unlink()
    if (copy / 'C6_result.json').exists():
        (copy / 'C6_result.json').unlink()
    t0 = time.time()
    cp = subprocess.run([sys.executable, '-B', str(ROOT / 'tools/production.py'), 'merge', str(copy)], capture_output=True, text=True)
    if cp.returncode:
        raise RuntimeError('production.py merge failed:\n' + cp.stderr[-3000:])
    for g in sorted((full / 'groups').iterdir()):
        a, b = digest(g / 'merged.json'), digest(copy / 'groups' / g.name / 'merged.json')
        c, d = digest(g / 'graph_replicates.csv'), digest(copy / 'groups' / g.name / 'graph_replicates.csv')
        row('A records', f'{g.name}: merged.json and graph_replicates.csv rebuilt from the checkpoints', a[:16], b[:16], a == b and c == d,
            'sha256 equal', 'tools/production.py merge (scratch copy)')
    print(f'remerge: {time.time() - t0:.0f} s', flush=True)
    return copy


def load_records(directory: Path, result: dict):
    """assemble.load_campaign, step by step, with tasks.sqlite checked only when present (not in the merged-record set)."""
    m, im, mh = production.verify_base(directory, check_executable=False)   # tool and inputs hashes bound by the plan
    row('A records', 'tools/{production,assemble,common,prepare_inputs}.py and inputs/manifest.json = the hashes in manifest.json',
        'bound', 'equal', True, 'sha256 equal', 'production.verify_base')
    ar = {t: {} for t in m['campaign_weights']}
    configs, merged, tasks = {}, {}, []
    for gr in m['groups']:
        p = directory / 'groups' / gr['name']
        cfg = production.read_verified(p / 'config.json', gr['sha256'])
        if (p / 'tasks.sqlite').exists():
            checked(p / 'tasks.sqlite', cfg['tasks_sha256'])
            tasks.append(gr['name'])
        d = production.validate_merged(p, cfg, m, mh)    # schema, complete, plan and config hash, payload hash, CSV hash
        a = np.array(d['batches'], float)
        if a.shape != (cfg['replicates'], 2 * (7 - cfg['L'])) or not np.isfinite(a).all():
            raise ValueError('invalid replicate array ' + gr['name'])
        ar[cfg['campaign']][cfg['L']] = a
        configs[gr['name']], merged[gr['name']] = cfg, d
    bound = all(digest(directory / 'groups' / n / 'merged.json') == h for n, h in result['merged_sha256'].items())
    row('A records', '8 groups: config.json = manifest hash; merged.json schema, plan hash, config hash, payload hash, CSV hash',
        '8 valid', f'{len(merged)} valid', len(merged) == 8, 'exact', 'production.read_verified, validate_merged')
    row('A records', 'merged.json sha256 = C6_result.json merged_sha256; manifest sha256 = source_manifest_sha256',
        'bound', 'equal' if bound and result['source_manifest_sha256'] == mh else 'differs',
        bound and result['source_manifest_sha256'] == mh, 'sha256 equal', 'C6_result.json')
    row('A records', 'tasks.sqlite = config tasks_sha256 (full run directory only)', 'bound',
        f'{len(tasks)} checked' if tasks else 'not in the merged-record set', len(tasks) == 8 if tasks else 'SKIP', 'sha256 equal',
        'hosted run-20260929-m8192_full.tgz')
    if len(tasks) == 8:   # the package's own entry point works on the full run directory
        m2, mh2, ar2, ih2 = assemble.load_campaign(directory)
        row('A records', 'assemble.load_campaign accepts the full run directory', 'accepted', 'accepted', mh2 == mh, 'exact', 'tools/assemble.py')
    return m, mh, ar, configs, merged


def design_checks(m, configs, merged):
    inv = load(ROOT / 'inputs/inventory.json')
    counts = [len(inv[str(L)]) for L in range(3, 7)]
    row('B design', 'nonzero kernel classes at L = 3, 4, 5, 6', '5, 16, 76, 395', ', '.join(map(str, counts)), counts == [5, 16, 76, 395],
        'exact', 'inputs/inventory.json')
    six = {r['id'] for r in inv['6']}
    prim_ok = len(PIDS) == 10 and PIDS <= six and all(configs[f'{c}_L6']['counts'][str(g)] > 0 for c in 'ab' for g in PIDS)
    row('B design', 'the ten primitive six-loop kernels are integrated in both campaigns', '10 included', f'{len(PIDS)} included',
        prim_ok, 'exact', 'groups/*_L6/config.json')
    mult = m['allocation']['multiplier']
    alloc_ok, zero = True, 0
    for name, cfg in configs.items():
        frozen = load(ROOT / f'inputs/counts_L{cfg["L"]}.json')
        frozen = frozen.get('counts', frozen)
        for r in inv[str(cfg['L'])]:
            f = int(frozen.get(str(r['id']), 0))
            zero += (f == 0 and cfg['campaign'] == 'a')
            alloc_ok &= cfg['counts'][str(r['id'])] == max(4, f) * mult
    row('B design', 'every stratum = frozen refinement allocation x 2^13 (zero targets raised to 4)', '2^13 = 8192',
        f'{mult}; {zero} zero targets', alloc_ok and mult == 8192, 'exact', 'config.json vs inputs/counts_L*.json')
    per_rep = [sum(configs[f'a_L{L}']['counts'].values()) for L in range(3, 7)]
    same = all(configs[f'a_L{L}']['counts'] == configs[f'b_L{L}']['counts'] for L in range(3, 7))
    quoted = [1241513984, 2499805184, 9743368192, 35891576832]
    row('B design', 'points per replicate at L = 3, 4, 5, 6 (both campaigns)', ', '.join(f'{q:,}' for q in quoted),
        ', '.join(f'{q:,}' for q in per_rep), per_rep == quoted and same, 'exact', 'config.json counts')
    total = sum(c['samples'] for c in configs.values())
    row('B design', 'kernel samples in the two campaigns', '6,320,161,816,576', f'{total:,}', total == 6320161816576, 'exact', 'config.json samples')
    flags = all(c['replicates'] == 64 and c['seed_scheme'] == 'hashed' and c['layout'] == 0 and D(c['rate']) == 1 and c['grid'] is None
                and c['sum_mode'] == 'compensated' and c['primitive_mode'] == 'recompute' for c in configs.values())
    bits = {c['campaign']: c['net']['bits'] for c in configs.values()}
    reps = sorted({c['replicates'] for c in configs.values()})
    row('B design', '64 replicates per loop and campaign; hashed seeds; layout 0, rate 1, no grid, compensated sums; bits a/b',
        '64; 52/60', f"{'/'.join(map(str, reps))}; {bits['a']}/{bits['b']}", flags and bits == {'a': 52, 'b': 60}, 'exact', 'config.json')
    row('B design', 'frozen campaign weights', '1/2, 1/2', str(m['campaign_weights']), m['campaign_weights'] == {'a': 0.5, 'b': 0.5}, 'exact', 'manifest.json')
    jobs, thr = len(m['jobs']), m['threads']
    row('B design', 'independent array elements x threads', '458 x 64', f'{jobs} x {thr}', jobs == 458 and thr == 64, 'exact', 'manifest.json')
    est = m['estimates']
    proj = est['projected_C6_sampling_se']
    proj_s = 'none (point override)' if proj is None else f'{proj:.2g}'
    row('B design', 'planned cost and projected SE (CAMPAIGN.md)', '9,653 core-h; 0.00022',
        f"{est['total_core_hours']:,.0f} core-h; {proj_s}",
        round(est['total_core_hours']) == 9653 and proj_s == '0.00022', 'rounded', 'manifest.json estimates')
    src = (ROOT / 'src/kernel.hpp').read_text()
    thr_ok = src.count('ratio<1e-9L') == 2 and src.count('Q(1e-23L)') == 2
    row('B design', 'binary128 and 300-digit fallback thresholds in the worker', '1e-9, 1e-23', 'found' if thr_ok else 'not found',
        thr_ok, 'text', 'src/kernel.hpp')
    fb = {k: sum(d['fallbacks'][k] for d in merged.values()) for k in ('quad', 'mp')}
    row('B design', 'binary128 / 300-digit promotions in production (information)', '-', f"{fb['quad']:,} / {fb['mp']}", 'INFO', '-',
        'merged.json fallbacks')


def evaluate(directory: Path, bootstrap: int) -> dict:
    """assemble.evaluate, the package's own assembly entry point (slurm/merge.sh runs it with --bootstrap 4096).

    The merged-record set does not contain the task databases (tasks.sqlite, in the hosted tarball). Only for this call,
    production.group_of is replaced by a copy that checks tasks.sqlite when it is present and skips it otherwise; every
    other check of load_campaign (plan, tool and input hashes, config hashes, merged payload and CSV hashes) is unchanged.
    """
    original = production.group_of
    def group_of(d, m, name):
        p = d / 'groups' / name
        config = production.read_verified(p / 'config.json', next(g['sha256'] for g in m['groups'] if g['name'] == name))
        if (p / 'tasks.sqlite').exists():
            checked(p / 'tasks.sqlite', config['tasks_sha256'])
        return p, config
    production.group_of = group_of
    try:
        return assemble.evaluate(directory, bootstrap)
    finally:
        production.group_of = original


def estimator_checks(m, directory, result, configs):
    t0 = time.time()
    res = evaluate(directory, result['bootstrap']['replicates'])
    secs = time.time() - t0
    C, S = res['C6'], res['sampling_standard_error']
    row('C estimator', 'C6(3) estimator (note Sec. 1)', '33.57542664131543', repr(C),
        abs(C - 33.57542664131543) <= REL_FLOAT * 33.58, f'rel {REL_FLOAT:g}', 'assemble.combine on merged.json')
    row('C estimator', 'sampling standard error (note Sec. 1)', '0.0001185495235', repr(S), abs(S - 0.0001185495235) <= 5e-14, 'printed 10 digits',
        'assemble.combine')
    # A lower-order pull (estimate - reference) / SE divides the float64 rounding of the estimate (rel REL_FLOAT, as for
    # C6 above) by an SE far below the estimate (C3: |C3| / SE = 1.3e7), so its last digits move with the CPU's BLAS
    # kernels (5e-9 relative on an Intel Xeon 6148 against the AMD production). Its tolerance is that rounding over SE.
    for i, lo in enumerate(result['lower_order_checks']):
        ABS_FIELD[f'.lower_order_checks[{i}].pull'] = REL_FLOAT * abs(lo['estimate']) / lo['sampling_se']
    w = compare(json.loads(json.dumps(res, allow_nan=False)), result)
    bit = canon(json.loads(json.dumps(res, allow_nan=False))) == canon(result)
    row('C estimator', 'every field of C6_result.json recomputed', 'C6_result.json',
        'bitwise identical' if bit else f'max rel dev {w["rel"]:.1e}' + (f'; {w["bad"][:3]}' if w['bad'] else ''), not w['bad'],
        f'rel {REL_RECORD:g} (bootstrap mean shift: abs 1e-12; pulls: rel {REL_FLOAT:g} of the estimate / SE)', f'assemble.evaluate, bootstrap 4096 ({secs:.0f} s)')
    for t, cq, sq in (('a', '33.57562307', '0.00015062'), ('b', '33.57523021', '0.00018311')):
        c = res['campaigns'][t]
        row('C estimator', f'campaign {t}: C6(3) and SE', f'{cq} +- {sq}', f"{rounded(c['C6'], 8)} +- {rounded(c['sampling_se'], 8)}",
            str(rounded(c['C6'], 8)) == cq and str(rounded(c['sampling_se'], 8)) == sq, 'printed digits', 'C6_result.json campaigns')
    row('C estimator', 'combined (note table)', '33.57542664 +- 0.00011855', f'{rounded(C, 8)} +- {rounded(S, 8)}',
        str(rounded(C, 8)) == '33.57542664' and str(rounded(S, 8)) == '0.00011855', 'printed digits', '')
    eb = res['error_by_loop']
    q = ['0.000001', '0.000021', '0.000058', '0.000101']
    got = [str(rounded(eb[str(L)], 6)) for L in range(3, 7)]
    row('C estimator', 'error budget L3, L4, L5, L6, common, total', ', '.join(q) + ', 0.000000, 0.000119',
        ', '.join(got) + f", {rounded(res['shared_reference_standard_error'], 6)}, {rounded(S, 6)}",
        got == q and res['shared_reference_standard_error'] == 0 and str(rounded(S, 6)) == '0.000119', 'printed digits', 'error_by_loop')
    row('C estimator', 'CAMPAIGN.md error by loop', 'L3 1.1e-6, L4 2.1e-5, L5 5.8e-5, L6 1.0e-4',
        ', '.join(f'L{L} {sig(eb[str(L)], 2):.1e}' for L in range(3, 7)),
        [f'{sig(eb[str(L)], 2):.1e}' for L in range(3, 7)] == ['1.1e-06', '2.1e-05', '5.8e-05', '1.0e-04'], '2 significant digits', 'error_by_loop')
    co = res['coefficients']
    row('C estimator', 'C0, C1, C2 (exact inputs, note Sec. 1 table)', '3/2, -1/6, 0.181221785406',
        f'{co[0]!r}, {co[1]!r}, {rounded(co[2], 12)}', co[0] == 1.5 and abs(co[1] + 1 / 6) < 1e-15 and str(rounded(co[2], 12)) == '0.181221785406',
        'exact (C1 to 1e-15) / 12 decimals', 'coefficients')
    cam = [('-0.3535815650', '2.6e-8'), ('1.2280621550', '1.3e-6'), ('-5.8503379659', '1.5e-5')]
    for (vq, sq), lo in zip(cam, res['lower_order_checks']):
        n = lo['order']
        row('C estimator', f'C{n}(3) estimate and SE (CAMPAIGN.md table)', f'{vq} (SE {sq})',
            f"{rounded(lo['estimate'], 10)} (SE {sig(lo['sampling_se'], 2):.1e})",
            str(rounded(lo['estimate'], 10)) == vq and f"{sig(lo['sampling_se'], 2):.1e}".replace('e-0', 'e-') == sq, 'printed digits',
            'coefficients, standard_errors')
    bs = res['bootstrap']
    row('C estimator', 'bootstrap SE (4096 resamples) and mean minus estimate', '0.00011534; +2.1e-8',
        f"{rounded(bs['sampling_se'], 8)}; {sig(bs['mean_minus_estimate'], 2):+.1e}",
        str(rounded(bs['sampling_se'], 8)) == '0.00011534' and f"{sig(bs['mean_minus_estimate'], 2):+.1e}" == '+2.1e-08' and bs['replicates'] == 4096,
        'printed digits', 'combine bootstrap (seed 82491001)')
    return res


def rule_and_gates(res, prev, fresh):
    C, S = res['C6'], res['sampling_standard_error']
    four = D(repr(4 * S))
    a1 = (four / D('0.0001')).to_integral_value(rounding=decimal.ROUND_CEILING) * D('0.0001')
    reg = (four / D('0.001')).to_integral_value(rounding=decimal.ROUND_CEILING) * D('0.001')
    row('D rule', '4 x SE', '0.00047', f'{sig(4 * S, 2)}', f'{sig(4 * S, 2)}' == '0.00047', '2 significant digits', 'CAMPAIGN.md rule 2')
    row('D rule', 'allowance, Amendment 1: 4 x SE rounded up to a multiple of 0.0001', '0.0005', str(a1), a1 == D('0.0005'), 'exact', 'CAMPAIGN.md Amendment 1')
    row('D rule', 'allowance under the rule as registered (step 0.001), superseded', '0.001', str(reg), reg == D('0.001'), 'exact', 'CAMPAIGN.md rule 2')
    row('D rule', 'reported value C6(3) = 33.5754 +- 0.0005 (note Sec. 1, eq. meth:reported)', '33.5754 +- 0.0005', f'{rounded(C, 4)} +- {a1}',
        str(rounded(C, 4)) == '33.5754' and a1 == D('0.0005'), 'exact', '')
    ca, cb = res['campaigns']['a'], res['campaigns']['b']
    pull = abs(ca['C6'] - cb['C6']) / math.hypot(ca['sampling_se'], cb['sampling_se'])
    row('E gates', 'a/b campaigns: |a - b| / combined SE <= 3', '1.66', f'{pull:.2f}', f'{pull:.2f}' == '1.66' and pull <= 3, 'printed; gate 3', 'CAMPAIGN.md gate 1')
    ratio = res['bootstrap']['sampling_se'] / S
    row('E gates', 'bootstrap SE / covariance SE within +-20%', '0.973', f'{ratio:.3f}', f'{ratio:.3f}' == '0.973' and 0.8 <= ratio <= 1.2,
        'printed; gate 0.8-1.2', 'CAMPAIGN.md gate 2')
    pp = (C - prev['C6']) / prev['sampling_standard_error']
    pc = (D('33.5754') - D('33.5682')) / D('0.0242')
    row('E gates', 'previous estimator: (C6 - 33.5681968) / 0.0241840 <= 3 (note); (33.5754 - 33.5682) / 0.0242 (CAMPAIGN.md)', '0.30; +0.0072 = 0.30',
        f'{pp:.2f}; {D("33.5754") - D("33.5682"):+} = {pc:.2f}', f'{pp:.2f}' == '0.30' and f'{pc:.2f}' == '0.30' and pp <= 3,
        'printed; gate 3', 'recomputed previous estimator (group G)')
    for lo, q in zip(res['lower_order_checks'], ('-1.69', '-1.09', '+0.92')):
        row('E gates', f"C{lo['order']}(3) pull against the special-function value, |pull| <= 4", q, f"{lo['pull']:+.2f}",
            f"{lo['pull']:+.2f}" == q and abs(lo['pull']) <= 4, 'printed; gate 4', 'lower_order_checks (assemble.REFERENCE_LOWER)')
    row('E gates', 'reference constants C3..C5 equal the note Sec. 1 values', '-0.353581520433, 1.228063545, -5.850351421',
        f'{rounded(assemble.REFERENCE_LOWER[0], 12)}, {rounded(assemble.REFERENCE_LOWER[1], 9)}, {rounded(assemble.REFERENCE_LOWER[2], 9)}',
        str(rounded(assemble.REFERENCE_LOWER[0], 12)) == '-0.353581520433' and str(rounded(assemble.REFERENCE_LOWER[1], 9)) == '1.228063545'
        and str(rounded(assemble.REFERENCE_LOWER[2], 9)) == '-5.850351421', 'printed digits', 'tools/assemble.py REFERENCE_LOWER')
    return pull


def precision_checks(res, m, prev, fresh):
    S, C = res['sampling_standard_error'], res['C6']
    proj = m['estimates']['projected_C6_sampling_se']
    ratio = 'none' if proj is None else f'{S / proj:.2f}'
    row('F precision', 'SE / plain-MC projection 0.00022 (note; CAMPAIGN.md erratum)', '0.54', ratio, ratio == '0.54', 'printed',
        'manifest.json projected_C6_sampling_se')
    row('F precision', 'previous SE / SE (CAMPAIGN.md: "204x below the archived 0.0242")', '204', f'{prev["sampling_standard_error"] / S:.0f}',
        f'{prev["sampling_standard_error"] / S:.0f}' == '204', 'printed', 'group G')
    r = (C - fresh['C6']) / fresh['sampling_standard_error']
    row('F precision', '(C6 - refinement-only) / refinement SE', '0.52', f'{r:.2f}', f'{r:.2f}' == '0.52', 'printed', 'group G')


def superseded_checks(m):
    """The previous estimators, recomputed with assemble.combine from the archived records (as tests/archived_assembly.py)."""
    from archived_assembly import arrays, FRESH, PREVIOUS
    vi = assemble.verified_inputs(m['inputs_manifest_sha256'])
    exp = load(ROOT / 'reference/verification/method_precision_results.json')['3']
    new = {'a': arrays(FRESH, 'new_a'), 'b': arrays(FRESH, 'new_b')}
    old = {'a': arrays(PREVIOUS, 'prod_a'), 'b': arrays(PREVIOUS, 'prod_b')}
    fresh = assemble.combine(new, {'a': .5, 'b': .5}, vi['B2'], bootstrap=0)
    base = assemble.combine(old, {'a': .5, 'b': .5}, vi['B2'], bootstrap=0)
    allfour = {'new_a': new['a'], 'new_b': new['b'], 'prod_a': old['a'], 'prod_b': old['b']}   # order of tests/archived_assembly.py
    four = assemble.combine(allfour, {t: .25 for t in allfour}, vi['B2'], bootstrap=0)
    def rec(name, r, e, cq, sq, places):
        """r: recomputed (combine result or campaign entry); e: the archived record; cq, sq: the note's printed digits."""
        sr = r.get('sampling_standard_error', r.get('sampling_se'))
        ok = math.isclose(r['C6'], e['C6'], rel_tol=REL_FLOAT) and math.isclose(sr, e['sampling_standard_error'], rel_tol=REL_FLOAT)
        row('G superseded', name, f'{cq} +- {sq}', f'{rounded(r["C6"], places)} +- {rounded(sr, len(sq) - 2)}',
            ok and str(rounded(r['C6'], places)) == cq and str(rounded(sr, len(sq) - 2)) == sq,
            f'rel {REL_FLOAT:g} vs record; printed digits', 'reference/records, method_precision_results.json')
    rec('refinement-only estimate (refinement A+B, 1/2 each)', fresh, exp['fresh_only'], '33.56084035', '0.028119', 8)
    rec('refinement campaign A', fresh['campaigns']['a'], exp['fresh_campaigns']['new_a'], '33.59417512', '0.040029', 8)
    rec('refinement campaign B', fresh['campaigns']['b'], exp['fresh_campaigns']['new_b'], '33.52750475', '0.039502', 8)
    rec('previous estimator (four campaigns, 1/4 each)', four, exp, '33.5681968', '0.0241840', 7)
    for t, cq, sq in (('a', '33.590772', '0.057948'), ('b', '33.560344', '0.053265')):
        c = base['campaigns'][t]
        row('G superseded', f'baseline campaign {t.upper()}', f'{cq} +- {sq}', f"{rounded(c['C6'], 6)} +- {rounded(c['sampling_se'], 6)}",
            str(rounded(c['C6'], 6)) == cq and str(rounded(c['sampling_se'], 6)) == sq, 'printed digits', 'reference/baseline_previous/records')
    samples = 0
    for t in ('new_a', 'new_b'):
        for L in range(3, 7):
            r = load(ROOT / f'reference/records/{t}_d3_L{L}.json')
            samples += int(r['replicates']) * sum(int(c) for c in r['counts_per_replicate'])
    rep = load(ROOT / 'benchmarks/expanse_2026-09/logs/validation_54510646/archived_stream_replay.json')
    fb_ok = all(s['quad'][0] == s['quad'][1] and s['mp'][0] == s['mp'][1] for s in rep['streams']) and len(rep['streams']) == 8
    row('G superseded', 'cited archived-stream replay (Expanse job 54510646): status, samples, fallbacks, C6 bit for bit', 'passed; 385,744,896; equal; true',
        f"{rep['status']}; {rep['samples_total']:,}; {'equal' if fb_ok else 'differ'}; {rep['C6_bitwise_identical']}",
        rep['status'] == 'passed' and rep['samples_total'] == 385744896 == samples and fb_ok and rep['C6_bitwise_identical'] is True,
        'exact', 'benchmarks/expanse_2026-09/logs/validation_54510646/archived_stream_replay.json')
    row('G superseded', 'replayed refinement-only C6 = the value recomputed here from the archived records', repr(fresh['C6']),
        repr(rep['replayed_fresh_only_C6']), math.isclose(rep['replayed_fresh_only_C6'], fresh['C6'], rel_tol=1e-13),
        'rel 1e-13 (the replay test tolerance)', 'same record')
    x = load(ROOT / 'reference/verification/extra_checks.json')['3']
    lag, bias = x['max_Lagrange_difference'], max(abs(v) for v in x['nonlinear_jackknife_bias'])
    row('G superseded', 'previous estimator: Lagrange expansion vs fixed point; delete-one bias (read, not recomputed)', '5e-14; below 6.5e-8',
        f'{lag:.1e}; {bias:.2e}', f'{sig(lag, 1):.0e}' == '5e-14' and bias < 6.5e-8, 'printed', 'reference/verification/extra_checks.json')
    return exp, exp['fresh_only']


def c7_check(res, c7: Path | None):
    if c7 and c7.exists():
        d = load(c7)
        c, s, src = d['coefficients'][6], d['standard_errors'][6], str(c7)
    else:
        c, s, src = 33.5738672, 0.0019782, 'note values (C7(3) record not found; pass --c7-result)'
    p = (c - res['C6']) / math.hypot(s, res['sampling_standard_error'])
    row('H independent', 'C7(3) production by-product C6(3) and its pull from the estimator', '33.57387 +- 0.00198; -0.79',
        f'{rounded(c, 5)} +- {rounded(s, 5)}; {p:+.2f}', str(rounded(c, 5)) == '33.57387' and str(rounded(s, 5)) == '0.00198' and f'{p:+.2f}' == '-0.79',
        'printed', src)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--results', type=Path, default=ROOT / '../../results/C6_3/results_run-20260929-m8192')
    ap.add_argument('--c7-result', type=Path, default=ROOT / '../../results/C7_3/run1-20260930-m4096/C7_result.json')
    ap.add_argument('--out', type=Path, default=ROOT / '.work/replay')
    ap.add_argument('--remerge', action='store_true', help='rebuild merged records from checkpoints first (full run directory only)')
    a = ap.parse_args()
    t0 = time.time()
    directory = a.results.resolve()
    a.out.mkdir(parents=True, exist_ok=True)
    if not (ROOT / 'reference/records').is_dir():
        sys.exit('reference/ is missing: run `make -f public.mk setup` (links ../LRI_C6_D2_HPC/reference)')
    result = load(directory / 'C6_result.json')
    fail = None
    try:
        if a.remerge:
            directory = remerge(directory, a.out.resolve())
        m, mh, ar, configs, merged = load_records(directory, result)
        design_checks(m, configs, merged)
        res = estimator_checks(m, directory, result, configs)
        prev, fresh = superseded_checks(m)
        rule_and_gates(res, prev, fresh)
        precision_checks(res, m, prev, fresh)
        c7_check(res, a.c7_result.resolve())
        (a.out / 'C6_result_replayed.json').write_text(json.dumps(res, indent=2, allow_nan=False) + '\n')
    except Exception as e:  # a broken binding or record is a FAIL, not a crash without a table
        fail = f'{type(e).__name__}: {e}'
        row('Z error', 'replay aborted', '-', fail[:200], False, '-', '')
    lines = [f'# C6(3) replay ({time.strftime("%Y-%m-%d %H:%M:%S")}, {time.time() - t0:.0f} s)', '',
             f'results: `{a.results}`; package: `{ROOT.name}`; numpy {np.__version__}; python {sys.version.split()[0]}', '',
             '| # | group | quantity | quoted | replayed | tolerance | status | source |', '|---|---|---|---|---|---|---|---|']
    cell = lambda x: str(x).replace('|', '\\|')
    for i, r in enumerate(ROWS, 1):
        lines.append('| ' + ' | '.join(cell(x) for x in (i, r['group'], r['what'], r['quoted'], r['replayed'], r['tol'], r['status'], r['source'])) + ' |')
    n = {s: sum(r['status'] == s for r in ROWS) for s in ('PASS', 'FAIL', 'SKIP', 'INFO')}
    lines += ['', f"PASS {n['PASS']}, FAIL {n['FAIL']}, SKIP {n['SKIP']}, INFO {n['INFO']}", '',
              'REPLAY ' + ('PASSED' if n['FAIL'] == 0 else 'FAILED')]
    text = '\n'.join(lines) + '\n'
    (a.out / 'REPLAY_C6_3.md').write_text(text)
    print(text)
    sys.exit(1 if n['FAIL'] else 0)


if __name__ == '__main__':
    main()
