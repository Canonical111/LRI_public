#!/usr/bin/env python3
"""Replay of C6(2), the two-dimensional sixth-order production (note Sections 1, 24.6, 24.8-24.9, 28, 33), from its
merged records.

Run from the package folder (GFF/code/LRI_C6_D2_HPC) as `make -f public.mk replay`. Nothing is integrated. The
production's own assembler (tools/assemble.py at git commit 6aaf656, whose hash the frozen plan pins) recombines the 8
per-group merged records (64 replicate jet vectors each) exactly as the production's merge job did, with the same 4096
bootstrap resamples; the result is compared field by field with the published C6_result.json. Then every number the note
quotes for C6(2) is recomputed and compared at the digits the note prints.

Inputs (relative to the package folder):
  ../../data/C6_2/run-20260928-m8192/   manifest.json, groups/<g>/{config.json, merged.json, graph_replicates.csv}
  ../../results/C6_2/                   C6_result.json, preflight/threadcheck-54508994.out
  ../../results/C7_2/C7_result.json     the seventh-order production (its C6 by-product is the cross-check)
  reference/verification/               the superseded estimator and its archived checks (shipped with this package)

Hosted, not needed and not read unless present: groups/<g>/tasks.sqlite, sobol.bin and checkpoints/ (392 MiB). Their
hashes are pinned in the shipped config.json files and checkpoint records. The unmodified tools/assemble.py hash-checks
tasks.sqlite, so this script calls its evaluate() with production.group_of replaced by a version that verifies config.json
against the plan and checks tasks.sqlite only when it is present (one SKIP row says so). Everything else evaluate() checks
is unchanged: plan schema, the 5 pinned tools, the inputs manifest and the two assembly inputs, merged-record identity,
payload hash, graph_replicates.csv hash. `make -f public.mk remerge` runs the unmodified tools on the hosted copy.

Tolerances. The merge sums decimal strings at 50 digits and is bitwise reproducible; the assembly is float64 numpy
(np.cov, matrix products, convolutions, complex-step Jacobians, a PCG64 bootstrap with seed 82491001), so only the
summation order of numpy/BLAS can change last bits. Headline fields (C6, sampling_standard_error, coefficients,
standard_errors, campaigns, jet_means, error_by_loop, and estimate/sampling_se/reference of lower_order_checks): relative
1e-12. Other numbers with |reference| > 1e-9 (covariance, jet_covariances, pulls, bootstrap): relative 1e-7, because pulls
and the bootstrap amplify rounding by cancellation. Numbers with |reference| <= 1e-9 (covariance entries of the low
orders, smallest nonzero 1.6e-15, and exact zeros): absolute 1e-22. Strings, hashes and flags: exact.
Checked on macOS arm64: numpy 1.26.3 / Python 3.11.16, numpy 1.24.4 / Python 3.10.12, numpy 1.23.5 / Python 3.10.11.
Largest differences seen: headline 6.3e-16 relative (numpy 1.23.5; C6 itself is bitwise with 1.24 and 1.26, the SE is
1 ulp off), pulls 1.8e-10, bootstrap SE 7.0e-13, small covariance entries 1.5e-15 relative. The production ran Python 3.11
with numpy 1.26.4 on Linux x86-64. Quoted numbers are compared at the digits the note prints, except the 17-digit
estimator of Section 1, which is compared to relative 1e-12.
"""
import argparse, hashlib, json, math, sys
from decimal import Decimal, ROUND_CEILING
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / 'tools'))
import numpy as np  # noqa: E402
import production  # noqa: E402  (pinned by the plan; only group_of is replaced, see the header)
import assemble  # noqa: E402  (the production's assembler, pinned by the plan)
from common import object_hash  # noqa: E402
from primitive_allocation import PIDS, GRADIENT  # noqa: E402

RUN = 'run-20260928-m8192'
C7_SHA256 = '5c7a331874e480399156631c63b21a625f42cb891714912f5ef7d1beb23bdc45'
HEADLINE = ('C6', 'sampling_standard_error', 'coefficients', 'standard_errors', 'campaigns', 'jet_means', 'error_by_loop')
HEADLINE_CHECK_LEAVES = ('estimate', 'sampling_se', 'reference')
RTOL_HEAD, RTOL, ATOL, TINY = 1e-12, 1e-7, 1e-22, 1e-9
ROWS = []


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p): return json.loads(Path(p).read_text())


