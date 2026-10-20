#!/usr/bin/env python3
"""Stage 5 on Expanse: recompute the verdicts and key numbers of the Stage-5 Expanse jobs from the records copied into
benchmarks/expanse_2026-10-c8/stage5/exp/ (one directory per job), standard library only. Run from the repository root:
  python3 -B benchmarks/expanse_2026-10-c8/stage5/exp/scripts/s5e_summary.py [--write]
With --write the summary goes to stage5/exp/s5e_summary.json. Exit 1 if a gate fails.

  exp1      J-EXP-1: identity of the executables (final default build), BOOST_LIB_VERSION 1_77, make test's records.
  zen2      the GMP_PREFIX=zen2 gates: the zen2 build record; J-VAL-2 (make test-full), G-BK8 and forced tiers each
            passed, and each record equal, after the run-specific fields are removed (summarize_final.py's rules), to
            G4b's record of the DEFAULT build (stage4b/final: g4bval2.54672151.0, g4bval3.54672152.0); and the L8
            comparison of the zen2 worker with the default worker (validate.py --l8self <default bin>) exact.
  perf5     A-PERF-5: per (sector, L) and per (campaign, sector, L), the speedup of the final default binary
            (J-SWEEP-2E's cost model) over the Stage-3 baseline (J-SWEEP-1's cost model, stage3b/sweep1.54641706.0):
            sum over the stratum's graphs of the Stage-3 seconds per point / the same sum for the final binary (every
            graph weighted by its points, as in a uniform-points pilot or the sweep itself).
  pilot     J-PIL-1E: the plan's printed estimate, and a lane simulation of the plan's indices on N Expanse compute
            nodes (16 lanes of 8 cores each, heaviest index first to the earliest free lane, index wall = est core
            seconds / (8 x 0.9), the plan's own sizing assumption) for N = 1..8: makespan, node-hours, SU at 128 SU per
            node-hour, lane occupancy.
"""
from __future__ import annotations
import argparse, glob, gzip, hashlib, heapq, importlib.util, json, math, sys
from pathlib import Path

ROOT = Path.cwd(); X = ROOT / 'benchmarks/expanse_2026-10-c8/stage5/exp'
G4B = ROOT / 'benchmarks/expanse_2026-10-c8/stage4b/final'
CM1 = ROOT / 'benchmarks/expanse_2026-10-c8/stage3b/sweep1.54641706.0/cost_model.json'
spec = importlib.util.spec_from_file_location('summarize_final', G4B / 'scripts/summarize_final.py'); SF = importlib.util.module_from_spec(spec)
spec.loader.exec_module(SF)  # strip/diff/keyed/compare: the G4b comparison rules (main() is not run)


def load(p): return json.loads(Path(p).read_text())


def one(pattern):
    m = sorted(glob.glob(str(X / pattern)))
    if len(m) != 1: raise SystemExit(f'expected one {pattern} under {X}, found {m}')
    return Path(m[0])


def verdict(j): return j.get('status') or ('passed' if j.get('passed') is True else 'FAILED')


def exp1():
    E = one('s5eexp1.*'); ident = load(E / 'identity.json'); packs = load(E / 'l8_packs.json')
    recs = {p.stem: verdict(load(p)) for p in sorted((E / 'test').glob('*.json'))}
    log = (E / 'make_test.log').read_text()
    return {'job': E.name, 'executables_identical_to_final_default': ident['identical'], 'boost_1_77_everywhere': ident['boost_1_77_everywhere'],
            'sha256': {k: v['sha256'] for k, v in ident['executables'].items()}, 'l8_packs_equal_manifest': all(v['equal'] for v in packs.values()),
            'make_test_records': recs, 'make_test_records_all_passed': bool(recs) and all(v == 'passed' for v in recs.values()),
            'make_test_error_lines': [l for l in log.splitlines() if 'Error' in l or 'FAILED' in l][:10],
            'executables_unchanged_by_make_test': [l[:64] for l in (E / 'binaries.sha256').read_text().splitlines()] == [l[:64] for l in (E / 'binaries_after.sha256').read_text().splitlines()],
            'build_passed': ident['ok'] and all(v['equal'] for v in packs.values()),
            'passed': ident['ok'] and bool(recs) and all(v == 'passed' for v in recs.values()) and 'unit_orchestration' in recs and 'staging' in recs}


