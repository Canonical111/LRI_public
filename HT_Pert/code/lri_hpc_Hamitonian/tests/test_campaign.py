"""Campaign planning and status logic (cluster/expanse/campaign.py, status.py) on synthetic calibration data."""
import json, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'cluster' / 'expanse'))
import campaign as C
import status as S

# Calibration rows as measured by V (job 54519867, revision 74b0ac0) on an AMD EPYC 7742 node.
CAL = {('thermal', 7): [(60, 11900137, 4.44, 1211072908, 19.2), (70, 39623469, 14.68, 4264330864, 35.9)],
       ('phi6', 5): [(50, 1555644, 0.59, 142938586, 6.7), (70, 13057619, 3.98, 1316721606, 16.6)],
       ('phi6', 3): [(128, 3681457, 0.87, 293114886, 3.9), (200, 21017626, 4.49, 1705243794, 10.7)]}
models = {k: C.Model(*k, [dict(cutoff=L, dim=d, threads=64, rss=g * 2**30, edges=e, seconds=t, source='x')
                          for L, d, g, e, t in rows]) for k, rows in CAL.items()}

# Memory model reproduces the calibration points to within 2 %.
for k, rows in CAL.items():
    for L, d, g, e, t in rows[1:]:
        assert abs(models[k].rss_gib(L, d) / g - 1) < 0.02, (k, L, models[k].rss_gib(L, d), g)
# int64 edges cost more per state than int32 at the same cutoff.
m = models[('thermal', 7)]
assert m.edge_bytes_per_state(112, 2**31) > m.edge_bytes_per_state(112, 2**31 - 1)

items, rejected = C.plan_items(models)   # exact dimensions via lri_hpc.basis.count_tables
keys = [C.item_key(it) for it in items]
assert len(keys) == len(set(keys))
for it in items:
    assert it['partition'] == ('shared' if it['request_gib'] <= C.SHARED_MAX_GIB else 'large-shared')
    assert it['request_gib'] <= C.LARGE_MAX_GIB
    assert it['stretch'] == (C.MARGIN * it['model_rss_gib'] + C.PAD_GIB > C.LARGE_MAX_GIB)
    assert it['int64'] == (it['dim'] > C.INT32_MAX)
# every task stops at its first inadmissible cutoff; it and every larger candidate are recorded (review IR-002)
assert {(r['task'], r['degree']) for r in rejected} == set(C.CAPS)
for r in rejected:
    assert all(it['cutoff'] < r['cutoff'] for it in items if (it['task'], it['degree']) == (r['task'], r['degree']))
    assert r['reason'].startswith('memory')
for tk in C.CAPS:
    first = min(r['cutoff'] for r in rejected if (r['task'], r['degree']) == tk)
    assert sorted(r['cutoff'] for r in rejected if (r['task'], r['degree']) == tk) == [L for L in C.planned_cutoffs(*tk) if L >= first]
    assert sorted([it['cutoff'] for it in items if (it['task'], it['degree']) == tk] +
                  [r['cutoff'] for r in rejected if (r['task'], r['degree']) == tk]) == C.planned_cutoffs(*tk), 'complete inventory'

lanes = C.make_lanes(items)
seen = [C.item_key(it) for ln in lanes for it in ln['items']]
assert sorted(seen) == sorted(keys), 'each item in exactly one lane'
for ln in lanes:
    assert {it['partition'] for it in ln['items']} == {ln['partition']}
    assert ln['mem_gib'] >= max(it['request_gib'] for it in ln['items'])
    assert ln['threads'] <= C.MAX_THREADS and ln['threads'] <= ln['cores'] <= 128
    assert ln['mem_gib'] <= (C.SHARED_MAX_GIB if ln['partition'] == 'shared' else C.LARGE_MAX_GIB)
    st = [it['stretch'] for it in ln['items']]
    assert st == sorted(st), 'stretch items run last'
    nonst = [it['dim'] for it in ln['items'] if not it['stretch']]
    assert nonst == sorted(nonst, reverse=True), 'largest first'
