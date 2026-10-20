#!/usr/bin/env python3
"""Kernel time of a campaign: for each completed attempt, the sum of the 'seconds' of its checkpoint rows, against the
attempt's wall time times its threads. Prints the totals and one line per (sector, loop). Usage: kernel_time.py RUN_DIR.
This is the computation behind results/C8_2_check/prod1_analysis/kernel_util.txt (25,585.3 kernel core-hours, 0.967 of
the attempt core-hours; 0.965 of the 26,526 allocated core-hours)."""
import calendar, collections, json, sys, time
from pathlib import Path

run = Path(sys.argv[1]); m = json.loads((run / 'manifest.json').read_text()); jobs = {j['id']: j for j in m['jobs']}
ts = lambda s: calendar.timegm(time.strptime(s, '%Y-%m-%dT%H:%M:%SZ'))
K = W = 0.0; by = collections.defaultdict(lambda: [0, 0.0, 0.0]); n = 0; outcomes = collections.Counter()
for f in sorted((run / 'attempts').glob('*.jsonl')):
    j = jobs[int(f.stem)]
    for a in (json.loads(x) for x in f.read_text().splitlines()):
        outcomes[a.get('outcome')] += 1
        if a.get('outcome') != 'done': continue
        w = ts(a['end']) - ts(a['start'])
        k = sum(r['seconds'] for c in (run / 'groups' / j['group'] / 'checkpoints').glob(f"s{j['shard']:06d}_p*.json")
                for r in json.loads(c.read_text())['native']['rows'])
        g = j['group'].split('_', 1)[1]; by[g][0] += 1; by[g][1] += k; by[g][2] += w * a['threads']; K += k; W += w * a['threads']; n += 1
print('attempt outcomes', dict(outcomes))
print(f'done attempts {n} kernel_core_h {K / 3600:.1f} attempt_core_h {W / 3600:.1f} util {K / W:.3f}')
for g, (c, k, w) in sorted(by.items(), key=lambda x: -x[1][1]):
    print(f'{g:10s} n={c:4d} kernel_core_h={k / 3600:9.1f} attempt_core_h={w / 3600:9.1f} util={k / w:.3f}')