def exp1b():
    """J-EXP-1's follow-up: every `make test` command to the end (exits.txt), the lanes group alone, and the two
    diagnoses (s5enfdebug: the f2_profile failure; s5eexp1c: the one-line fix checked in a copy)."""
    E = one('s5eexp1b.*'); ex = {}
    for l in (E / 'exits.txt').read_text().splitlines():
        f = l.split()
        if len(f) == 4: ex[f'{f[0]}.{f[1]}'] = {'exit': int(f[2]), 'seconds': int(f[3])}
        elif len(f) == 2: ex[f[0]] = {'exit': int(f[1])}
    uo = load(E / 'test/unit_orchestration.json'); nf = load(E / 'test/test_numerics_flags.json')
    C = one('s5eexp1c.*'); fixed = load(C / 'test_numerics_flags_patched.json')
    return {'job': E.name, 'commands': ex, 'make_test_commands_failed': [k for k, v in ex.items() if v['exit'] and '.' in k],
            'unit_orchestration_failed_groups': [{'test': f.get('test'), 'error': [l for l in (f.get('error') or '').splitlines() if l.startswith('C8: ')][:1]} for f in uo.get('failed') or []],
            'test_numerics_flags_failed': nf.get('failed'), 'lanes_alone_whole_node_exit': ex.get('lanes_full', {}).get('exit'),
            'lanes_alone_taskset_0_15_exit': ex.get('lanes_taskset16', {}).get('exit'),
            'numerics_flags_fix_checked_in_copy': {'job': C.name, 'patch': (C / 'patch.diff').read_text(), 'passed': fixed['passed'], 'failed': fixed['failed']},
            'passed': not [k for k, v in ex.items() if v['exit'] and '.' in k]}


def campaigns():
    out = {}
    for t, what in (('t2', 'J-EXP-2 shared array (2 elements) + shared merge'), ('t3', 'J-EXP-3 debug lane worker (8 x 16) + debug merge'),
                    ('t4', 'J-EXP-4 compute lane worker (16 x 8) + compute merge')):
        d = X / 's5ecampaigns' / t; a = load(d / 'accounting.json'); v = load(d / 'verify_result.json'); r = load(d / 'C8_test_result.json')
        led = [json.loads(l) for l in (d / 'submissions.jsonl').read_text().splitlines() if l.strip()]
        st = (d / 'status.txt').read_text()
        out[t] = {'what': what, 'complete': 'complete: every checkpoint block is committed' in st, 'result_scope_test_partial': 'INCOMPLETE workflow test' in str(r.get('scope')),
                  'verify_result': v.get('verified'), 'ledger': [{k: x.get(k) for k in ('jobid', 'role', 'partition', 'elements', 'admission_ref') if k in x} for x in led],
                  'accounting': {k: a.get(k) for k in ('complete', 'allocated_core_hours', 'work_core_hours', 'overhead_core_hours', 'busy_thread_core_hours', 'eta_node')}}
    out['passed'] = all(v['complete'] and v['verify_result'] for v in out.values())
    return out


