#!/usr/bin/env python3
"""Replay the package's own lane admission (tools/slurm_submit.py: Context.user_tokens/opts/partitions and admission())
for the production submission `C8_AMDQ_CAP=9 C8_SBATCH_ARGS="-p amdq --exclude=<list>" slurm/submit.sh --lanes 8`
against a real `squeue -u zzheng1 -h -r -o '%i|%T|%P|%q|%D|%u|%j'` snapshot of symmetry, without submitting anything: a
fake `squeue` on PATH prints the snapshot (plus each scenario's extra lines), so the real _squeue_records parses it.
Template: ../pilot/scripts/admission_check.py. Run on the Mac from the package root at the export's commit (ba68f40;
tools/ identical to the export, checked by the caller):
  admission_check.py SNAPSHOT EXCLUDE OUT.json
Scenarios (each line of the snapshot that is not a c8d2-* job is another session's and is never counted):
  a  the window (cap 9), nothing of this session live, --lanes 8: k = 8 + 1 merge = 9 (admitted)
  b  the same with the start-latency probe still live (k 9 against room 8: refused, largest N 7)
  c  without the window (env.sh's default cap 4): refused, largest N 3
  d  the window with three C63d c8d3-* jobs live on amdq (another session: not counted; admitted)
  e  round 2 after round 1 has ended (its workers and its afterany merge terminal): --lanes 2, k 3 (admitted)
  f  round 2 while two round-1 workers still run and the round-1 merge is PENDING on them: live 3, --lanes 6 (k 7 >
     room 6: refused, largest N 5), and --lanes 5 (k 6, admitted; the superseded merge is cancelled after the new one
     is accepted, A-ORC-10)"""
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

probe = '999001|RUNNING|amdq|normal|1|zzheng1|c8d2-prod-probe\n'
c63d = ''.join(f'99900{i}|RUNNING|amdq|normal|1|zzheng1|c8d3-prod{i}\n' for i in (2, 3, 4))
r1live = '999011|RUNNING|amdq|normal|1|zzheng1|c8d2-lanes\n999012|RUNNING|amdq|normal|1|zzheng1|c8d2-lanes\n999013|PENDING|amdq|normal|1|zzheng1|c8d2-merge\n'
own = [l for l in snap.splitlines() if l.split('|')[-1].startswith('c8d2-')]
res = {'package_root': str(ROOT), 'snapshot': str(snap_f), 'snapshot_lines': snap.splitlines(), 'snapshot_live_c8d2_lines': own, 'C8_SBATCH_ARGS': args,
       'allowlist_refusal': why,
       'scenarios': [run('a: window cap 9, nothing of this session live, --lanes 8', 9, 8), run('b: window, probe still live', 9, 8, probe),
                     run('c: no window (env.sh default cap 4)', 4, 8), run('d: window, three C63d c8d3-* jobs live', 9, 8, c63d),
                     run('e: round 2 after round 1 ended, --lanes 2', 9, 2), run('f1: round 2 with 2 round-1 workers live + pending merge, --lanes 6', 9, 6, r1live),
                     run('f2: the same, --lanes 5', 9, 5, r1live)]}
out.write_text(json.dumps(res, indent=1) + '\n')
print('allowlist:', why or 'accepted'); print('live c8d2-* lines in the snapshot:', own or 'none')
for s in res['scenarios']:
    r = s.get('record') or {}
    print(f"{s['scenario']}: admitted={s['admitted']}" + (f" k={r.get('k')} amd_live={r.get('amd_live')} room={r.get('room')} partitions={r.get('new_jobs')}" if s['admitted'] else f" exit={s.get('exit')} {s['message'][:240]}"))
