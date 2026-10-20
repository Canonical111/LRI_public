#!/usr/bin/env python3
"""Replay of the independent C8(2) check (note Section 31.7) from its merged records.

Run from the package folder (GFF/code/LRI_C8_D2_HPC_optimized) as `make -f public.mk replay`. Nothing is integrated: the
production's own assembler, tools/assemble.py at the commit that ran, recombines the 24 per-group merged records of the
production (and of the pilot) and the result is compared field by field with the published C8_result.json. Then every
number the note quotes for this check is recomputed and compared with its quoted digits.

Inputs (relative to the package folder):
  ../../data/C8_2_check/prod1/    manifest.json, allocation.json, cost_model.json, groups/<g>/{config,merged}.json, attempts/
  ../../data/C8_2_check/pilot1/   manifest.json, groups/<g>/{config,merged}.json
  ../../results/C8_2_check/       prod1/C8_result.json, pilot1/C8_result.json, prod1_analysis/ (recorded diagnostics)
  ../../results/C8_2/C8_final.json, ../../results/C7_2/C7_result.json   (the estimates this check is compared with)

Not needed and not read: tasks.sqlite, graph_replicates.csv and the checkpoints of each group (1.7 GB, hosted). Their hashes
are pinned in the shipped configs and merged records; `make -f public.mk remerge` uses them after `fetch-data`.

Tolerances. Same records, same code: the recombination is a deterministic numpy computation (bootstrap with a fixed seed),
so differences come only from numpy/BLAS summation order. Headline fields (C8_full, its sampling SE, all coefficients and
their SEs, the power-free part and its SE, campaigns, half streams, and the estimates of the lower-order checks): relative
1e-12. All other fields: relative 1e-7 where |reference| > 1e-9, absolute 1e-12 otherwise. Those are differences of nearly
equal numbers (power correction and power differences, lower-order pulls, bootstrap bias), whose relative rounding error is
amplified by the cancellation. Checked: numpy 2.3.5 / Python 3.11.9 (the production, Expanse) and numpy 1.23.5 /
Python 3.10 (Mac): headline fields within 4e-16 relative, all fields within 3.6e-9 (bootstrap bias at order 6).
Quoted numbers are compared at the digits the note prints.
"""
import argparse, datetime as dt, hashlib, json, math, sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / 'tools'))
import numpy as np  # noqa: E402
import assemble  # noqa: E402  (the production's assembler, pinned by the manifest)
from production import object_hash, SMALL_INPUTS  # noqa: E402

HEADLINE = ('C8_full', 'sampling_standard_error', 'coefficients', 'standard_errors', 'power_free_C8', 'power_free_se',
            'campaigns', 'half_streams')
HEADLINE_CHECK_LEAVES = ('estimate', 'sampling_se', 'reference', 'reference_se')  # of lower_order_checks; pulls are differences
RTOL_HEAD, RTOL, ATOL, TINY = 1e-12, 1e-7, 1e-12, 1e-9
ROWS = []


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p): return json.loads(Path(p).read_text())


def row(name, got, want, ok, note=''):
    ROWS.append(dict(check=name, got=got, expected=want, status='PASS' if ok else 'FAIL', note=note))


def quoted(name, value, text, note=''):
    """PASS when value, printed with as many decimals as the quoted text, equals the quoted text."""
    t = text.replace('+', '').replace(',', '')
    nd = len(t.split('.')[1]) if '.' in t else 0
    got = f'{value:.{nd}f}'
    row(name, got if not text.startswith('+') or got.startswith('-') else '+' + got, text, float(got) == float(t), note)


def flat(x, p=''):
    if isinstance(x, dict):
        for k, v in x.items(): yield from flat(v, f'{p}.{k}' if p else k)
    elif isinstance(x, list):
        for i, v in enumerate(x): yield from flat(v, f'{p}[{i}]')
    else: yield p, x


