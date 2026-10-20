#!/usr/bin/env python3
"""Stage 4b, G4b: recompute the verdicts and key numbers of the final J-VAL-2/J-VAL-3 from the records copied into
benchmarks/expanse_2026-10-c8/stage4b/final/ (one directory per job), and compare every record with its Stage-3
counterpart on the Stage-3 baseline (jobs 54637263 and 54637264; merge scale 54643361; assembly 54633368).
Standard library only; run from the repository root:
  python3 -B benchmarks/expanse_2026-10-c8/stage4b/final/scripts/summarize_final.py [--write]
With --write the summary goes to stage4b/final/final_summary.json. Exit 1 if any gate fails.
A record's status is accepted only together with the coverage its tool recomputes from it (Stage-6 fix rounds 3 and 4:
forced_tiers Z2, quad_differential W1, thread_identity W22, and validate.coverage for J-VAL-2, G-BK8, G-L8SELF and
A-IN-6b), since a restricted run can say "passed".

The Stage-3 comparison removes the fields that legitimately differ between two runs or two builds (wall and integration
seconds, the environment block, compile and harness commands with their paths, output-file sha256s that include those
seconds, the executables' own digests, and the record field 'executed' that validate.py gained after Stage 3), matches
the tests of a record by their identifying fields, lists the test kinds added after Stage 3 (they have no Stage-3
counterpart), and then requires the rest to be equal. The merge-scale throughputs and RSS are
measurements, so only their pass/fail verdicts are compared.
"""
from __future__ import annotations
import argparse, glob, json, re, sys
from pathlib import Path

ROOT = Path.cwd(); F = ROOT / 'benchmarks/expanse_2026-10-c8/stage4b/final'
S3 = ROOT / 'benchmarks/expanse_2026-10-c8/stage3'
VOLATILE = {'wall_seconds', 'environment', 'seconds', 'integration_seconds', 'compile_command', 'reference_worker_command',
            'harness_command', 'tool_command', 'command', 'commands', 'candidate', 'baseline', 'sha256', 'host', 'hostname',
            'max_rss_kb', 'scratch', 'output', 'path', 'paths', 'elapsed', 'timing', 'timings', 'cpus', 'lane_cpus',
            'c8_binaries'}


def load(p): return json.loads(Path(p).read_text())


def one(pattern):
    m = sorted(glob.glob(str(F / pattern)))
    if len(m) != 1: raise SystemExit(f'expected one {pattern} under {F}, found {m}')
    return Path(m[0])


def strip(x):
    if isinstance(x, dict):
        return {k: strip(v) for k, v in x.items() if k not in VOLATILE and not k.endswith('_seconds') and not k.endswith('_s')}
    if isinstance(x, list): return [strip(v) for v in x]
    if isinstance(x, str) and re.search(r'/expanse/|/scratch/|/home/', x): return '<path>'
    return x


def diff(a, b, path='', out=None, limit=40):
    out = [] if out is None else out
    if len(out) >= limit: return out
    if type(a) != type(b): out.append(f'{path}: type {type(a).__name__} != {type(b).__name__}')
    elif isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b: out.append(f'{path}/{k}: only in {"new" if k in a else "stage3"}')
            else: diff(a[k], b[k], f'{path}/{k}', out, limit)
    elif isinstance(a, list):
        if len(a) != len(b): out.append(f'{path}: {len(a)} != {len(b)} items')
        for i, (u, v) in enumerate(zip(a, b)): diff(u, v, f'{path}[{i}]', out, limit)
    elif a != b: out.append(f'{path}: {str(a)[:80]} != {str(b)[:80]}')
    return out


def _module(name):
    """tests/<name>.py loaded from this checkout (the acceptance rules live with the tools that write the records)."""
    import importlib.util as iu
    for d in ('tools', 'tests'):
        if str(ROOT / d) not in sys.path: sys.path.insert(0, str(ROOT / d))
    if name in sys.modules: return sys.modules[name]
    spec = iu.spec_from_file_location(name, ROOT / f'tests/{name}.py'); m = iu.module_from_spec(spec); sys.modules[name] = m; spec.loader.exec_module(m)
    return m


def _verdict(rec, cov):
    good = rec.get('status') == 'passed' and cov['complete']
    return ('passed' if good else f'FAILED (status {rec.get("status")!r}; coverage: {"; ".join(cov["why"])[:300]})'), cov