def zen2():
    E = one('s5ezen2.*'); b = load(E / 'zen2_build.json'); r = {'job': E.name, 'build': b}
    v = E / 'val2'
    r['val2'] = {k: verdict(load(v / f'{k}.json')) for k in ('validate_full', 'point_checks', 'workflow', 'staging')}
    pc = load(v / 'point_checks.json'); r['point_checks_max'] = {x['backend']: x['max_error_scaled_by_absolute_terms'] for x in pc['results']}
    vf = load(v / 'validate_full.json'); tot = {}
    r['val2']['validate_full'], r['validate_full_coverage'] = SF.validate_verdict(vf, 'J-VAL-2')  # fix round 4 (W1/W22's class): recomputed coverage
    for t in vf['tests']:
        if t.get('test') != 'replay_all_kernels': continue
        for g, x in t['gates'].items():
            s = tot.setdefault(g, {'rows': 0, 'mp_rows': 0, 'quad_points': 0, 'mp_points': 0})
            for k in s: s[k] += int(x.get(k, 0))
    r['replay_totals_by_gate'] = tot
    for k in ('bk8', 'forced_tiers', 'vs_default_l8'):
        f = E / f'{k}.json'; r[k] = verdict(load(f)) if f.is_file() else 'FAILED (no record)'
    bk = load(E / 'bk8.json'); r['bk8'], r['bk8_coverage'] = SF.validate_verdict(bk, 'G-BK8', row_rule=False)  # fix round 4 (W2): pre-W2 record
    r['vs_default_l8'], r['vs_default_l8_coverage'] = SF.validate_verdict(load(E / 'vs_default_l8.json'), 'G-L8SELF')  # fix round 4: recomputed coverage
    r['bk8_tests'] = [{x: t[x] for x in ('sector', 'L', 'graphs', 'rows', 'mp_rows', 'quad_points', 'mp_points', 'max_normalized_difference_mp_rows')} for t in bk['tests']]
    ft = load(E / 'forced_tiers.json'); r['forced_tiers_gates'] = ft['gates']
    r['forced_tiers'], r['forced_tiers_coverage'] = SF.forced_tiers_verdict(ft)  # fix round 3 (Z2): status and recomputed coverage
    l8 = load(E / 'vs_default_l8.json'); r['vs_default_l8_tests'] = [{x: t[x] for x in ('sector', 'backend', 'graphs', 'rows', 'quad_points', 'mp_points')} for t in l8['tests']]
    r['vs_default_l8_baseline'] = l8['tests'][0]['baseline']; r['vs_default_l8_candidate'] = l8['tests'][0]['candidate']
    r['executables_unchanged'] = (E / 'binaries_before.sha256').read_text() == (E / 'binaries_after.sha256').read_text()
    a2, a3 = G4B / 'g4bval2.54672151.0/val2', G4B / 'g4bval3.54672152.0'
    pairs = {'validate_full': (v / 'validate_full.json', a2 / 'validate_full.json'), 'point_checks': (v / 'point_checks.json', a2 / 'point_checks.json'),
             'workflow': (v / 'workflow.json', a2 / 'workflow.json'), 'staging': (v / 'staging.json', a2 / 'staging.json'),
             'bk8': (E / 'bk8.json', a3 / 'bk8.json'), 'forced_tiers': (E / 'forced_tiers.json', a3 / 'forced_tiers.json')}
    cmp = {}
    for k, (n, o) in pairs.items():
        c = SF.compare(n, o); c['default_record'] = str(Path(o).relative_to(ROOT)); c.pop('stage3_record', None)
        # the inspector's mkdtemp directory names (CK-K03 test, c8d2_inspect.XXXXXX) are random in every run
        c['ignored_random_tempdir_names'] = [d for d in c['differences'] if '/private_directory/name:' in d]
        c['differences'] = [d for d in c['differences'] if d not in c['ignored_random_tempdir_names']]
        c['equal_after_volatile_fields'] = not c['differences']; cmp[k] = c
    r['vs_default_build_records'] = cmp
    r['vs_default_build_records_all_equal'] = all(c['equal_after_volatile_fields'] for c in cmp.values())
    r['passed'] = (b['ok'] and all(x == 'passed' for x in r['val2'].values()) and all(r[k] == 'passed' for k in ('bk8', 'forced_tiers', 'vs_default_l8'))
                   and r['executables_unchanged'] and all(float(x) < 1e-280 for x in r['point_checks_max'].values()))
    return r


SWEEP_FINAL = 's5esweep2.54676908.0'   # exp-1-07: the Expanse cost model (cost_models/gmp_expanse_amd_c8.json)
SWEEP_SLOW = 's5esweep2.54676896.0'    # exp-1-29: the first J-SWEEP-2E, on the node that is slow on L7/L8 work


def cost_model(run):
    """A sweep's cost model: the final one is the committed cost_models/gmp_expanse_amd_c8.json (checked against the
    sha256 the job's evidence records), the exp-1-29 one is kept gzipped in its evidence folder."""
    d = X / run; want = (d / 'cost_model.sha256').read_text().split()[0]
    data = (ROOT / 'cost_models/gmp_expanse_amd_c8.json').read_bytes() if run == SWEEP_FINAL else gzip.decompress((d / 'cost_model.json.gz').read_bytes())
    if hashlib.sha256(data).hexdigest() != want: raise SystemExit(f'{run}: cost model sha256 differs from {d}/cost_model.sha256')
    return json.loads(data)