def row(name, got, want, ok, note='', status=None):
    ROWS.append(dict(check=name, got=got, expected=want, status=status or ('PASS' if ok else 'FAIL'), note=note))


def quoted(name, value, text, note=''):
    """PASS when value, printed with as many decimals as the quoted text, equals the quoted text."""
    t = text.replace('+', '').replace(',', '')
    nd = len(t.split('.')[1]) if '.' in t else 0
    got = f'{value:.{nd}f}'
    if text.startswith('+') and not got.startswith('-'): got = '+' + got
    row(name, got, text, float(got) == float(t), note)


def quoted_sci(name, value, text, note=''):
    """Same for a quote in scientific notation, e.g. -1.3e-5 or 7e-13 (mantissa digits as printed)."""
    mant = text.lower().split('e')[0].lstrip('+-')
    nd = len(mant.split('.')[1]) if '.' in mant else 0
    got = f'{value:.{nd}e}'
    row(name, got, text, float(got) == float(text), note)


def exact(name, got, want, note=''): row(name, got, want, got == want, note)


def flat(x, p=''):
    if isinstance(x, dict):
        for k, v in x.items(): yield from flat(v, f'{p}.{k}' if p else k)
    elif isinstance(x, list):
        for i, v in enumerate(x): yield from flat(v, f'{p}[{i}]')
    else: yield p, x


def compare_results(label, got, ref):
    G, F = dict(flat(json.loads(json.dumps(got)))), dict(flat(ref))
    worst_head = worst = worst_abs = 0.0; bad = []
    for k, w in F.items():
        if k not in G: bad.append(f'{k}: missing'); continue
        g = G[k]
        if isinstance(w, bool) or not isinstance(w, (int, float)) or not isinstance(g, (int, float)) or w is None:
            if g != w: bad.append(f'{k}: {g!r} != {w!r}')
            continue
        top = k.split('.')[0].split('[')[0]
        head = top in HEADLINE or (top == 'lower_order_checks' and k.rsplit('.', 1)[-1] in HEADLINE_CHECK_LEAVES)
        d = abs(g - w)
        if abs(w) > TINY:
            rel = d / abs(w)
            if head: worst_head = max(worst_head, rel)
            else: worst = max(worst, rel)
            if rel > (RTOL_HEAD if head else RTOL): bad.append(f'{k}: rel {rel:.2e}')
        else:
            worst_abs = max(worst_abs, d)
            if d > ATOL: bad.append(f'{k}: abs {d:.2e}')
    extra = sorted(set(G) - set(F))
    if extra: bad.append('extra fields: ' + ', '.join(extra[:5]))
    bitwise = json.dumps(json.loads(json.dumps(got)), sort_keys=True) == json.dumps(ref, sort_keys=True)
    row(f'{label}: equals C6_result.json (all {len(F)} fields)', f'{len(bad)} differences', '0 differences', not bad,
        f'max rel headline {worst_head:.1e}, other {worst:.1e}, max abs small {worst_abs:.1e}; bitwise: {"yes" if bitwise else "no"}'
        + ('; ' + '; '.join(bad[:4]) if bad else ''))


def pull(a, sa, b, sb): return (a - b) / math.hypot(sa, sb)