def forced_tiers_verdict(ft):
    """Stage-6 fix round 3 (Z2, S6A3-02): a forced_tiers record is accepted only with its status 'passed' AND the
    coverage tests/forced_tiers.py's coverage() recomputes from the record (scale 1, the prescribed sample, both
    sectors, the quotas, the graphs and points per (sector, L), no violation); the status alone could come from a
    --sectors subset. The records summarized here predate the Z1 source binding, so that one condition is not required
    (source_binding=False; tests/forced_tiers.py --check, the acceptance check of new records, requires it).
    (verdict, coverage)."""
    return _verdict(ft, _module('forced_tiers').coverage(ft, source_binding=False))


def quad_differential_verdict(qd):
    """Stage-6 fix round 4 (W1, S6A4-01): a quad_differential record is accepted only with its status 'passed' AND
    tests/quad_differential.py's coverage() recomputed from the record (>= 10^9 random pairs per operation over the four
    streams, the six default range blocks and the kernel windows they give, every edge category, the injection and the
    sanitizer runs); before, a --pairs 4 --min-pairs 4 run said 'passed' and was accepted here. (verdict, coverage)."""
    return _verdict(qd, _module('quad_differential').coverage(qd))


def thread_identity_verdict(ti, teams=False):
    """Stage-6 fix round 4 (W22): a thread_identity record is accepted only with its status 'passed' AND
    tests/thread_identity.py's coverage() (both default backends x both sectors, 1/8/16/64 threads and 8 x 8 lanes,
    64 tasks x 256 points on 32 graphs, identical); before, a --backends or --threads subset said 'passed'. The records
    summarized here predate X3 (no observed teams), so teams=False. (verdict, coverage)."""
    return _verdict(ti, _module('thread_identity').coverage(ti, teams=teams))


def validate_verdict(rec, gate, **kw):
    """Stage-6 fix round 4 (W1/W22's class): a tests/validate.py record speaks for a gate (J-VAL-2, G-BK8, G-L8SELF,
    A-IN-6b) only when validate.coverage(record, gate) is complete: its status says only that the tests it executed
    passed (--only and the options choose them). G-BK8 records made before W2 lack the full row rule (row_rule=False).
    (verdict, coverage)."""
    cov = _module('validate').coverage(rec, gate, **kw)
    return ('passed' if cov['complete'] else f'FAILED (coverage: {"; ".join(cov["why"])[:300]})'), cov


IDKEYS = ('test', 'sector', 'L', 'backend', 'layout', 'rate', 'order')


def keyed(x):
    # a record's test list, keyed by its identifying fields (the order of tests and new test kinds may differ)
    if isinstance(x, dict) and isinstance(x.get('tests'), list) and all(isinstance(t, dict) for t in x['tests']):
        x = dict(x); x['tests'] = {'|'.join(f'{k}={t.get(k)}' for k in IDKEYS if k in t): t for t in x['tests']}
    return x