def perf5():
    E = X / SWEEP_FINAL; new = cost_model(SWEEP_FINAL); old = load(CM1)
    a, b = old['seconds_per_point'], new['seconds_per_point']
    if set(a) != set(b): raise SystemExit('the two cost models have different keys')
    def agg(keyf):
        s = {}
        for k in a:
            c, sec, L, g = k.split(':'); key = keyf(c, sec, int(L))
            x = s.setdefault(key, [0., 0., 0]); x[0] += a[k]; x[1] += b[k]; x[2] += 1
        return s
    out = {'stage3': {'cost_model': str(CM1.relative_to(ROOT)), 'executable_sha256': old['executable_sha256'], 'lane_width': old.get('lane_width'), 'job_ids': old.get('job_ids'), 'hosts': old.get('hosts')},
           'final': {'cost_model': 'cost_models/gmp_expanse_amd_c8.json (= ' + SWEEP_FINAL + ')', 'executable_sha256': new['executable_sha256'], 'lane_width': new.get('lane_width'),
                     'job_ids': new.get('job_ids'), 'hosts': new.get('hosts'), 'keys': len(b)},
           'rule': 'speedup = sum over the stratum of Stage-3 seconds per point / the same sum for the final binary (equal points per graph)'}
    rows = {}
    for (sec, L), (x, y, n) in sorted(agg(lambda c, s, L: (s, L)).items()):
        rows[f'{sec}_L{L}'] = {'graphs_x_campaigns': n, 'stage3_core_s_per_point_sum': x, 'final_core_s_per_point_sum': y, 'speedup': x / y}
    out['per_sector_L'] = rows
    out['per_campaign_sector_L'] = {f'{c}_{s}_L{L}': {'graphs': n, 'speedup': x / y} for (c, s, L), (x, y, n) in sorted(agg(lambda c, s, L: (c, s, L)).items())}
    for name, f in (('per_sector', lambda c, s, L: s), ('per_L', lambda c, s, L: L), ('total', lambda c, s, L: 'all')):
        out[name] = {str(k): {'speedup': x / y, 'stage3_core_h_per_point_x1e6': x / 3600 * 1e6} for k, (x, y, n) in sorted(agg(f).items())}
    qf = {}
    for frac in ('quad_fraction', 'mp_fraction'):
        fa, fb = old.get(frac) or {}, new.get(frac) or {}; t = {}
        for k in fa:
            c, s, L, g = k.split(':'); x = t.setdefault(f'{s}_L{L}', [0., 0., 0]); x[0] += fa[k]; x[1] += fb.get(k, 0.); x[2] += 1
        qf[frac] = {k: {'stage3_mean': x / n, 'final_mean': y / n} for k, (x, y, n) in sorted(t.items())}
    out['promotion_fractions_mean_over_graphs'] = qf
    # the same sweep on exp-1-29 (another fresh seed, so per-graph sampling noise as well): the node comparison
    slowm = cost_model(SWEEP_SLOW); slow = slowm['seconds_per_point']; t = {}
    for k in b:
        c, s, L, g = k.split(':'); x = t.setdefault(f'{s}_L{L}', [0., 0.]); x[0] += slow[k]; x[1] += b[k]
    out['node_check'] = {'slow_run': SWEEP_SLOW, 'slow_hosts': slowm.get('hosts'), 'final_hosts': new.get('hosts'),
                         'exp_1_29_over_final_per_sector_L': {k: x / y for k, (x, y) in sorted(t.items())},
                         'exp_1_29_over_final_total': sum(slow.values()) / sum(b.values()),
                         'stage3_over_exp_1_29_total': sum(a.values()) / sum(slow.values())}
    return out


def pilot():
    E = one('s5epilot.*'); p = load(E / 'plan_stdout.json'); js = load(E / 'jobs_compact.json')
    est = sorted((j['est_core_seconds'] for j in js['jobs']), reverse=True); W = js['threads']; eff = js['assumed_efficiency']
    walls = [e / (W * eff) for e in est]; per_node = 128 // W
    sims = {}
    for N in range(1, 9):
        lanes = [0.] * (N * per_node); heapq.heapify(lanes)
        for w in walls: t = heapq.heappop(lanes); heapq.heappush(lanes, t + w)
        mk = max(lanes); busy = sum(walls)
        sims[N] = {'lanes': N * per_node, 'makespan_h': mk / 3600, 'node_hours': N * mk / 3600, 'SU_at_128_per_node_hour': 128 * N * mk / 3600,
                   'lane_occupancy': busy / (N * per_node * mk) if mk else None}
    return {'plan': p, 'jobs': len(est), 'threads': W, 'assumed_efficiency': eff, 'largest_index_wall_h': walls[0] / 3600 if walls else None,
            'sum_index_walls_lane_h': sum(walls) / 3600, 'estimated_core_hours': sum(est) / 3600, 'lane_simulation': sims}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--write', action='store_true'); ap.add_argument('--only', nargs='*'); a = ap.parse_args()
    out = {}
    for name, f in (('exp1', exp1), ('exp1b', exp1b), ('campaigns', campaigns), ('zen2', zen2), ('perf5', perf5), ('pilot', pilot)):
        if a.only and name not in a.only: continue
        try: out[name] = f()
        except (SystemExit, FileNotFoundError) as e: out[name] = {'missing': str(e)}
    txt = json.dumps(out, indent=1, default=str) + '\n'
    if a.write: (X / 's5e_summary.json').write_text(txt)
    print(txt[:20000])
    ok = all(v.get('passed', True) and 'missing' not in v for v in out.values() if isinstance(v, dict))
    return 0 if ok else 1


if __name__ == '__main__': sys.exit(main())