def compare_results(label, got, ref):
    G, F = dict(flat(got)), dict(flat(ref))
    worst_head = worst = 0.0; bad = []
    for k, w in F.items():
        if k not in G: bad.append(f'{k}: missing'); continue
        g = G[k]
        if isinstance(w, bool) or not isinstance(w, (int, float)) or not isinstance(g, (int, float)) or w is None:
            if g != w: bad.append(f'{k}: {g!r} != {w!r}')
            continue
        top = k.split('.')[0].split('[')[0]
        d = abs(g - w); head = top in HEADLINE or (top == 'lower_order_checks' and k.rsplit('.', 1)[-1] in HEADLINE_CHECK_LEAVES)
        if abs(w) > TINY:
            rel = d / abs(w)
            if head: worst_head = max(worst_head, rel)
            else: worst = max(worst, rel)
            if rel > (RTOL_HEAD if head else RTOL): bad.append(f'{k}: rel {rel:.2e}')
        elif d > ATOL: bad.append(f'{k}: abs {d:.2e}')
    extra = sorted(set(G) - set(F))
    if extra: bad.append('extra fields: ' + ', '.join(extra[:5]))
    row(f'{label}: recombined result equals C8_result.json (all {len(F)} fields)', f'{len(bad)} differences',
        '0 differences', not bad, f'max rel headline {worst_head:.1e}, other {worst:.1e}' + ('; ' + '; '.join(bad[:4]) if bad else ''))


def recombine(run, ref):
    m = load(run / 'manifest.json'); mh = sha(run / 'manifest.json')
    row(f'{run.name}: manifest sha256 = result source_manifest_sha256', mh[:16], ref['source_manifest_sha256'][:16],
        mh == ref['source_manifest_sha256'])
    pins = {n: h for n, h in m['tool_sha256'].items() if sha(PKG / 'tools' / n) != h}
    row(f'{run.name}: shipped tools/ equal the {len(m["tool_sha256"])} tools pinned by the plan', f'{len(pins)} differ', '0 differ',
        not pins, ', '.join(pins))
    im = load(PKG / 'inputs/manifest.json')
    ok = sha(PKG / 'inputs/manifest.json') == m['inputs_manifest_sha256'] and all(
        sha(PKG / 'inputs' / n) == im['sha256'][n] for n in SMALL_INPUTS)
    row(f'{run.name}: inputs manifest and {", ".join(SMALL_INPUTS)} as pinned', 'match' if ok else 'mismatch', 'match', ok)
    for key, f in (('allocation_file_sha256', 'allocation.json'), ('cost_model_sha256', 'cost_model.json')):
        if m.get(key):
            row(f'{run.name}: {f} as pinned', 'match' if sha(run / f) == m[key] else 'mismatch', 'match', sha(run / f) == m[key])
    ar = {s: {t: {} for t in 'ab'} for s in ('free', 'power')}; bad = []
    for g in m['groups']:
        p = run / 'groups' / g['name']; cfg = load(p / 'config.json'); d = load(p / 'merged.json')
        if sha(p / 'config.json') != g['sha256']: bad.append(g['name'] + ' config')
        if sha(p / 'merged.json') != ref['merged_sha256'][g['name']]: bad.append(g['name'] + ' merged')
        if object_hash({k: v for k, v in d.items() if k != 'payload_sha256'}) != d['payload_sha256']: bad.append(g['name'] + ' payload')
        if d['manifest_sha256'] != mh or d['config_hash'] != object_hash(cfg) or d.get('complete') is not True: bad.append(g['name'] + ' identity')
        x = np.asarray(d['batches'], float)
        if x.shape != (cfg['replicates'], 2 * (9 - cfg['L'])): bad.append(g['name'] + ' shape')
        ar[cfg['sector']][cfg['campaign']][cfg['L']] = x
    row(f'{run.name}: {len(m["groups"])} group configs and merged records verify (hashes, identity, shape)',
        f'{len(bad)} bad', '0 bad', not bad, ', '.join(bad[:6]))
    r = assemble.combine(ar, None, ref['bootstrap']['replicates'])
    r.update(source_manifest_sha256=mh, merged_sha256={g['name']: sha(run / 'groups' / g['name'] / 'merged.json') for g in m['groups']},
             primitive_mode=m['primitive_mode'], backend=m['backend'], build=m['build'], test_only=m['test_only'],
             allocation=m.get('allocation'), purpose=m.get('purpose', 'pilot'))
    r['numerical_status'] = ('complete-coverage pilot; convergence not established' if r['purpose'] == 'pilot' else
                             'complete-coverage numerical campaign; inspect convergence diagnostics before reporting')
    compare_results(run.name, r, ref)
    return m, r


