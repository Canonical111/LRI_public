#!/usr/bin/env python3
"""Replay of C8(2) = 45990 +- 33 (note Section 31; Section 1 tables) from the shipped records.

Run from the package folder (GFF/code/LRI_C8_D2_HPC) as `make -f public.mk replay`. Nothing is integrated. The package's
own code at the production commit (tools/assemble.py, tools/combine.py, tools/production.py, tools/verify_result.py,
the vendored order-8 assembly) recombines the 24 merged group records of the production batch, and the results are
compared field by field with the batch's C8_result.json (assembly, 4,096 bootstrap draws) and the published
C8_final.json (combination of the K = 1 planned batches, 1,024 draws). Then every number the note quotes for C8(2) is
recomputed from the records and compared at the digits the note prints.

Inputs (relative to this folder):
  ../../data/C8_2/prod1-2.5e-4-ddmp256-20261006-ba68f401e46e/   the batch: manifest.json, cost_model.json, design_bundle/,
        C8_result.json, groups/<g>/{config,merged}.json (copied from the campaign directory; same name, so the batch label
        that combine.py records is unchanged)
  ../../results/C8_2/   C8_final.json (the published record), pilot/C8_result.json, production/{analysis,accounting}.json and
        tails.csv.gz, tailcheck/*.json (the published analyses this replay compares with)
  ../../results/C7_2/C7_result.json, ../../results/C6_2/C6_result.json   (the lower-order references)
  ../LRI_C8_shared/   the shared inventory and the order-8 assembly (vendored copy compared byte for byte)
  benchmarks/symmetry_2026-10-c8/ and benchmarks/expanse_2026-10-c8/   evidence shipped with the code (scheduler records,
        pilot analysis, numerics gate records), read as inputs
  reference/ or ../LRI_C7_D2_HPC/reference/   the C7(2) reference trees (class tables at loops 3-6)

Not read (hosted, see ../../data/C8_2/DATA.md): each group's graph_replicates.csv, graph_tails.csv, graph_costs.csv,
tasks, checkpoints and logs. Their sha256 are pinned in the shipped merged.json and config.json; `make -f public.mk
replay-tails` uses them after `fetch-data`. The one check of the package's own loader that needs them
(production.validate_merged) is replaced here by the same checks minus the three table hashes (row says so).

Tolerances (why): the recombination is a deterministic numpy computation (bootstrap with the package's fixed seed), so
differences come only from numpy/BLAS summation order. Headline fields (C8_full, its SE, the coefficient and SE vectors,
power-free part and SE, campaigns, half streams, the estimates and references of the lower-order checks): relative 1e-12.
Every other float: relative 1e-7 where |reference| > 1e-9, absolute 1e-12 otherwise; these include differences of nearly
equal numbers (power correction and power differences, pulls, bootstrap bias), whose relative rounding error is amplified
by cancellation. The gates' rounding-level residuals (affinity linear_response_residual, loop-7 rel_deviation): absolute
1e-9 (64 ulp of the C8 scale 4.6e4; tools/verify_result.py bounds them the same way). Quoted numbers: equal at the printed
digits. Checked on macOS (arm64) with Python 3.10.11 / numpy 1.23.5 (anaconda) against records written on AMD EPYC 7543
with Python 3.11 / numpy 2.3.5: see the max differences printed in the comparison rows.
Output: a PASS/FAIL/SKIP table on stdout, public/out/replay.json; exit 1 on any FAIL.
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import csv
import hashlib
import json
import math
import re
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / 'tools'))
import numpy as np  # noqa: E402
import assemble as asm  # noqa: E402  (the production's assembler; verifies the vendored module at import)
import combine as cb  # noqa: E402
import production as prod  # noqa: E402
import verify_result as vr  # noqa: E402
from common import object_hash  # noqa: E402

RUN_NAME = 'prod1-2.5e-4-ddmp256-20261006-ba68f401e46e'
EV = PKG / 'benchmarks/symmetry_2026-10-c8'
HEADLINE = ('C8_full', 'sampling_standard_error', 'coefficients', 'standard_errors', 'power_free_C8', 'power_free_se',
            'campaigns', 'half_streams')
CHECK_HEAD = ('estimate', 'sampling_se', 'reference', 'reference_se')
ROUNDING = ('linear_response_residual', 'rel_deviation')
RTOL_HEAD, RTOL, ATOL, ATOL_ROUND, TINY = 1e-12, 1e-7, 1e-12, 1e-9, 1e-9
ROWS: list[dict] = []


def sha(p) -> str:
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def load(p):
    return json.loads(Path(p).read_bytes())


def row(name, got, want, ok, note='', status=None):
    ROWS.append(dict(check=name, got=got, expected=want, status=status or ('PASS' if ok else 'FAIL'), note=note))


def skip(name, why):
    row(name, '-', '-', True, why, status='SKIP')


def quoted(name, value, text, note=''):
    """PASS when value printed at the digits of the quoted text equals it (fixed or e-notation)."""
    t = text.replace('+', '').replace(',', '').replace('−', '-')
    if 'e' in t:
        mant = t.split('e')[0]
        nd = len(mant.split('.')[1]) if '.' in mant else 0
        got = f'{value:.{nd}e}'
        ok = float(got) == float(t)
        got = re.sub(r'e([+-])0*(\d)', r'e\g<1>\2', got).replace('e+', 'e')
    else:
        nd = len(t.split('.')[1]) if '.' in t else 0
        got = f'{value:.{nd}f}'
        ok = float(got) == float(t)
    if text.startswith('+') and not got.startswith('-'):
        got = '+' + got
    row(name, got, text, ok, note)


def flat(x, p=''):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from flat(v, f'{p}.{k}' if p else k)
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from flat(v, f'{p}[{i}]')
    else:
        yield p, x


def compare_results(label, got, ref):
    G, F = dict(flat(got)), dict(flat(ref))
    worst_head = worst = worst_round = 0.0
    bad = []
    for k, w in F.items():
        if k not in G:
            bad.append(f'{k}: missing')
            continue
        g = G[k]
        if isinstance(w, bool) or not isinstance(w, (int, float)) or not isinstance(g, (int, float)) or isinstance(g, bool):
            if g != w:
                bad.append(f'{k}: {g!r} != {w!r}')
            continue
        top = k.split('.')[0].split('[')[0]
        d = abs(g - w)
        if any(r in k for r in ROUNDING):
            worst_round = max(worst_round, d)
            if d > ATOL_ROUND:
                bad.append(f'{k}: abs {d:.2e}')
            continue
        head = top in HEADLINE or (top == 'lower_order_checks' and k.rsplit('.', 1)[-1] in CHECK_HEAD)
        if abs(w) > TINY:
            rel = d / abs(w)
            if head:
                worst_head = max(worst_head, rel)
            else:
                worst = max(worst, rel)
            if rel > (RTOL_HEAD if head else RTOL):
                bad.append(f'{k}: rel {rel:.2e}')
        elif d > ATOL:
            bad.append(f'{k}: abs {d:.2e}')
    extra = sorted(set(G) - set(F))
    if extra:
        bad.append('extra fields: ' + ', '.join(extra[:5]))
    row(f'{label}: all {len(F)} fields', f'{len(bad)} differences', '0 differences', not bad,
        f'max rel headline {worst_head:.1e}, other {worst:.1e}; rounding-level abs {worst_round:.1e}'
        + ('; ' + '; '.join(bad[:4]) if bad else ''))


def pull(a, sa, b, sb):
    return (a - b) / math.hypot(sa, sb)


def sacct_rows(path: Path) -> list[dict]:
    """Rows of an `sacct` table, parsed by tokens in the header's column order (not by column widths, so that the release
    scrub, which replaces node names by a token of another length, cannot shift a column). Two values contain spaces:
    the state 'CANCELLED by <uid>' and the node list 'None assigned'."""
    lines = path.read_text().splitlines()
    head = lines[0].split()
    out = []
    for ln in lines[2:]:
        tok = ln.split()
        if not tok:
            continue
        row, i = {}, 0
        for h in head:
            if h == 'State' and tok[i] == 'CANCELLED' and i + 1 < len(tok) and tok[i + 1] == 'by':
                row[h], i = ' '.join(tok[i:i + 3]), i + 3
            elif h == 'NodeList' and tok[i] == 'None' and i + 1 < len(tok) and tok[i + 1] == 'assigned':
                row[h], i = 'None assigned', i + 2
            else:
                row[h], i = tok[i], i + 1
        if i != len(tok):
            raise ValueError(f'{path}: cannot parse the row {ln!r}')
        out.append(row)
    return out


def core_hours(rows) -> float:
    """Physical-core hours as tools/accounting.py counts them: 64 per AMD node, AllocCPUS/2 on the Intel shared nodes."""
    return sum(int(r['ElapsedRaw'] or 0) * (64 if r['Partition'].startswith('amd') else int(r['AllocCPUS'] or 0) / 2)
               for r in rows) / 3600


def ref_path(rel: str) -> Path:
    """A C7(2) reference file: here after `make -f public.mk setup`, else in its one shipped copy."""
    p = PKG / 'reference' / rel
    return p if p.is_file() else PKG.parent / 'LRI_C7_D2_HPC' / 'reference' / rel


# ---------------------------------------------------------------------------------------------------------------------
def recombine(run: Path, res: Path):
    data_result = load(run / 'C8_result.json')
    final = load(res / 'C8_final.json')
    mh = sha(run / 'manifest.json')
    row('batch manifest sha256 = C8_result.json source_manifest_sha256', mh[:16], data_result['source_manifest_sha256'][:16],
        mh == data_result['source_manifest_sha256'])
    plan_copy = EV / 'production/plan/prplan.570722.0/manifest.json'
    row('batch manifest = the plan job\'s copy shipped with the code', sha(plan_copy)[:16], mh[:16], sha(plan_copy) == mh)
    # the package's own campaign check: pinned tools, inputs manifest, small inputs, cost model, vendored assembly pins
    try:
        m, inputs, mh2, changes = prod.verify_base(run, check_executable=False, accept_tool_change=False, vendored=True)
        ok, note = (mh2 == mh and not changes), f'{len(m["tool_sha256"])} pinned tools, inputs {m["inputs_manifest_sha256"][:12]}, cost model {m["cost_model_sha256"][:12]}'
    except Exception as e:  # noqa: BLE001
        m, ok, note = load(run / 'manifest.json'), False, str(e)
    row('production.verify_base (tools, inputs, cost model, vendored assembly as pinned by the plan)', 'pass' if ok else 'fail',
        'pass', ok, note)
    # groups: configs at their manifest pins; merged records against plan, config and their own payload hash
    ar = {s: {t: {} for t in asm.CAMPAIGNS} for s in asm.SECTORS}
    groups, seeds, bad, merged_sha = {}, [], [], {}
    blocks = thread_s = 0.0
    for g in m['groups']:
        try:
            p, cfg = prod.group_of(run, m, g['name'])
        except Exception as e:  # noqa: BLE001
            bad.append(f'{g["name"]} config: {e}')
            continue
        d = load(p / 'merged.json')
        merged_sha[g['name']] = sha(p / 'merged.json')
        if (d.get('schema') != prod.MERGED_SCHEMA or d.get('complete') is not True or d.get('manifest_sha256') != mh
                or d.get('config_hash') != object_hash(cfg) or (d.get('sector'), d.get('L'), d.get('campaign')) != (cfg['sector'], cfg['L'], cfg['campaign'])
                or d.get('rates_identity') != m['rates_identity'] or d.get('numerics') != m['numerics']):
            bad.append(g['name'] + ' identity')
        if object_hash({k: v for k, v in d.items() if k != 'payload_sha256'}) != d.get('payload_sha256'):
            bad.append(g['name'] + ' payload')
        if len(d['batches']) != cfg['replicates'] or d.get('replicates') != cfg['replicates']:
            bad.append(g['name'] + ' replicates')
        x = np.asarray(d['batches'], float)
        if x.shape != (cfg['replicates'], 2 * (9 - cfg['L'])):
            bad.append(g['name'] + ' shape')
        if merged_sha[g['name']] != data_result['merged_sha256'].get(g['name']):
            bad.append(g['name'] + ' merged sha256 vs C8_result.json')
        ar[cfg['sector']][cfg['campaign']][cfg['L']] = x
        groups[(cfg['campaign'], cfg['sector'], cfg['L'])] = cfg.get('graph_points') or {}
        seeds.append(cfg['seed'])
        blocks += d['blocks']
        thread_s += d['thread_seconds_sum']
    row(f'{len(m["groups"])} group configs and merged records verify (pins, identity, payload hash, shape, C8_result binding)',
        f'{len(bad)} bad', '0 bad', not bad and len(groups) == 24, ', '.join(bad[:5]))
    row('graph_replicates/tails/costs.csv of each group (sha256 pinned in merged.json)', 'hosted', 'not needed here', True,
        'replay-tails verifies them (production.validate_merged) after fetch-data', status='SKIP')
    # coverage: every group's graph set equals the inputs inventory, every count = bundle count x s
    try:
        bundle = prod.design_bundle(run, m)
        cov = asm.coverage_guard(groups, prod.verified_inventory(m), 8, bundle, m['design']['s'], meta_sha256=m['design']['meta_sha256'])
        row('coverage guard (24 groups, inventory graph sets, design bundle counts x s)', f'{cov["graphs"]} graph-campaigns',
            '48,346 graph-campaigns', cov['graphs'] == 2 * 24173, f'bundle design_meta {m["design"]["meta_sha256"][:12]}')
    except Exception as e:  # noqa: BLE001
        row('coverage guard (24 groups, inventory graph sets, design bundle counts x s)', 'fail', 'pass', False, str(e))
    # 1. the assembly, as tools/assemble.py evaluate() does it -> C8_result.json
    r = asm.combine(ar, 8, data_result['bootstrap']['replicates'])
    asm.check_combination(r)
    r.update(source_manifest_sha256=mh, merged_sha256=merged_sha, backend=m['backend'], build=m['build'],
             test_only=m['test_only'], allocation=m.get('allocation'), final=not m['test_only'],
             numerics=m.get('numerics', 'exact'), rates_identity=m.get('rates_identity', 'default'))
    compare_results('recombined assembly (tools/assemble.combine, 4,096 draws) = data C8_result.json', r, data_result)
    # 2. the combination of the K = 1 planned batches, as tools/combine.py does it -> C8_final.json
    batch = dict(label=run.name, design_sha256=m['design']['meta_sha256'], planned=int(m['design']['batches']),
                 inputs_manifest_sha256=m['inputs_manifest_sha256'], numerics=m.get('numerics', 'exact'),
                 rates_identity=m.get('rates_identity', 'default'), seeds=seeds, ar=ar)
    f = cb.combine_batches([batch], batch['planned'], False, final['bootstrap']['replicates'])
    compare_results('recombined combination (tools/combine.combine_batches, K = 1, 1,024 draws) = results C8_final.json', f, final)
    for label, rec in (('results C8_final.json', final), ('data C8_result.json', data_result),
                       ('results pilot/C8_result.json', load(res / 'pilot/C8_result.json'))):
        probs = vr.verify(rec)
        row(f'tools/verify_result.py on {label}', f'{len(probs)} problems', '0 problems', not probs, '; '.join(probs[:3]))
    return m, r, f, final, data_result, blocks, thread_s


def identities(run: Path, res: Path, shared: Path):
    pairs = [(res / 'C8_final.json', EV / 'production/result/batch_copy/C8_final.json', 'b14da47c312e'),
             (run / 'C8_result.json', EV / 'production/result/batch_copy/C8_result.json', '9383ab814726'),
             (res / 'pilot/C8_result.json', EV / 'pilot/analysis/pilot_copy/C8_result.json', None),
             (res / 'production/analysis.json', EV / 'production/result/prres.571287.0/analysis.json', None),
             (res / 'production/accounting.json', EV / 'production/result/prres.571287.0/accounting.json', None),
             (res / 'production/tails.csv.gz', EV / 'production/result/prres2.571296.0/tails.csv.gz', None)]
    for name in ('cert_summary', 'dl_targeted', 'nested_split', 'ab_hill'):
        pairs.append((res / f'tailcheck/{name}.json', EV / f'production/tailcheck/results/{name}.json', None))
    pairs += [(res / 'tailcheck/cert_check.json', EV / 'production/tailcheck/evidence/tc2cert.571402.0/cert_check.json', None),
              (res / 'tailcheck/negctl_check.json', EV / 'production/tailcheck/evidence/tc2neg.571403.0/negctl_check.json', None),
              (res / 'tailcheck/nested_joint.json', EV / 'production/tailcheck/evidence/tc2an.571406.0/nested_joint.json', None)]
    bad = []
    for a, b, pre in pairs:
        if sha(a) != sha(b) or (pre and not sha(a).startswith(pre)):
            bad.append(a.name)
    row(f'{len(pairs)} published records equal their copies in the code\'s evidence (C8_final b14da47c, C8_result 9383ab81)',
        f'{len(bad)} differ', '0 differ', not bad, ', '.join(bad))
    tails_raw = hashlib.sha256(gzip.open(res / 'production/tails.csv.gz').read()).hexdigest()
    row('production tail table: sha256 of the decompressed tails.csv = the BeeGFS original (large_files.sha256)', tails_raw[:16],
        '8039682a7601213b', tails_raw.startswith('8039682a7601213b'))
    # the vendored order-8 assembly is the shared one, byte for byte
    vend = sorted(p.relative_to(PKG / 'vendor/c8_assembly').as_posix() for p in (PKG / 'vendor/c8_assembly').rglob('*') if p.is_file())
    diff = [n for n in vend if not (shared / 'assembly' / n).is_file() or sha(shared / 'assembly' / n) != sha(PKG / 'vendor/c8_assembly' / n)]
    row(f'vendor/c8_assembly ({len(vend)} files) = ../LRI_C8_shared/assembly byte for byte', f'{len(diff)} differ', '0 differ',
        not diff and sha(PKG / 'vendor/c8_assembly/HANDOFF_assembly.json').startswith('f5ff6a353371'), ', '.join(diff[:4]) or 'HANDOFF_assembly.json f5ff6a35')
    pin = sha(shared / 'inventory/inventory8_d2/MANIFEST.json')
    im = load(PKG / 'inputs/manifest.json')
    row('shared inventory MANIFEST.json sha256 = the pin in inputs/manifest.json (C8_H1_PIN)', pin[:16], im['inventory8_d2_manifest_sha256'][:16],
        pin == im['inventory8_d2_manifest_sha256'] == '46341a3c0f11d74f0cf7c08cdd685d9cf073a142160de5a0ca408e021b4ff099')


# ---------------------------------------------------------------------------------------------------------------------
def quoted_numbers(m, r, f, final, data_result, blocks, thread_s, run: Path, res: Path, shared: Path, c6, c7):
    # Section 1 (note l.104, l.130, l.137-141) and Section 31.1 (l.11581-11605)
    quoted('C8(2) underlying estimator (Sec 1 table; published record, which the recombination reproduces)', final['C8_full'], '45990.00263614446',
           f'recombined here: {f["C8_full"]!r} (relative {abs(f["C8_full"] / final["C8_full"] - 1):.0e})')
    quoted('C8(2) sampling SE (Sec 1 table)', f['sampling_standard_error'], '8.216820958')
    for name, v, t in (('power-free C8^pf(2)', f['power_free_C8'], '45991.2684796'), ('its SE', f['power_free_se'], '7.6797436'),
                       ('power correction Delta_p C8(2)', f['power_correction'], '-1.2658435'), ('its SE', f['power_correction_se'], '2.9224044'),
                       ('complete C8(2)', f['C8_full'], '45990.0026361'), ('its SE', f['sampling_standard_error'], '8.2168210')):
        quoted(f'Sec 31.1 table: {name}', v, t)
    se = f['sampling_standard_error']
    quoted('allowance: 4 sigma', 4 * se, '32.87')
    dev = [abs(h[8] - f['C8_full']) for h in f['half_streams']]
    quoted('half-stream deviation (largest)', max(dev), '2.39'); quoted('half-stream deviation (smallest)', min(dev), '2.39')
    row('4 sigma exceeds both half-stream deviations', f'{4 * se:.2f} > {max(dev):.2f}', 'true', 4 * se > max(dev))
    allowance = math.ceil(4 * se)
    row('allowance = 4 sigma rounded up to a multiple of 1 (two significant figures)', allowance, 33, allowance == 33)
    quoted('reported value (boxed eq. c8d2:reported, Sec 1, abstract)', f['C8_full'], '45990')
    p = load(res / 'pilot/C8_result.json')
    quoted('exact-path pilot', p['C8_full'], '45620'); quoted('pilot SE', p['sampling_standard_error'], '214')
    quoted('pilot vs production (combined SE)', abs(pull(f['C8_full'], se, p['C8_full'], p['sampling_standard_error'])), '1.73')
    lo = {c['order']: c for c in f['lower_order_checks']}
    C = {3: lo[3]['reference'], 4: lo[4]['reference'], 5: lo[5]['reference'], 6: c6['C6'], 7: c7['C7_full'], 8: f['C8_full']}
    for n, t in ((8, '-11.86'), (4, '-5.77'), (5, '-7.69'), (6, '-9.33'), (7, '-10.70')):
        quoted(f'ratio C{n}(2)/C{n - 1}(2)', C[n] / C[n - 1], t)
    # Section 31.2: inputs, assembly, inventory
    tl = load(PKG / 'inputs/two_loop.json')['B2'][6]
    pre = '-266.52096796135938173225219261908980094902'
    row('b_{2,6} (inputs/two_loop.json, quoted digits)', tl[:len(pre)], pre, tl.startswith(pre))
    ext = load(PKG / 'inputs/verification/two_loop_extension8.json')
    quoted('two 75-digit Cauchy contours agree to', float(ext['max_two_contour_difference']), '3.1e-66')
    quoted('130-digit series confirms the stored value to', float(ext['max_stored_vs_reference']), '7.7e-68')
    l2 = load(PKG.joinpath('benchmarks/expanse_2026-10-c8/stage3/s3val3.54637264.0/l2_control.json'))['tests'][0]
    mp = max(abs(v) for b in l2['backends'].values() for s in b['slots'] for v in s['pulls'].values())
    quoted('two-loop control graph reproduces b_2 within (SE; job 54637264)', mp, '1.22')
    ec = load(PKG / 'vendor/c8_assembly/exact_check_results.json')['float_vs_exact_order8']
    row('assembly: random eighth-order cases', ec['cases'], 64, ec['cases'] == 64)
    quoted('assembly: float vs exact inversions (of the coefficient scale)', ec['max_relative_error'], '7.0e-16')
    g = f['gates']
    dev7 = g['loop7']['rel_deviation']
    row('gates: loop-7 derivatives exact to (relative)', f'{dev7:.1e}', '< 6e-16', dev7 < 6e-16)
    sel = load(shared / 'inventory/inventory8_d2/selection.json')['coverage_partition']
    inv8 = load(shared / 'inventory/inventory8_d2/inventory_L8.json'); inv7 = load(shared / 'inventory/inventory8_d2/inventory_L7.json')
    inputs_inv = load(PKG / 'inputs/inventory.json')
    for L, invL in ((7, inv7), (8, inv8)):
        fr = invL['free']; pw = invL['power']
        allc, powc = len(fr), sum(r['status'] == 'power-sector-not-integrated' for r in fr)
        nz = sum(r['status'] == 'finite-kernel' for r in pw)
        want = {7: (3986, 1091, 709, 2441, 709), 8: (26540, 7231, 4891, 16064, 4336)}[L]
        got = (allc, powc, nz, len(inputs_inv['free'][str(L)]), len(inputs_inv['power'][str(L)]))
        row(f'inventory table, L = {L} (classes, power-containing, nonzero mixed, integrated pf, integrated power)', got, want, got == want)
    for L, want in ((3, (8, 1, 1, 5, 1)), (4, (27, 5, 3, 16, 3)), (5, (129, 31, 20, 76, 20)), (6, (660, 173, 107, 395, 107))):
        rows = load(ref_path(f'power_mass/inputs/L{L}/inventory.json'))
        got = (len(rows), sum(r['status'] != 'not-power' for r in rows), sum(r['status'] == 'finite-kernel' for r in rows),
               len(inputs_inv['free'][str(L)]), len(inputs_inv['power'][str(L)]))
        row(f'inventory table, L = {L}', got, want, got == want)
    fr8 = {r['id']: r for r in inv8['free']}; pw8 = {r['id']: r for r in inv8['power']}
    fin = lambda i: fr8[i]['status'] == 'finite-kernel' or pw8[i]['status'] == 'finite-kernel'  # noqa: E731
    zc = sum(r['mass_numerator'] == 4 for r in fr8.values())
    zm = sum(1 for i, r in fr8.items() if r['mass_numerator'] != 4 and not fin(i))
    selL8 = load(shared / 'inventory/inventory8_d2/selection.json')['L8']
    prim = sum(fr8[int(i)]['primitive'] for i in selL8['free'])
    got = (zc, zm, len(selL8['free']) - prim, prim, len(selL8['power']))
    want = (2254, 3886, 15816, 248, 4336)
    row('L8: 3w_B-w_A=0 classes, vanishing mixed map, integrated nonprimitive/primitive/power', got, want,
        got == want and got == tuple(sel['8'][k] for k in ('zero_channel_weight', 'zero_mixed_forest_kernel_at_nonzero_weight',
                                                          'retained_powerfree_nonprimitive', 'retained_primitive', 'new_power_containing')))
    s7 = sel['7']; got = (s7['retained_powerfree_nonprimitive'], s7['retained_primitive'], s7['new_power_containing'])
    row('L7: integrated nonprimitive, primitive, power-containing (3,150)', got, (2397, 44, 709), got == (2397, 44, 709) and sum(got) == 3150)
    nk = sum(len(v) for s in inputs_inv.values() for v in s.values())
    row('kernels integrated (inputs/inventory.json)', nk, 24173, nk == 24173)
    l8rows = inputs_inv['free']['8'] + inputs_inv['power']['8']
    row('largest eight-loop kernel: complement-of-tree monomials, forest terms', (max(x['monomials'] for x in l8rows), max(x['terms'] for x in l8rows)),
        (4032, 280), (max(x['monomials'] for x in l8rows), max(x['terms'] for x in l8rows)) == (4032, 280))
    ez = (sum(r['status'] == 'exact-zero-kernel' for r in inv8['free']), sum(r['status'] == 'exact-zero-kernel' for r in inv8['power']))
    row('exactly vanishing eight-loop kernels (power-free, power)', ez, (2511, 2340), ez == (2511, 2340))
    gt = shared / 'inventory/inventory8_d2/gates'
    ef = load(gt / 'g_edge_forests.json')['per_loop']; kf = load(gt / 'k_forests.json')['per_loop']; kh = load(gt / 'h_kirchhoff.json')
    got = (ef['L7']['graphs'], ef['L8']['graphs'], kh['count'], kf['L8']['total'])
    row('independent rederivations: edge forests L7/L8, Kirchhoff kernels, compatible log forests (gate records)', got,
        (1091, 7231, 144, 11254373), got == (1091, 7231, 144, 11254373) and kh['passed'] and load(gt / 'g_edge_forests.json')['passed'])
    # Section 31.3: pilot, design, numerics
    pa = EV / 'pilot/analysis/pa.570669.0'
    quoted('pilot cost (core-h; scheduler records)', core_hours(sacct_rows(pa / 'sacct.txt')), '227')
    pm = load(run / 'design_bundle/design_meta.json')
    row('pilot: replicates x points per graph', (pm['pilot']['allocation']['replicates'], pm['pilot']['allocation']['points']), (8, 4096),
        (pm['pilot']['allocation']['replicates'], pm['pilot']['allocation']['points']) == (8, 4096))
    ca, cb_ = p['campaigns']['a'], p['campaigns']['b']
    quoted('pilot campaigns apart (SE)', abs(pull(ca['C8'], ca['sampling_se'], cb_['C8'], cb_['sampling_se'])), '0.64')
    mx = max(p['lower_order_checks'], key=lambda c: abs(c['pull']))
    quoted(f'pilot lower-order pulls at most (at C{mx["order"]})', abs(mx['pull']), '2.11')
    row('largest pilot pull is at C6', mx['order'], 6, mx['order'] == 6)
    pg = load(pa / 'pa_analysis.json')['per_group']; tot = sum(v['row_core_hours'] for v in pg.values())
    cost = lambda s, L: 100 * sum(v['row_core_hours'] for k, v in pg.items() if k.endswith(f'{s}_L{L}')) / tot  # noqa: E731
    quoted('pilot: power-free L7 share of the variance (%)', 100 * p['error_by_loop']['free']['7']['share'], '71')
    quoted('pilot: power-free L7 share of the cost (%)', cost('free', 7), '2.4')
    quoted('pilot: power-free L8 share of the variance (%)', 100 * p['error_by_loop']['free']['8']['share'], '18')
    quoted('pilot: power-free L8 share of the cost (%)', cost('free', 8), '71')
    reps = {load(run / 'groups' / gg['name'] / 'config.json')['replicates'] for gg in m['groups']}
    row('replicates in every campaign, sector and loop', sorted(reps), [128], reps == {128})
    row('Neyman floor: points per graph', pm['parameters']['min_points'], 4096, pm['parameters']['min_points'] == 4096)
    row('target: relative SE, |C8| scale', (pm['target']['rel'], pm['target']['c8_magnitude']), (0.00025, 46000.0),
        (pm['target']['rel'], pm['target']['c8_magnitude']) == (0.00025, 46000.0))
    quoted('predicted SE with the safety factor', pm['predictions']['se_total'], '11.50')
    row('safety factor', pm['parameters']['variance_margin'], 1.5, pm['parameters']['variance_margin'] == 1.5)
    quoted('raw predicted SE', pm['predictions']['se_raw_total'], '7.67')
    mins, samples = None, 0
    for gg in m['groups']:
        cfg = load(run / 'groups' / gg['name'] / 'config.json')
        samples += sum(int(v) for v in cfg['graph_points'].values()) * cfg['replicates']
        if cfg['sector'] == 'free' and cfg['L'] == 8:
            v = min(int(x) for x in cfg['graph_points'].values()); mins = v if mins is None else min(mins, v)
    row('every power-free eight-loop graph has at least (points per replicate)', mins, 32768, mins == 32768)
    row('kernel samples in the batch', samples, 779836456960, samples == 779836456960)
    gate = load(EV / 's6fix4/s4flag.570574.0/jflag_dd+mp256/numerics_flags.json')
    row('numerics gate record sha256 = the one the design bundle pins (42e6d2d8)', sha(EV / 's6fix4/s4flag.570574.0/jflag_dd+mp256/numerics_flags.json')[:12],
        pm['profile_recost']['gates'][0]['sha256'][:12], sha(EV / 's6fix4/s4flag.570574.0/jflag_dd+mp256/numerics_flags.json') == pm['profile_recost']['gates'][0]['sha256'])
    F1 = gate['F1']['total']
    row('(F1) points with 450-digit references', F1['points'], 153600, F1['points'] == 153600 and gate['verdicts']['F1'])
    quoted('(F1) largest error, double-double', float(F1['tiers']['double_double']['max_relative_error']), '5.2e-12')
    quoted('(F1) largest error, binary128', float(F1['tiers']['binary128']['max_relative_error']), '1.4e-11')
    F2 = gate['F2']
    row('(F2) replicates x points; tasks', (F2['replicates'], F2['points'], int(F2['per_task']['normalized']['n'])), (4, 256, 193384),
        (F2['replicates'], F2['points'], int(F2['per_task']['normalized']['n'])) == (4, 256, 193384))
    stat = F2['total']['dC8'] + 3 * F2['total']['se']
    quoted('(F2) |dC8| + 3 SE_d [note prints 4.3e-16: erratum, note_changes.md]', stat, '4.2e-16')
    bound = float(re.search(r'^BOUND_DC8\s*=\s*([0-9.eE+-]+)', (PKG / 'tests/numerics_flags.py').read_text(), re.M).group(1))
    quoted('(F2) bound (tests/numerics_flags.py BOUND_DC8: 1% of the SE at the tightest target)', bound, '0.062')
    quoted('(F2) per-task normalized differences at most', F2['per_task']['normalized']['max'], '5.6e-14')
    row('(F5) identical at 1, 8, 16, 64 threads and 8 lanes of 8', gate['F5']['threads'] + [gate['F5']['lanes']], [1, 8, 16, 64, '8x8'],
        gate['F5']['passed'] and gate['F5']['threads'] == [1, 8, 16, 64])
    row('(F4) eight-loop sample free/power', (gate['F4']['sample']['free'], gate['F4']['sample']['power']), (1600, 400),
        (gate['F4']['sample']['free'], gate['F4']['sample']['power']) == (1600, 400))
    sp = gate['F4']['speedup_exact_over_profile']['total']
    row('(F4) profile speed over the exact path at eight loops ("about 2.5 times")', f'{sp:.3f}', '2.5 +- 0.1', abs(sp - 2.5) < 0.1)
    rb = pm['route_b_choice']['kept_exact_allocation']
    quoted('route (b) cost / exact path at the same target', rb['cost_total_core_hours'] / rb['exact_cost_total_core_hours'], '0.37')
    skip('exact path replays (3,773 kernels bit for bit, 1,600 + 400 L8 sample, 2^32 operand pairs)',
         'native validation runs (make test-full on a cluster; records under benchmarks/*/s6fix3, stage4b); not recomputable here')
    # Section 31.4: production
    rows = sacct_rows(EV / 'production/result/prres.571287.0/sacct.txt')
    lanes = [x for x in rows if x['JobName'] == 'c8d2-lanes' and int(x['ElapsedRaw'] or 0) > 0]
    r1 = [int(x['ElapsedRaw']) / 3600 for x in lanes if x['Submit'] < '2026-10-07']
    r2 = [int(x['ElapsedRaw']) / 3600 for x in lanes if x['Submit'] >= '2026-10-07']
    row('nodes in round 1 / round 2', (len(r1), len(r2)), (8, 6), (len(r1), len(r2)) == (8, 6))
    cv, ri = load(run / 'cpu_vendor.json'), load(run / 'runtime_identity.json')
    row('CPU of every claim (the campaign\'s vendor pin)', cv['model_name'], 'AMD EPYC 7543 32-Core Processor', cv['model_name'] == 'AMD EPYC 7543 32-Core Processor')
    row('one runtime identity (the campaign\'s pin; the node survey key)', ri['key'][:12], '04f1e51dfc2e', ri['key'].startswith('04f1e51dfc2e'))
    quoted('round 1 shortest worker (h)', min(r1), '22.4'); quoted('round 1 longest worker (h)', max(r1), '23.0')
    quoted('round 2 shortest worker (h)', min(r2), '4.4'); quoted('round 2 longest worker (h)', max(r2), '5.6')
    row('work indices, tasks, checkpoint blocks (plan)', (m['scale']['jobs'], m['scale']['tasks'], m['scale']['checkpoints']),
        (1129, 6192256, 24848), (m['scale']['jobs'], m['scale']['tasks'], m['scale']['checkpoints']) == (1129, 6192256, 24848))
    row('checkpoint blocks committed (sum of merged.json blocks)', int(blocks), 24848, int(blocks) == 24848)
    t0 = min(dt.datetime.fromisoformat(x['Submit']) for x in lanes)
    t1 = max(dt.datetime.fromisoformat(x['End']) for x in rows if x['State'] == 'COMPLETED')
    quoted('hours from submission to the final merge', (t1 - t0).total_seconds() / 3600, '28.7')
    ch = core_hours(rows)
    quoted('allocated core-hours (scheduler records)', ch, '13454')
    quoted('cost / design estimate', ch / pm['predictions']['cost_total_core_hours'], '0.93')
    acc = load(res / 'production/accounting.json')
    quoted('allocated core-hours = accounting.json (tools/accounting.py)', acc['allocated_core_hours'], f'{ch:.2f}')
    quoted('busy thread core-hours (sum of merged.json thread_seconds_sum) = accounting.json', thread_s / 3600, f'{acc["busy_thread_core_hours"]:.2f}')
    skip('about 1.6e4 core-hours with development, pilot and tail diagnostics',
         'development accounting is in the plan log (not shipped); shipped parts: pilot 227 + production 13,454 + tail checks 70')
    for t, v, s in (('a', '45993.58', '12.15'), ('b', '45986.42', '11.06')):
        quoted(f'campaign {t}', f['campaigns'][t]['C8'], v); quoted(f'campaign {t} SE', f['campaigns'][t]['sampling_se'], s)
    quoted('first half stream', f['half_streams'][0][8], '45987.61'); quoted('second half stream', f['half_streams'][1][8], '45992.39')
    quoted('combined (table)', f['C8_full'], '45990.00'); quoted('combined SE (table)', se, '8.22')
    quoted('campaigns differ by (combined SE)', abs(pull(f['campaigns']['a']['C8'], f['campaigns']['a']['sampling_se'],
                                                        f['campaigns']['b']['C8'], f['campaigns']['b']['sampling_se'])), '0.44')
    table = {'free': ('0.01', '0.07', '0.22', '0.65', '3.67', '6.71'), 'power': ('0.00', '0.01', '0.11', '0.43', '1.02', '2.70')}
    for s, vals in table.items():
        for L, t in zip(range(3, 9), vals):
            quoted(f'SE contribution, {s} L = {L}', f['error_by_loop'][s][str(L)]['se'], t)
    quoted('realized SE / raw design prediction', se / pm['predictions']['se_raw_total'], '1.07')
    an = load(res / 'production/analysis.json')['variance']['strata']
    rat = [r['error_by_loop'][s][str(L)]['variance'] / an[f'{s}_L{L}']['predicted_variance_from_pilot_sigma'] for s in ('free', 'power') for L in (7, 8)]
    quoted('per-stratum realized/predicted variance at L7, L8: smallest', min(rat), '0.98', 'prediction from analysis.json (pilot sigma; replay-tails recomputes it)')
    quoted('per-stratum realized/predicted variance at L7, L8: largest', max(rat), '1.32')
    # Section 31.5: tails
    by = {}
    with gzip.open(res / 'production/tails.csv.gz', 'rt') as fh:
        for x in csv.DictReader(fh):
            if x['L'] == '8' and x['status'] == 'defined':
                by.setdefault((x['sector'], int(x['graph'])), {})[x['campaign']] = (int(x['points']), float(x['xi_hat']))
    import design  # the package's rule constants
    conf = {'free': 0, 'power': 0}
    for (s, _), v in by.items():
        if min(v['a'][0], v['b'][0]) >= design.CONFIRM_POINTS and (v['a'][1] + v['b'][1]) / 2 > design.XI_CONFIRM_MEAN:
            conf[s] += 1
    row('rule: k, confirmation points, two-campaign mean threshold', (design.HILL_K, design.CONFIRM_POINTS, design.XI_CONFIRM_MEAN),
        (16, 32768, 0.44), (design.HILL_K, design.CONFIRM_POINTS, design.XI_CONFIRM_MEAN) == (16, 32768, 0.44))
    row('confirmed eight-loop graphs (all, power-free, power)', (sum(conf.values()), conf['free'], conf['power']), (4832, 4631, 201),
        (sum(conf.values()), conf['free'], conf['power']) == (4832, 4631, 201), 'recounted from tails.csv.gz')
    th = load(res / 'production/analysis.json')['tails']
    row('analysis.json confirmed count = recount', th['production_confirmed_total'], sum(conf.values()), th['production_confirmed_total'] == sum(conf.values()))
    share = th['threat']['free_L8']['confirmed_share_of_C8_variance'] + th['threat']['power_L8']['confirmed_share_of_C8_variance']
    quoted('their share of Var C8(2) (%) [note prints 27.5: erratum, note_changes.md]', 100 * share, '27.6')
    quoted('largest single graph-campaign share (%)', 100 * th['threat']['free_L8']['largest_single_graph_campaign_share_of_C8_variance_any_L8'], '0.08')
    cs, cc = load(res / 'tailcheck/cert_summary.json'), load(res / 'tailcheck/cert_check.json')
    nsub = sum(v['series_subsets'] for v in cs['per_sector_L'].values()); ng = sum(v['graphs'] for v in cs['per_sector_L'].values())
    row('verification: expanded subsets, kernels', (nsub, ng), (3959753, 24173), (nsub, ng) == (3959753, 24173) and cc['passed'])
    row('verification: primes per graph, points per prime', (cc['primes_per_graph'], cc['points_per_prime']), (4, 2), (cc['primes_per_graph'], cc['points_per_prime']) == (4, 2))
    row('verification: union bound on any wrong valuation', f'1e{cc["log10_error_bound_union"]:.2f}', '< 1e-53', cc['log10_error_bound_union'] < -53)
    neg = load(res / 'tailcheck/negctl_check.json')
    row('archived controls behave as asserted', (neg['controls'], neg['all_passed']), (9, True), neg['controls'] == 9 and neg['all_passed'])
    mm = cc['min_margins_L7_L8']
    got = (mm['min_bound_margin_a'], mm['min_bound_margin_b'], mm['min_second_margin_a'], mm['min_second_margin_b'])
    row('margins m - rho alpha (a, b) and 2m - rho alpha (a, b), L7/L8', got, (0.1, 0.05, 0.6, 0.55), all(abs(x - y) < 1e-9 for x, y in zip(got, (0.1, 0.05, 0.6, 0.55))))
    unb = sum(v['graphs'] - v['bounded_both_rates'] for v in cs['per_sector_L'].values())
    row('unbounded weights of finite variance (free L5/L6, legacy rate tables)', unb, 17, unb == 17)
    tc = cs['L8_by_tail_class']
    row('median forest terms, confirmed vs cleared power-free', (tc['free confirmed']['terms_median'], tc['free cleared']['terms_median']), (128.0, 16.0),
        (tc['free confirmed']['terms_median'], tc['free cleared']['terms_median']) == (128.0, 16.0))
    nj = load(res / 'tailcheck/nested_joint.json')['classes']
    hx = [v['hill_exponent_W0']['value'] for v in nj.values()]
    quoted('Hill log-log slopes: lowest', min(hx), '-0.34'); quoted('Hill log-log slopes: highest', max(hx), '-0.17')
    for cls, n, v, lo_, hi in (('confirmed free L8', 16, '-0.018', '-0.051', '+0.030'), ('confirmed power L8', 8, '-0.062', '-0.110', '+0.060')):
        c = nj[cls]
        row(f'nested test, {cls}: graphs', c['graphs'], n, c['graphs'] == n)
        quoted(f'nested slope, {cls}', c['slope_C8_W0']['value'], v)
        quoted(f'95% interval low, {cls}', c['slope_C8_W0']['ci95'][0], lo_); quoted(f'95% interval high, {cls}', c['slope_C8_W0']['ci95'][1], hi)
    dl = load(res / 'tailcheck/dl_targeted.json')
    row('double-lift power L8 graphs', dl['double_lift_graphs'], 380, dl['double_lift_graphs'] == 380)
    quoted('their share of the measured variance (%)', 100 * dl['measured_share_of_var_C8'], '0.058')
    row('targeted test: largest contributors', dl['targeted']['graphs'], 16, dl['targeted']['graphs'] == 16)
    quoted('their share of the class variance (%)', 100 * dl['targeted']['class_fraction'], '52')
    for k, t in ((18.9, '8.26'), (45, '8.32'), (335, '8.97')):
        k_exact = dl['earlier_sample']['F']['value'] if k == 18.9 else k
        sek = se * math.sqrt(1 + (k_exact - 1) * dl['measured_share_of_var_C8'])
        quoted(f'SE if the class variance were x{k} (recomputed)', sek, t)
    quoted('inflation factor of the earlier sample', dl['earlier_sample']['F']['value'], '18.9')
    # Section 31.6: lower-order checks
    for c, (e, s, pl) in zip(f['lower_order_checks'], (('-0.8748487258', '1.24e-6', '+1.04'), ('5.0489759126', '6.80e-5', '+1.58'),
                                                       ('-38.8332791554', '9.37e-4', '+0.39'), ('362.3625083', '0.0116244', '-0.34'),
                                                       ('-3875.545222', '0.289774', '+0.97'))):
        n = c['order']
        quoted(f'C{n} by-product', c['estimate'], e); quoted(f'C{n} SE', c['sampling_se'], s)
        quoted(f'C{n} pull (both SEs)', pull(c['estimate'], c['sampling_se'], c['reference'], c['reference_se']), pl)
    quoted('sum of squared pulls', sum(pull(c['estimate'], c['sampling_se'], c['reference'], c['reference_se']) ** 2 for c in f['lower_order_checks']), '4.78')
    for n, text in ((3, '-0.874850012653'), (4, '5.048868431'), (5, '-38.833645896')):
        quoted(f'C{n} reference used = the Sec 1 closed-form value (13-digit archived value, printed digits)', lo[n]['reference'], text)
        row(f'C{n} reference SE', lo[n]['reference_se'], 0.0, lo[n]['reference_se'] == 0.0)
    for n, label, ref, rse in ((6, 'results/C6_2/C6_result.json', c6['C6'], c6['sampling_standard_error']),
                               (7, 'results/C7_2/C7_result.json', c7['C7_full'], c7['sampling_standard_error'])):
        c = lo[n]
        row(f'C{n} reference and SE used = {label}', (c['reference'], c['reference_se']), (ref, rse), (c['reference'], c['reference_se']) == (ref, rse))
    nulls = {x['order']: x for x in f['power_null_checks']['null_rows']}
    for n, d_, s_ in ((4, '1.37e-6', '4.03e-6'), (5, '7.7e-5', '2.35e-4'), (6, '2.28e-3', '4.86e-3'), (7, '2.54e-2', '9.00e-2')):
        quoted(f'power null row, order {n}', nulls[n]['delta'], d_)
        quoted(f'power null row, order {n}, SE', nulls[n]['se'], s_)
    quoted('largest |pull| of the null rows', max(abs(nulls[n]['pull']) for n in (4, 5, 6, 7)), '0.47')
    row('order-3 power difference vanishes by the weights', nulls[3]['delta'], 0.0, nulls[3]['delta'] == 0.0)
    quoted('eighth-order power correction', f['power_correction'], '-1.27'); quoted('its SE', f['power_correction_se'], '2.92')
    quoted('bootstrap SE (4,096 resamples; C8_result.json)', r['bootstrap']['full_se'][8], '8.09')
    row('bootstrap resamples (assembly)', r['bootstrap']['replicates'], 4096, r['bootstrap']['replicates'] == 4096)
    quoted('seventh-order by-product', f['coefficients'][7], '-3875.55'); quoted('its SE', f['standard_errors'][7], '0.29')


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--data', type=Path, default=PKG / '../../data/C8_2')
    ap.add_argument('--results', type=Path, default=PKG / '../../results/C8_2')
    ap.add_argument('--shared', type=Path, default=PKG / '../LRI_C8_shared')
    ap.add_argument('--c6', type=Path, default=PKG / '../../results/C6_2/C6_result.json')
    ap.add_argument('--c7', type=Path, default=PKG / '../../results/C7_2/C7_result.json')
    ap.add_argument('--out', type=Path, default=PKG / 'public/out')
    a = ap.parse_args()
    run, res, shared = (a.data / RUN_NAME).resolve(), a.results.resolve(), a.shared.resolve()
    m, r, f, final, data_result, blocks, thread_s = recombine(run, res)
    identities(run, res, shared)
    quoted_numbers(m, r, f, final, data_result, blocks, thread_s, run, res, shared, load(a.c6), load(a.c7))
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / 'replay.json').write_text(json.dumps(dict(numpy=np.__version__, python=sys.version.split()[0], rows=ROWS), indent=1, default=str) + '\n')
    w = min(100, max(len(x['check']) for x in ROWS))
    for x in ROWS:
        print(f"{x['status']:4}  {x['check']:<{w}}  {x['got']!s:>16}  (expected {x['expected']})" + (f"  {x['note']}" if x['note'] else ''))
    n = {s: sum(x['status'] == s for x in ROWS) for s in ('PASS', 'FAIL', 'SKIP')}
    print(f"\n{n['PASS']} PASS, {n['FAIL']} FAIL, {n['SKIP']} SKIP (numpy {np.__version__}, Python {sys.version.split()[0]})")
    return 1 if n['FAIL'] else 0


if __name__ == '__main__':
    sys.exit(main())