def verify_records(run, ref):
    """Every hash binding that can be checked without the hosted files. Returns (manifest, {group: config})."""
    m = load(run / 'manifest.json'); mh = sha(run / 'manifest.json')
    exact('manifest sha256 = C6_result.source_manifest_sha256', mh[:16], ref['source_manifest_sha256'][:16])
    exact('plan schema', m['schema'], production.SCHEMA)
    diff = [n for n, h in m['tool_sha256'].items() if sha(PKG / 'tools' / n) != h]
    row(f'shipped tools/ equal the {len(m["tool_sha256"])} tools pinned by the plan', f'{len(diff)} differ', '0 differ',
        not diff, ', '.join(diff))
    ih = sha(PKG / 'inputs/manifest.json')
    row('inputs/manifest.json = plan and result pins', ih[:16], m['inputs_manifest_sha256'][:16],
        ih == m['inputs_manifest_sha256'] == ref['input_sha256']['inputs/manifest.json'])
    table = load(PKG / 'inputs/manifest.json')['sha256']
    for n in ('two_loop.json', 'primitive_reference.json'):
        h = sha(PKG / 'inputs' / n)
        row(f'inputs/{n} = inputs manifest and result pins', h[:16], table[n][:16], h == table[n] == ref['input_sha256']['inputs/' + n])
    cfgs = {}; bad = []; csv_ok = csv_n = 0; sq = {'checked': 0, 'hosted': 0, 'bad': []}; nets = {'checked': 0, 'hosted': 0, 'bad': []}
    for g in m['groups']:
        p = run / 'groups' / g['name']; cfg = load(p / 'config.json'); d = load(p / 'merged.json'); cfgs[g['name']] = cfg
        if sha(p / 'config.json') != g['sha256']: bad.append(g['name'] + ' config')
        if sha(p / 'merged.json') != ref['merged_sha256'][g['name']]: bad.append(g['name'] + ' merged')
        if object_hash({k: v for k, v in d.items() if k != 'payload_sha256'}) != d['payload_sha256']: bad.append(g['name'] + ' payload')
        if (d.get('schema') != 'c6-d2-merged-1' or d.get('complete') is not True or d['manifest_sha256'] != mh
                or d['config_hash'] != object_hash(cfg) or d['L'] != cfg['L'] or d['primitive_mode'] != m['primitive_mode']):
            bad.append(g['name'] + ' identity')
        x = np.asarray(d['batches'], float)
        if x.shape != (cfg['replicates'], 2 * (7 - cfg['L'])) or not np.isfinite(x).all(): bad.append(g['name'] + ' shape')
        if (p / 'graph_replicates.csv').exists():
            csv_n += 1; csv_ok += sha(p / 'graph_replicates.csv') == d['graph_replicates_sha256']
        for f, key, acc in (('tasks.sqlite', cfg['tasks_sha256'], sq), ('sobol.bin', cfg['net']['sha256'], nets)):
            if (p / f).exists():
                acc['checked'] += 1
                if sha(p / f) != key: acc['bad'].append(g['name'])
            else: acc['hosted'] += 1
    row(f'{len(m["groups"])} group configs and merged records verify (hashes, payload, identity, shape)', f'{len(bad)} bad',
        '0 bad', not bad, ', '.join(bad[:6]))
    row('graph_replicates.csv = merged.graph_replicates_sha256', f'{csv_ok}/{csv_n}', f'{len(m["groups"])}/{len(m["groups"])}',
        csv_ok == csv_n == len(m['groups']))
    for f, acc in (('tasks.sqlite', sq), ('sobol.bin', nets)):
        if acc['hosted'] == len(m['groups']):
            row(f'{f} (pinned in config.json)', 'hosted', 'not read', True, 'not in git; checked by `make -f public.mk remerge`', 'SKIP')
        else:
            row(f'{f} = config.json pins', f'{acc["checked"] - len(acc["bad"])}/{acc["checked"]} match', 'all present match',
                not acc['bad'] and acc['hosted'] == 0, ', '.join(acc['bad']))
    here = any((run / 'groups' / g['name'] / 'checkpoints').is_dir() for g in m['groups'])
    row('996 checkpoints (payload hashes, task coverage)', 'present' if here else 'hosted', 'not read', True,
        'validated by the merge step of `make -f public.mk remerge`', 'SKIP')
    return m, cfgs