def pull(a, sa, b, sb): return (a - b) / math.hypot(sa, sb)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--data', type=Path, default=PKG / '../../data/C8_2_check')
    ap.add_argument('--results', type=Path, default=PKG / '../../results/C8_2_check')
    ap.add_argument('--ours8', type=Path, default=PKG / '../../results/C8_2/C8_final.json')
    ap.add_argument('--ours7', type=Path, default=PKG / '../../results/C7_2/C7_result.json')
    ap.add_argument('--out', type=Path, default=PKG / 'public/out')
    a = ap.parse_args(); data, res = a.data.resolve(), a.results.resolve()

    ref = load(res / 'prod1/C8_result.json'); m, r = recombine(data / 'prod1', ref)
    pref = load(res / 'pilot1/C8_result.json'); pm, pr = recombine(data / 'pilot1', pref)
    o8, o7 = load(a.ours8), load(a.ours7)

    # --- the numbers quoted in the note (Section 31.7, Sections 1, 28 and 31.1)
    quoted('C8(2), independent code', r['C8_full'], '46006.1'); quoted('its sampling SE', r['sampling_standard_error'], '13.4')
    quoted('combined (table)', r['C8_full'], '46006.14'); quoted('combined SE (table)', r['sampling_standard_error'], '13.42')
    for t, v, s in (('a', '46012.55', '19.70'), ('b', '45999.73', '18.23')):
        quoted(f'campaign {t}', r['campaigns'][t]['C8'], v); quoted(f'campaign {t} SE', r['campaigns'][t]['sampling_se'], s)
    quoted('first half stream', r['half_streams'][0][8], '46008.16'); quoted('second half stream', r['half_streams'][1][8], '46004.11')
    ca, cb = r['campaigns']['a'], r['campaigns']['b']
    quoted('campaign difference (combined SE)', abs(pull(ca['C8'], ca['sampling_se'], cb['C8'], cb['sampling_se'])), '0.48')
    quoted('bootstrap SE (4,096 resamples)', r['bootstrap']['full_se'][8], '13.38')
    row('bootstrap resamples', r['bootstrap']['replicates'], 4096, r['bootstrap']['replicates'] == 4096)
    quoted('power-free part', r['power_free_C8'], '46004.84'); quoted('power-free SE', r['power_free_se'], '12.90')
    quoted('power correction', r['power_correction'], '+1.29'); quoted('power correction SE', r['power_correction_se'], '3.71')
    se2 = r['sampling_standard_error'] ** 2
    quoted('variance share, power-free L8 (%)', 100 * r['error_by_loop']['8']['free'] ** 2 / se2, '78')
    quoted('variance share, power-free L7 (%)', 100 * r['error_by_loop']['7']['free'] ** 2 / se2, '14')
    for c, t in zip(r['lower_order_checks'], ('-0.01', '+1.75', '+0.57', '-1.18', '+1.04')):
        quoted(f'lower-order pull C{c["order"]}', c['pull'], t)
    quoted('sum of squared lower-order pulls', sum(c['pull'] ** 2 for c in r['lower_order_checks']), '5.88')
    quoted('max |pull| of the power null rows (orders 4-6)', max(abs(c['pull']) for c in r['power_null_checks'] if c['pull'] is not None), '0.76')
    quoted('C7(2) by-product', r['coefficients'][7], '-3875.47'); quoted('C7(2) by-product SE', r['standard_errors'][7], '0.35')
    quoted('C7(2) by-product vs the C7(2) production (combined SE)', pull(r['coefficients'][7], r['standard_errors'][7],
           o7['C7_full'], o7['sampling_standard_error']), '+1.04')
    d, sd = r['C8_full'] - o8['C8_full'], math.hypot(r['sampling_standard_error'], o8['sampling_standard_error'])
    quoted('difference from the reported estimator', d, '+16.1'); quoted('its combined SE', sd, '15.7')
    quoted('difference in combined SE', d / sd, '+1.03')
    quoted('power-free parts differ by (combined SE)', abs(pull(r['power_free_C8'], r['power_free_se'], o8['power_free_C8'], o8['power_free_se'])), '0.90')
    quoted('power corrections differ by (combined SE)', abs(pull(r['power_correction'], r['power_correction_se'], o8['power_correction'], o8['power_correction_se'])), '0.54')
    # pilot and allocation
    quoted('pilot C8(2)', pr['C8_full'], '46178'); quoted('pilot SE', pr['sampling_standard_error'], '417')
    reps = {load(data / 'pilot1/groups' / g['name'] / 'config.json')['replicates'] for g in pm['groups']}
    row('pilot replicates per campaign', sorted(reps), [32], reps == {32})
    al = load(data / 'prod1/allocation.json')
    quoted('allocation, kernel core-hours', al['target_core_hours'], '28500'); row('allocation replicates', al['replicates'], 64, al['replicates'] == 64)
    quoted('predicted SE', al['model_only_standard_error_forecast'], '14.97')
    for s, want in (('free', 8192), ('power', 4096)):
        v = min(al['counts'][s]['8'].values()); row(f'min points per replicate, {s} L8 graphs', v, want, v == want)
    n = {(s, L): len(al['counts'][s][L]) for s in al['counts'] for L in al['counts'][s]}
    for name, got, want in (('kernels in all', sum(n.values()), 24173), ('power-free L8 kernels', n['free', '8'], 16064),
                            ('power L8 kernels', n['power', '8'], 4336), ('L7 kernels', n['free', '7'] + n['power', '7'], 3150)):
        row(name, got, want, got == want)
    # cost, from the attempt records (job spans; the note's 207 node-h come from the scheduler's elapsed times)
    jobs = {}; outcomes = {}
    for f in sorted((data / 'prod1/attempts').glob('*.jsonl')):
        for line in f.read_text().splitlines():
            t = json.loads(line); outcomes[f.stem] = outcomes.get(f.stem, []) + [t['outcome']]
            s, e = (dt.datetime.fromisoformat(t[k].replace('Z', '+00:00')) for k in ('start', 'end'))
            j = jobs.setdefault(t['job'], [s, e]); j[0], j[1] = min(j[0], s), max(j[1], e)
    once = sum(v == ['done'] for v in outcomes.values())
    row('work indices that ran once, without a failure', once, 342, once == 342 and len(outcomes) == len(m['jobs']) == 342)
    row('whole nodes', len(jobs), 11, len(jobs) == 11)
    span = sorted((e - s).total_seconds() / 3600 for s, e in jobs.values())
    quoted('shortest node wall (h)', span[0], '16.3'); quoted('longest node wall (h)', span[-1], '20.1')
    nh = sum(span); row('node-hours (attempt spans)', round(nh, 1), 207, abs(nh - 207.2) < 0.5, 'scheduler elapsed 207.2 node-h; spans omit ~30 s of runner start-up per node')
    row('core-hours (128 per node)', round(nh * 128), 26526, abs(nh * 128 - 26526) / 26526 < 0.003)
    # kernel time: per attempt, the sum of the checkpoint rows' seconds (tools in public/kernel_time.py; needs the hosted
    # checkpoints); here the recorded total is divided by the allocated core-hours
    kern = float((res / 'prod1_analysis/kernel_util.txt').read_text().split('kernel_core_h ')[1].split()[0])
    quoted('kernel time, % of allocated core-hours (recorded kernel core-h / attempt spans)', 100 * kern / (nh * 128), '96.5')

    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / 'replay.json').write_text(json.dumps(dict(numpy=np.__version__, python=sys.version.split()[0], rows=ROWS), indent=1) + '\n')
    w = max(len(x['check']) for x in ROWS)
    for x in ROWS: print(f"{x['status']}  {x['check']:<{w}}  {x['got']!s:>14}  (expected {x['expected']})" + (f"  {x['note']}" if x['note'] else ''))
    fails = sum(x['status'] == 'FAIL' for x in ROWS)
    print(f'\n{len(ROWS) - fails} PASS, {fails} FAIL (numpy {np.__version__})')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
