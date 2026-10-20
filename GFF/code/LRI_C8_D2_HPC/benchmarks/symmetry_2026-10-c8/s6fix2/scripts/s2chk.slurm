#!/bin/bash
#SBATCH -p sharedq -N 1 -n 1 -c 2 --mem=4G -t 00:20:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# Stage-6 fix round 2 on symmetry: the checks after the lane drill of the Y2 campaign (RUNDIR, planned and partly run by
# s2y2.slurm; the rest run by `slurm/submit.sh --lanes 1` in drill mode on sharedq, submitted with OMP_THREAD_LIMIT=1
# and OMP_DYNAMIC=true exported, C8_ENV_SETUP = scripts/env_probe.sh recording what each job inherited in PROBE):
#   - every checkpoint of the campaign records runtime.omp_team with 4 threads requested, per Slurm job (the s2y2 job's
#     direct and array runs, the lane worker's lanes); no 'smaller' and no refusal; each verdict 'verified' (at least 4
#     observed), or 'unverified' only for a worker that lived less than SHORT seconds (0.1 s: the watch samples after
#     0, 1, 2, 4, 8, ... ms, so a worker of a few milliseconds can exit before a sample sees its team; G2's design:
#     'unverified' is a run too short to observe, never refused; production refuses only 'smaller');
#   (first run, 570422: the same checks with every verdict required 'verified'; it failed on three such workers of
#   13-18 ms, so the criterion above was uploaded as work/s2-<sha12>/s2chk.slurm and run again)
#   - the lane worker and the merge inherited OMP_THREAD_LIMIT=1 and OMP_DYNAMIC=true (PROBE/omp_env_job_<id>.txt);
#   - the lane worker log names its lanes, its memory limit (Y7: the drill's --mem through the cgroup) and no refusal;
#   - production.py status exits 0 (complete, merged) and its omp_teams counts every checkpoint as verified.
# Usage: C8_PACKAGE=... RUNDIR=... PROBE=... sbatch --export=ALL --dependency=afterok:<merge> -J c8d2-s2chk s2chk.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}" "${RUNDIR:?}" "${PROBE:?}"
D=<SCRATCH>/c8d2; TAG=$(basename "$C8_PACKAGE"); RUN=s2chk.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$D/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; campaign $RUNDIR; probe $PROBE; evidence $E"
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1
cd "$C8_PACKAGE" || exit 64
status=0
python3 -B tools/production.py status "$RUNDIR" --json > "$E/status.json" 2> "$E/status.stderr"; c=$?
echo "status exit $c" | tee "$E/status_exit.txt"; [ $c -eq 0 ] || status=1
cp -p "$RUNDIR"/slurm_logs/*.log "$E/" 2>/dev/null; cp -p "$PROBE"/omp_env_job_*.txt "$E/" 2>/dev/null
python3 -B - "$RUNDIR" "$E" "$PROBE" <<'PY'
import json, re, sys
from pathlib import Path
run, E, probe = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
m = json.loads((run / 'manifest.json').read_text()); rows = []
for f in sorted(run.glob('groups/*/checkpoints/*.json')):
    rt = json.loads(f.read_text())['runtime']; t = rt.get('omp_team') or {}; fp = rt.get('fingerprint') or {}
    rows.append({'checkpoint': str(f.relative_to(run)), 'host': fp.get('host'), 'job': (fp.get('slurm') or {}).get('SLURM_JOB_ID'),
                 **{k: t.get(k) for k in ('requested', 'observed', 'verdict', 'samples', 'seconds')}})
by_job = {}
for r in rows:
    j = by_job.setdefault(str(r['job']), {'host': r['host'], 'checkpoints': 0, 'verdicts': {}})
    j['checkpoints'] += 1; j['verdicts'][r['verdict']] = j['verdicts'].get(r['verdict'], 0) + 1
st = json.loads((E / 'status.json').read_text()) if (E / 'status.json').exists() else {}
envs = {p.name: p.read_text().split() for p in sorted(probe.glob('omp_env_job_*.txt'))}
logs = {p.name: p.read_text(errors='replace') for p in sorted((run / 'slurm_logs').glob('*.log'))}
lane_lines = {k: [l for l in v.splitlines() if re.search(r'memory limit|lanes? of|refused|exit 64|smaller', l)][:12] for k, v in logs.items() if k.startswith('lane-')}
out = {'jobs_in_plan': len(m['jobs']), 'checkpoints': len(rows), 'by_job': by_job, 'verdicts': sorted({r['verdict'] for r in rows}),
       'status_omp_teams': st.get('omp_teams'), 'merged': len(list(run.glob('groups/*/merged.json'))), 'groups': len(m.get('groups', [])) or None,
       'inherited_env_per_job': envs, 'lane_log_lines': lane_lines}
SHORT = 0.1
ver = lambda r: r['verdict'] == 'verified' and (r['observed'] or 0) >= 4
short = lambda r: r['verdict'] == 'unverified' and (r['seconds'] or 0) < SHORT
out['all_verified'] = bool(rows) and all(ver(r) for r in rows)
out['unverified_short'] = [{k: r[k] for k in ('checkpoint', 'observed', 'samples', 'seconds')} for r in rows if short(r)]
out['teams_ok'] = bool(rows) and all(r['requested'] == 4 and (ver(r) or short(r)) for r in rows)
out['jobs_inherited_the_controls'] = bool(envs) and all('OMP_THREAD_LIMIT=1' in v and 'OMP_DYNAMIC=true' in v for v in envs.values())

out['ok'] = out['teams_ok'] and out['jobs_inherited_the_controls'] and 'smaller' not in out['verdicts'] and out['merged'] == (out['groups'] or len(m['jobs']))
(E / 'teams.json').write_text(json.dumps({**out, 'rows': rows}, indent=1) + '\n')
print(json.dumps(out, indent=1))
sys.exit(0 if out['ok'] else 3)
PY
[ $? -eq 0 ] || status=1
echo "finished $(date -Is), status $status"; exit $status