def recombine(run, bootstrap):
    """assemble.evaluate() as the merge job ran it, with group_of tolerating a hosted tasks.sqlite."""
    original = production.group_of

    def group_of(directory, m, name):
        p = directory / 'groups' / name
        config = production.read_verified(p / 'config.json', next(g['sha256'] for g in m['groups'] if g['name'] == name))
        if (p / 'tasks.sqlite').exists(): production.checked(p / 'tasks.sqlite', config['tasks_sha256'])
        return p, config
    production.group_of = group_of
    try: return assemble.evaluate(run, bootstrap)
    finally: production.group_of = original


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--data', type=Path, default=PKG / '../../data/C6_2' / RUN)
    ap.add_argument('--results', type=Path, default=PKG / '../../results/C6_2')
    ap.add_argument('--c7', type=Path, default=PKG / '../../results/C7_2/C7_result.json')
    ap.add_argument('--extra-result', type=Path, action='append', default=[],
                    help='another C6_result.json to compare with the published one (remerge passes the unmodified CLI output)')
    ap.add_argument('--out', type=Path, default=PKG / 'public/out')
    a = ap.parse_args(); run, res = a.data.resolve(), a.results.resolve()
    ref = load(res / 'C6_result.json')

    # --- records and recombination
    m, cfgs = verify_records(run, ref)
    try:
        r = recombine(run, ref['bootstrap']['replicates'])
        compare_results('recombined result (assemble.evaluate, 4096 bootstrap resamples)', r, ref)
    except Exception as e:  # report and continue with the published result, so every other row still prints
        row('recombination with tools/assemble.py', type(e).__name__, 'no error', False, str(e)[:200]); r = ref
    for f in a.extra_result: compare_results(f'{f.name}', load(f), ref)

    # --- quoted values (line numbers: note at fa71533)
    C, S = r['C6'], r['sampling_standard_error']
    allowance = (Decimal(repr(4 * S)) / Decimal('0.001')).to_integral_value(ROUND_CEILING) * Decimal('0.001')
    quoted('Sec 1 (l.62, 102), 24.6, 24.9: C6(2) value', C, '362.366')
    quoted('4 sampling SE (Sec 24.6)', 4 * S, '0.0032')
    row('allowance: 4 SE rounded up to a multiple of 0.001 (Sec 1 l.135, 24.6)', f'{allowance}', '0.004', allowance == Decimal('0.004'))
    exact('note form: estimator at the allowance\'s digit, allowance rounded up', f'{C:.3f}\\pm{allowance}', '362.366\\pm0.004')
    # the paper (numbers.tex \\CsixTwo, 2026-10-14) uses the PDG rule: the 4-SE allowance to two significant digits and the
    # estimate to the same decimal place; the note keeps its rounded-up allowance
    pdg = float(f'{4 * S:.2g}'); nd = max(0, -Decimal(repr(pdg)).normalize().as_tuple().exponent)
    exact('paper form (PDG rounding): numbers.tex \\CsixTwo', f'{C:.{nd}f}\\pm{pdg:.{nd}f}', '362.3665\\pm0.0032')
    row('Sec 1 l.124: underlying estimator (relative 1e-12)', repr(C), '362.36647176375726',
        abs(C - 362.36647176375726) <= 1e-12 * 362.36647176375726)
    quoted('Sec 1 l.124: sampling SE', S, '0.0007997307')
    quoted('Sec 24.6 table / 24.9 table: combined', C, '362.36647176'); quoted('combined SE', S, '0.00079973')
    ca, cb = r['campaigns']['a'], r['campaigns']['b']
    for t, c, v, s in (('a', ca, '362.36672022', '0.00097561'), ('b', cb, '362.36622331', '0.00126747')):
        quoted(f'campaign {t}', c['C6'], v); quoted(f'campaign {t} SE', c['sampling_se'], s)
    ab = pull(ca['C6'], ca['sampling_se'], cb['C6'], cb['sampling_se'])
    quoted('campaigns differ by (combined SE)', abs(ab), '0.31')
    prev = load(PKG / 'reference/verification/method_precision_results.json')['2']
    proj = prev['fresh_only']['sampling_standard_error'] / math.sqrt(2 * m['allocation_multiplier'])
    quoted('projected SE (archived fresh-only SE / sqrt(2 x 8192))', proj, '0.0015')
    quoted('realized / projected SE ("about half")', S / proj, '0.5')
    quoted('previous estimator', prev['C6'], '362.3489138'); quoted('previous SE', prev['sampling_standard_error'], '0.1526445')
    arch = (C - prev['C6']) / prev['sampling_standard_error']
    quoted('new estimator from the previous one (previous SE)', arch, '0.12')
    row('note README: SE "190 times smaller" than before', f'{prev["sampling_standard_error"] / S:.1f}', '190',
        int(prev['sampling_standard_error'] / S) == 190, 'ratio 190.9; the README truncates')
    # C7(2) cross-check (Sec 24.6 l.10063-10066 and Sec 28 l.11204)
    c7h = sha(a.c7); c7 = load(a.c7)
    exact('C7(2) result file sha256', c7h[:16], C7_SHA256[:16])
    v7, s7 = c7['coefficients'][6], c7['standard_errors'][6]
    quoted('C7(2) by-product C6 (Sec 24.6)', v7, '362.3727'); quoted('its SE (Sec 24.6)', s7, '0.0086')
    quoted('C7(2) by-product C6 (Sec 28 table)', v7, '362.3727456'); quoted('its SE (Sec 28 table)', s7, '0.0085778')
    quoted('C7(2) by-product from C6(2) (combined SE)', pull(v7, s7, C, S), '+0.73')
    # error budget (Sec 24.8, l.10394) and lower-order checks (l.10404)
    for L, t in (('3', '0.000005'), ('4', '0.000113'), ('5', '0.000365'), ('6', '0.000702')):
        quoted(f'error budget L={L}', r['error_by_loop'][L], t)
    quoted('error budget, common term', r['shared_reference_standard_error'], '0.000000')
    quoted('error budget, total', math.sqrt(sum(v ** 2 for v in r['error_by_loop'].values()) + r['shared_reference_standard_error'] ** 2), '0.000800')
    for c, t in zip(r['lower_order_checks'], ('-0.97', '-1.54', '-1.07')): quoted(f'C{c["order"]} pull', c['pull'], t)
    b = r['bootstrap']
    exact('bootstrap resamples', b['replicates'], 4096)
    quoted('bootstrap SE (Sec 24.9 l.10416)', b['sampling_se'], '0.00080124')
    quoted_sci('bootstrap mean - estimate', b['mean_minus_estimate'], '-1.3e-5')
    # archived checks of the previous estimator (shared d=2/d=3 sentence, Sec 24.9 l.10411-10414)
    ref_sums = load(PKG / 'reference/SHA256SUMS.json')
    for f in ('verification/method_precision_results.json', 'verification/extra_checks.json'):
        exact(f'reference/{f} = reference/SHA256SUMS.json', sha(PKG / 'reference' / f)[:16], ref_sums[f][:16])
    ex = load(PKG / 'reference/verification/extra_checks.json')['2']
    quoted_sci('archived Lagrange vs fixed point, d=2', ex['max_Lagrange_difference'], '7e-13')
    jk = max(abs(x) for x in ex['nonlinear_jackknife_bias'])
    row('archived delete-one bias, d=2, below 3.4e-7', f'{jk:.3e}', '< 3.4e-7', jk < 3.4e-7)
    # pre-registered consistency gates (CAMPAIGN.md)
    row('gate: |a - b| <= 3 combined SE', f'{abs(ab):.4f}', '<= 3', abs(ab) <= 3)
    ratio = b['sampling_se'] / S
    row('gate: bootstrap SE within 20% of covariance SE', f'{ratio:.4f}', '0.8 .. 1.2', 0.8 <= ratio <= 1.2)
    row('gate: previous estimator within 3 previous SE', f'{abs(arch):.4f}', '<= 3', abs(arch) <= 3)
    mx = max(abs(c['pull']) for c in r['lower_order_checks'])
    row('gate: |C3-C5 pulls| <= 4', f'{mx:.4f}', '<= 4', mx <= 4)
    # sample design (Sec 24.6 l.10007-10031), from the configs and the plan
    gs = {g: c for g, c in cfgs.items()}
    exact('nonzero classes per loop (L=3..6)', [len(gs[f'a_L{L}']['counts']) for L in range(3, 7)], [5, 16, 76, 395])
    exact('replicates in every group', sorted({c['replicates'] for c in gs.values()}), [64])
    exact('net bits, campaign a / b', [sorted({c['net']['bits'] for n, c in gs.items() if n[0] == t}) for t in 'ab'], [[52], [60]])
    exact('frozen separable map used by', sorted(n for n, c in gs.items() if c.get('grid')), ['a_L6'])
    exact('allocation multiplier (2^13)', m['allocation_multiplier'], 2 ** 13)
    a6 = {int(k): v for k, v in gs['a_L6']['counts'].items()}
    floor = sorted(k for k, v in a6.items() if v == 4 * 2 ** 13)
    exact('smallest per-replicate count at L=6 (4 x 2^13)', min(a6.values()), 4 * 2 ** 13)
    exact('kernels at that floor', len(floor), 28)
    exact('a and b use the same counts', all(gs[f'a_L{L}']['counts'] == gs[f'b_L{L}']['counts'] for L in range(3, 7)), True)
    for L, t in ((3, 1107296256), (4, 2164260864), (5, 9487515648)):
        exact(f'points per replicate, L={L}', gs[f'a_L{L}']['samples'] // 64, t)
    prim = [k for k in a6 if k in PIDS]
    exact('primitive kernels at L=6', len(prim), 10)
    exact('points per replicate, 385 nonprimitive L=6 kernels', (sum(a6.values()) - sum(a6[k] for k in prim), len(a6) - len(prim)), (38076809216, 385))
    exact('points per replicate, 10 primitives', sum(a6[k] for k in prim), 5645533184)
    exact('kernel samples, both campaigns', sum(c['samples'] for c in gs.values()), 7229621141504)
    exact('tasks (independent of nodes and threads)', sum(c['tasks'] for c in gs.values()), 865664)
    exact('array elements, threads per element', (len(m['jobs']), m['threads']), (428, 64))
    # the floor affects only kernels whose C6 projection vanishes: dC6/d(b6,c6) = (-1,3)/2187 (tools/primitive_allocation.py)
    worst = 0.0; n = 0
    for t in 'ab':
        lines = (run / f'groups/{t}_L6/graph_replicates.csv').read_text().splitlines()[1:]
        for ln in lines:
            rep, gi, b6, c6 = ln.split(','); gi = int(gi)
            if gi in floor:
                b6, c6 = Decimal(b6), Decimal(c6); n += 1
                proj = abs(Decimal(GRADIENT[0]) * b6 + Decimal(GRADIENT[1]) * c6); scale = abs(b6) + 3 * abs(c6)
                worst = max(worst, float(proj / scale) if scale else 0.0)
    row('the 28 floor kernels have zero C6 projection (64 replicates x 2 campaigns)', f'max |(-b6+3c6)|/(|b6|+3|c6|) = {worst:.1e}',
        '< 1e-15', n == 28 * 64 * 2 and worst < 1e-15, f'{n} per-graph replicate sums from graph_replicates.csv')
    core_h = sum(load(run / 'groups' / g / 'merged.json')['integration_seconds_sum'] for g in cfgs) * m['threads'] / 3600
    row('native integration core-hours (sum of block seconds x 64) vs 12,535 billed (Sec 24.6)', f'{core_h:.0f}', '0.97 .. 1.00 of 12535',
        0.97 * 12535 <= core_h <= 12535, 'the billed figure (Slurm accounting) adds start-up, staging and the merge')
    tc = (res / 'preflight/threadcheck-54508994.out').read_text().split('THREADCHECK')[1].split()
    tc = dict(x.split('=') for x in tc[:4])
    exact('thread identity: rows at 64 vs 16 threads, mismatches (Sec 24.6)', (int(tc['rows']), int(tc['mismatches'])), (2048, 0),
          'recorded by the preflight job; rerun template in REPRODUCE.md')
    exact('thread identity: binary128 promotions', int(tc['quad_promotions']), 152717)

    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / 'replay.json').write_text(json.dumps(dict(numpy=np.__version__, python=sys.version.split()[0], rows=ROWS), indent=1, default=str) + '\n')
    w = max(len(x['check']) for x in ROWS)
    for x in ROWS: print(f"{x['status']:<4}  {x['check']:<{w}}  {x['got']!s:>16}  (expected {x['expected']})" + (f"  {x['note']}" if x['note'] else ''))
    fails = sum(x['status'] == 'FAIL' for x in ROWS); skips = sum(x['status'] == 'SKIP' for x in ROWS)
    print(f'\n{len(ROWS) - fails - skips} PASS, {skips} SKIP (hosted), {fails} FAIL (numpy {np.__version__}, Python {sys.version.split()[0]})')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