big = [ln for ln in lanes if ln['partition'] == 'large-shared']
assert big[0]['items'][0]['task'] == 'thermal' and big[1]['items'][0]['task'] == 'thermal', 'thermal lanes first'

# Status classification from synthetic lane records, events and accounting (review LRI-012, LRI-014).
with tempfile.TemporaryDirectory() as tmp:
    C.CAMPAIGN = Path(tmp) / 'campaign'; C.RESULTS = Path(tmp) / 'results'
    (C.CAMPAIGN / 'events').mkdir(parents=True)
    its = [dict(task='thermal', degree=7, cutoff=L) for L in range(52, 76, 2)]
    k = [C.item_key(it) for it in its]
    subs = [dict(job='1', items=k[:4], mem_gib=10, wall_s=3600),     # TIMEOUT lane
            dict(job='2', items=[k[4]], mem_gib=10, wall_s=3600),    # pending
            dict(job='3', items=[k[1]], mem_gib=15, wall_s=3600),    # second OOM kill of k[1]
            dict(job='4', items=[k[6]], mem_gib=10, wall_s=3600),    # supervisor OOM-killed
            dict(job='5', items=[k[7]], mem_gib=10, wall_s=3600),    # cancelled
            dict(job='6', items=[k[8]], mem_gib=10, wall_s=3600),    # accounting missing
            dict(job='7', items=[k[9]], mem_gib=10, wall_s=3600),    # accounting nonterminal
            dict(job='8', items=[k[10]], mem_gib=1950, wall_s=3600)]  # killed at the ceiling, exhaustion recorded
    ev = {'1': [('start', k[0]), ('end', k[0], 0, True), ('start', k[1]), ('end', k[1], -9, False), ('start', k[2])],
          '3': [('start', k[1]), ('end', k[1], -9, False)], '4': [('start', k[6])], '5': [('start', k[7])],
          '6': [('start', k[8])], '7': [('start', k[9])], '8': [('start', k[10]), ('end', k[10], -9, False)]}
    for job, es in ev.items():
        with (C.CAMPAIGN / 'events' / f'{job}.jsonl').open('w') as f:
            for e in es:
                d = dict(event=e[0], key=e[1])
                if e[0] == 'end':
                    d.update(rc=e[2], ok=e[3], reason='x')
                f.write(json.dumps(d) + '\n')
    fp = 'FP'
    good = dict(task='thermal', degree=7, cutoff=52, source_sha256=fp, seconds=1., ranks=[dict(maxrss_kib=1024)],
                second_order_shell_residual=0., C=[0.] * 8, r=[0.] * 8, g=[0.] * 8, tuning_residual=0.)
    out = C.output_path(its[0]); out.parent.mkdir(parents=True); out.write_text(json.dumps(good))
    acct = {'1': 'TIMEOUT', '3': 'OUT_OF_MEMORY', '4': 'OUT_OF_MEMORY', '5': 'CANCELLED', '7': 'COMPLETING', '8': 'FAILED'}
    S.sacct_states = lambda ids: {i: acct[i] for i in ids if i in acct}
    (C.CAMPAIGN / 'EXHAUSTED.jsonl').write_text(json.dumps(dict(key=k[10], reason='killed at the node memory limit')) + '\n')
    res = S.collect(its, subs, {'2': dict(state='PENDING', name='n', partition='shared')}, fp)
    got = {key: res[key]['state'] for key in k}
    want = {k[0]: 'done', k[1]: 'exhausted', k[2]: 'interrupted', k[3]: 'not-reached', k[4]: 'queued',
            k[5]: 'unsubmitted', k[6]: 'killed', k[7]: 'failed', k[8]: 'unknown', k[9]: 'unknown', k[10]: 'exhausted',
            k[11]: 'unsubmitted'}
    assert got == want, {x: (got[x], want[x]) for x in k if got[x] != want[x]}
    assert res[k[2]]['last']['job_state'] == 'TIMEOUT'
    # a valid same-source result under another item's file name is not accepted as that item (review IR2-002)
    wrong = C.output_path(its[11]); wrong.write_text(json.dumps(good))
    assert S.collect(its[11:12], [], {}, fp)[k[11]]['state'] == 'unsubmitted'
    assert 'identity' in S.output_ok(its[11], fp)[1]
    bad = dict(good, second_order_shell_residual=1e-3); out.write_text(json.dumps(bad))
    assert S.collect(its[:1], [], {}, fp)[k[0]]['state'] == 'unsubmitted', 'gate-failing output is not done'

    # sbatch arguments (review LRI-011): complete --key=value options, QOS for large-shared only.
    import submit_cutoffs as U
    for ln in (big[0], [x for x in lanes if x['partition'] == 'shared'][0]):
        cmd = U.sbatch_command(ln, 7200, Path('/x/lane.json'))
        assert cmd[:2] == ['sbatch', '--parsable'] and cmd[-1].endswith('lane.slurm')
        opts = cmd[2:-1]
        assert all(o.startswith('--') and '=' in o for o in opts), cmd
        d = dict(o[2:].split('=', 1) for o in opts)
        assert d['partition'] == ln['partition'] and d['mem'] == f"{ln['mem_gib']}G" and d['time'] == '2:00:00'
        assert d['cpus-per-task'] == str(ln['cores']) and d['job-name'] == ln['name']
        assert ('qos' in d) == (ln['partition'] == 'large-shared') and d.get('qos', 'large-shared-normal') == 'large-shared-normal'
        assert U.sbatch_command(ln, 7200, Path('/x'), test_only=True)[1] == '--test-only'

    # Deadline admissibility per item (review LRI-015): near expiry a long item is exhausted, a short one survives.
    from datetime import timedelta
    near = C.EXPIRY - timedelta(hours=2)          # one hour usable before expiry - 1 h
    long_it = dict(task='thermal', degree=7, cutoff=110, model_seconds=7200.0, partition='large-shared', dim=2,
                   request_gib=900, stretch=False)
    short_it = dict(task='thermal', degree=7, cutoff=96, model_seconds=300.0, partition='large-shared', dim=1,
                    request_gib=300, stretch=False)
    keep, gone = U.deadline_filter([long_it, short_it], near)
    assert [C.item_key(i) for i in keep] == ['thermal_d7_L96'] and [g[0] for g in gone] == ['thermal_d7_L110'], (keep, gone)
    ln = C.make_lanes(keep)
    assert len(ln) == 1 and [i['cutoff'] for i in ln[0]['items']] == [96] and ln[0]['mem_gib'] == 300
    assert C.wall_seconds(ln[0]['model_seconds'], near)[0] <= 3600

    # Retry admission is decided per item (review IR-001): a 10-min item interrupted at the end of an 8 h lane is
    # retried when 3 h remain; an item that already ran 3 h is not; a kill at the memory ceiling is not.
    three_h = C.EXPIRY - timedelta(hours=4)
    small = dict(task='thermal', degree=7, cutoff=98, model_seconds=300.0, partition='large-shared', dim=1,
                 request_gib=300, stretch=False)
    st_late = dict(state='interrupted', last=dict(mem_gib=1500, wall_s=8 * 3600, elapsed_s=600.0))
    ln, why = U.retry_request(st_late, small, three_h)
    assert ln is not None and why is None and ln['wall_override'] == 3600 and ln['mem_gib'] == 1500, (ln, why)
    ln, why = U.retry_request(dict(state='interrupted', last=dict(mem_gib=1500, wall_s=8 * 3600, elapsed_s=3 * 3600.0)), small, three_h)
    assert ln is None and 'interrupted after' in why
    ln, why = U.retry_request(dict(state='killed', last=dict(mem_gib=C.LARGE_MAX_GIB, wall_s=3600)), small, three_h)
    assert ln is None and 'memory limit' in why
    ln, why = U.retry_request(dict(state='killed', last=dict(mem_gib=200, wall_s=3600)), small, three_h)
    assert ln['mem_gib'] == 300 and ln['partition'] == 'large-shared' and ln['cores'] == 64 and ln['wall_override'] is None
print(f'campaign: {len(items)} items in {len(lanes)} lanes ({len(big)} large-shared); rejected',
      [C.item_key(r) for r in rejected])
print('PASS test_campaign')