def compare(new, old):
    a, b = keyed(strip(load(new))), keyed(strip(load(old)))
    added, gone = [], []
    for rec in (a, b): rec.pop('executed', None)  # 'executed' was added to validate.py's record after Stage 3
    if isinstance(a.get('tests'), dict) and isinstance(b.get('tests'), dict):
        # test kinds changed by the checkpoint review (T-04 replaced inspector_order_key by inspector_execution_order,
        # CK-K03 added inspector_private_tempdir): listed, not compared
        added, gone = sorted(set(a['tests']) - set(b['tests'])), sorted(set(b['tests']) - set(a['tests']))
        for k in added: a['tests'].pop(k)
        for k in gone: b['tests'].pop(k)
    d = diff(a, b)
    return {'stage3_record': str(Path(old).relative_to(ROOT)), 'equal_after_volatile_fields': not d, 'differences': d,
            'tests_new_since_stage3': added, 'stage3_tests_replaced': gone,
            'tests_compared': len(a['tests']) if isinstance(a.get('tests'), dict) else None}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--write', action='store_true'); a = ap.parse_args()
    B, V2, V3 = one('g4bbuild.*'), one('g4bval2.*'), one('g4bval3.*')
    out = {'build': {}, 'J-VAL-2': {}, 'J-VAL-3': {}, 'vs_stage3': {}}
    ident = load(B / 'identity.json'); packs = load(B / 'l8_packs.json')
    out['build'] = {'job': B.name, 'identical_to_e7ef98d': ident['identical'],
                    'sha256': {k: v['this'] for k, v in ident['binaries'].items()},
                    'l8_packs_equal_manifest': all(v['equal'] for v in packs.values()),
                    'baseline': dict(l.split()[::-1] for l in (B / 'binaries.sha256').read_text().splitlines() if 'baseline' in l)}
    ok = ident['identical'] and out['build']['l8_packs_equal_manifest']
    # J-VAL-2: make test-full
    v = V2 / 'val2'; r = {'job': V2.name}
    vf = load(v / 'validate_full.json'); r['validate_full'], r['validate_full_coverage'] = validate_verdict(vf, 'J-VAL-2'); r['validate_full_parts'] = vf['parts']  # fix round 4
    summ = [t for t in vf['tests'] if t.get('test') == 'replay_summary'][0]
    r['replay_summary'] = {k: summ[k] for k in summ if k not in ('reference_worker_command',) and not isinstance(summ[k], (list, dict)) or k in ('gates', 'totals', 'counts')}
    tot = {}
    for t in vf['tests']:
        if t.get('test') != 'replay_all_kernels': continue
        for g, x in t['gates'].items():
            s = tot.setdefault(g, {'rows': 0, 'mp_rows': 0, 'quad_points': 0, 'mp_points': 0})
            for k in s: s[k] += int(x.get(k, 0))
    r['replay_totals_by_gate'] = tot
    r['random_access_chunks'] = sum(1 for t in vf['tests'] if t.get('test') == 'random_access_chunks')
    r['chunk_max_normalized_difference'] = max(float(t['max_normalized_difference']) for t in vf['tests'] if t.get('test') == 'random_access_chunks')
    pc = load(v / 'point_checks.json'); r['point_checks'] = pc['status']
    r['point_checks_max'] = {x['backend']: {'checks': x['checks'], 'max_error_scaled': x['max_error_scaled_by_absolute_terms']} for x in pc['results']}
    for k in ('workflow', 'staging'):
        j = load(v / f'{k}.json'); r[k] = j.get('status') or ('passed' if j.get('passed') else j.get('verdict'))
    log = (V2 / 'make_test_full.log').read_text(); m = re.findall(r'check_inputs[^\n]*?(\d+)/(\d+)', log)
    r['check_inputs_log'] = [l for l in log.splitlines() if 'check_inputs' in l and ('passed' in l or 'FAIL' in l)][-3:]
    r['executables_unchanged'] = (V2 / 'binaries_before.sha256').read_text() == (V2 / 'binaries_after.sha256').read_text()
    out['J-VAL-2'] = r
    ok &= all(r[k] == 'passed' for k in ('validate_full', 'point_checks', 'workflow', 'staging')) and r['executables_unchanged']
    ok &= all(float(x['max_error_scaled']) < 1e-280 for x in r['point_checks_max'].values())
    # J-VAL-3
    r = {'job': V3.name}
    def verdict(j): return j.get('status') or ('passed' if j.get('passed') is True else 'FAILED')
    for k in ('l2_control', 'bk8', 'l8self', 'thread_identity', 'forced_tiers', 'quad_differential', 'merge_scale'):
        f = V3 / f'{k}.json'; r[k] = verdict(load(f)) if f.is_file() else 'FAILED (no record)'
    r['assembly_checks_exact'] = 'FAILED (no record)'
    if (V3 / 'assembly_checks_exact.json').is_file():
        ac = load(V3 / 'assembly_checks_exact.json'); r['assembly_checks_exact'] = verdict(ac)
        r['assembly_checks_counts'] = {'checks': len(ac['checks']), 'passed': sum(1 for c in ac['checks'] if c['passed'] is True), 'failed': ac['failed']}
    ms = load(V3 / 'merge_scale.json'); sc = ms['scale']
    r['merge_scale_numbers'] = {'rows': sc['rows'], 'shards': sc['shards'], 'byte_identical': sc['byte_identical'],
                                'peak_rss_mb_parallel': round(sc['parallel']['peak_rss_bytes'] / 2**20, 1), 'peak_rss_mb_serial': round(sc['serial']['peak_rss_bytes'] / 2**20, 1),
                                'phase1_rows_per_s': sc['parallel']['phase1_rows_per_s'], 'phase2_rows_per_s': sc['parallel']['phase2_rows_per_s'],
                                'many_shards_passed': ms['many_shards']['passed'], 'memory_scaling_passed': ms['memory_scaling']['passed'],
                                'rss_growth_mb': {k: round(v['rss_growth_bytes'] / 2**20, 2) for k, v in ms['memory_scaling']['cases'].items()}}
    l8 = load(V3 / 'l8self.json'); r['l8self_tests'] = [{x: t[x] for x in ('sector', 'backend', 'graphs', 'rows', 'quad_points', 'mp_points')} for t in l8['tests']]
    r['l8self_baseline'] = l8['tests'][0]['baseline']; r['l8self_candidate'] = l8['tests'][0]['candidate']
    ti = load(V3 / 'thread_identity.json'); r['thread_identity_blocks'] = [{x: b[x] for x in ('backend', 'sector', 'tasks', 'identical', 'quad', 'mp')} for b in ti['blocks']]
    bk = load(V3 / 'bk8.json'); r['bk8_tests'] = [{x: t[x] for x in ('sector', 'L', 'graphs', 'rows', 'mp_rows', 'quad_points', 'mp_points', 'max_normalized_difference_mp_rows', 'tail_rows_exact')} for t in bk['tests']]
    l2 = load(V3 / 'l2_control.json')['tests'][0]; r['l2_control_seed'] = l2['base_seed']
    r['l2_control_max_abs_pull'] = max(abs(p) for b in l2['backends'].values() for s in b['slots'] for p in s['pulls'].values())
    ft = load(V3 / 'forced_tiers.json'); r['forced_tiers_gates'] = ft['gates']
    r['forced_tiers'], r['forced_tiers_coverage'] = forced_tiers_verdict(ft)  # fix round 3 (Z2): status and recomputed coverage
    qd = load(V3 / 'quad_differential.json'); r['quad_differential'], r['quad_differential_coverage'] = quad_differential_verdict(qd)  # fix round 4 (W1)
    r['thread_identity'], r['thread_identity_coverage'] = thread_identity_verdict(ti)  # fix round 4 (W22): status and recomputed coverage
    r['bk8'], r['bk8_coverage'] = validate_verdict(bk, 'G-BK8', row_rule=False)    # these records predate W2's row rule
    r['l8self'], r['l8self_coverage'] = validate_verdict(l8, 'G-L8SELF')
    r['l2_control'], r['l2_control_coverage'] = validate_verdict(load(V3 / 'l2_control.json'), 'A-IN-6b')
    out['J-VAL-3'] = r
    ok &= all(r[k] == 'passed' for k in ('l2_control', 'bk8', 'l8self', 'thread_identity', 'forced_tiers', 'quad_differential', 'merge_scale', 'assembly_checks_exact'))
    # Against Stage 3 (same tests on the Stage-3 baseline)
    a2, a3 = S3 / 's3val2.54637263.0', S3 / 's3val3.54637264.0'
    pairs = {'validate_full': (v / 'validate_full.json', a2 / 'validate_full.json'), 'point_checks': (v / 'point_checks.json', a2 / 'point_checks.json'),
             'l2_control': (V3 / 'l2_control.json', a3 / 'l2_control.json'), 'bk8': (V3 / 'bk8.json', a3 / 'bk8.json'),
             'thread_identity': (V3 / 'thread_identity.json', a3 / 'thread_identity.json'), 'forced_tiers': (V3 / 'forced_tiers.json', a3 / 'forced_tiers.json'),
             'l8self': (V3 / 'l8self.json', a3 / 'l8self.json')}
    for k, (n, o) in pairs.items(): out['vs_stage3'][k] = compare(n, o)
    out['vs_stage3_all_equal'] = all(v['equal_after_volatile_fields'] for v in out['vs_stage3'].values())
    out['passed'] = bool(ok)
    txt = json.dumps(out, indent=1, default=str) + '\n'
    if a.write: (F / 'final_summary.json').write_text(txt)
    print(txt[:30000]); return 0 if ok else 1


if __name__ == '__main__': sys.exit(main())
