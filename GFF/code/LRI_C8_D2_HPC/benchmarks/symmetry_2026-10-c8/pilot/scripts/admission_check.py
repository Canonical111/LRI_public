#!/usr/bin/env python3
"""Replay the package's own lane admission (tools/slurm_submit.py: Context.user_tokens/opts/partitions and admission())
for the pilot's submission `C8_AMDQ_CAP=5 C8_SBATCH_ARGS="-p amdq --exclude=<list>" slurm/submit.sh --lanes 4` against a
real `squeue -u zzheng1 -h -r -o '%i|%T|%P|%q|%D|%u|%j'` snapshot of symmetry, without submitting anything: a fake
`squeue` on PATH prints the snapshot (plus the scenario's extra lines), so the real _squeue_records parses it. Run on the
Mac from the package root at the pilot's commit (ba68f40; tools/ identical to the export):
  admission_check.py SNAPSHOT EXCLUDE OUT.json
Scenarios: (a) the snapshot as taken, window cap 5, --lanes 4 (k = 5); (b) the same with the start-latency probe still
live (k = 5 against room 4: refused, largest N 3); (c) without the window (env.sh's default cap 4); (d) the snapshot
plus three live C63d c8d3-* jobs on amdq (another session's jobs: not counted, H7 is per session); (e) --lanes 3 inside
the window (k = 4)."""
import json, os, shlex, stat, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'tools'))
import production as prod
import slurm_submit as ss
snap_f, exclude, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
snap = snap_f.read_text()
args = f'-p amdq --exclude={exclude}'
why = prod.check_sbatch_args(shlex.split(args))

class Stub:  # the real Context's option and partition methods on the scenario's settings
    user_tokens = ss.Context.user_tokens; opts = ss.Context.opts; partitions = ss.Context.partitions
    def __init__(self, cap, env): self.site = shlex.split(args); self.extra = []; self.env = env; self.site_name = 'symmetry'; self.amd_cap = cap

def run(name, cap, n, extra=''):
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / 'snap.txt'; f.write_text(snap + extra)
        sq = Path(td) / 'squeue'; sq.write_text(f'#!/bin/sh\ncat {shlex.quote(str(f))}\n'); sq.chmod(sq.stat().st_mode | stat.S_IXUSR)
        env = {'PATH': f'{td}:/usr/bin:/bin', 'C8_SITE': 'symmetry', 'C8_AMDQ_CAP': str(cap)}
        os.environ['PATH'] = env['PATH']
        try: rec = ss.admission(Stub(cap, env), [('lane', n), ('merge', 1)], 'lanes'); res = {'admitted': True, 'record': rec}
        except ss.Refuse as e: res = {'admitted': False, 'exit': e.code if hasattr(e, 'code') else None, 'message': str(e)}
    res.update(scenario=name, cap=cap, lanes=n, extra_lines=extra.splitlines()); return res

probe = '999001|RUNNING|amdq|normal|1|zzheng1|c8d2-pilot-probe\n'
c63d = ''.join(f'99900{i}|RUNNING|amdq|normal|1|zzheng1|c8d3-dev{i}\n' for i in (2, 3, 4))
res = {'package_root': str(ROOT), 'snapshot': str(snap_f), 'snapshot_lines': snap.splitlines(), 'C8_SBATCH_ARGS': args, 'allowlist_refusal': why,
       'scenarios': [run('a: window, nothing live', 5, 4), run('b: window, probe still live', 5, 4, probe), run('c: no window (default cap 4)', 4, 4),
                     run('d: window, three C63d c8d3-* jobs live', 5, 4, c63d), run('e: window, --lanes 3', 5, 3)]}
out.write_text(json.dumps(res, indent=1) + '\n')
print('allowlist:', why or 'accepted')
for s in res['scenarios']:
    r = s.get('record') or {}
    print(f"{s['scenario']}: admitted={s['admitted']}" + (f" k={r.get('k')} amd_live={r.get('amd_live')} room={r.get('room')} partitions={r.get('new_jobs')}" if s['admitted'] else f" exit={s.get('exit')} {s['message'][:220]}"))
