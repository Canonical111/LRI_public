#!/bin/bash
#SBATCH -p sharedq -N 1 -n 1 -c 8 --mem=15G -t 01:00:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# Stage-6 fix round 2 on symmetry, sharedq (Intel; outside the H7 AMD-pool cap), in the export built by s2build.slurm.
# SUBMITTED WITH OMP_THREAD_LIMIT=1 AND OMP_DYNAMIC=true EXPORTED (sbatch --export=ALL), as a module or a shell would
# leave them; every check below runs under them unless it says otherwise.
#   Y7  lanes.cgroup_memory_limit() / memory_limit() on this shared allocation (--mem=15G), with every cgroup level;
#   Y6  the node's fingerprint survey (common.fingerprint + fingerprint_problems = [] for bin/c8d2_gmp), then the
#       failing-ldd simulation on a fresh campaign: a fake `ldd` (exit 1) first on PATH, `production.py run --index I1`
#       must exit 64 ("incomplete runtime fingerprint", claim_io refusal) with no pin (cpu_vendor.json,
#       runtime_identity.json) and no checkpoint written;
#   Y2  the campaign RUNDIR (test-only pilot, 2 cheapest graphs per (sector, L), 2048 points x 2 replicates, --threads 4,
#       one index per group; fresh seed SEED, checked against $C8_SEEDS, added after the plan; never a result), with the
#       two indices of the largest estimate (L8) run here:
#         direct: `production.py run RUNDIR --index I1 --threads 4`;
#         array: slurm/run_array.sh with SLURM_ARRAY_TASK_ID=I2, SLURM_CPUS_PER_TASK=4 (the array element script, run in
#           this allocation: its unsetting of OMP_*/GOMP_*/KMP_* and its production.py run);
#       both exit 0 and every checkpoint they commit records runtime.omp_team verdict 'verified' with 4 threads requested,
#       and their logs name the inherited controls that were not passed to the worker; the other indices are left to
#       the lane drill (slurm/submit.sh --lanes 1 in drill mode, submitted from the Mac driver with the same exports).
#   Y13 tools/sweep.py --plan-only (all graphs, 16 points x 2 replicates, bootstrap chunk 16, one shard) with a fresh
#       seed SWEEP_SEED: inside this job without a seed log it is refused before planning (no directory); with
#       --seeds-log $C8_SEEDS it registers the seed right after the plan (source = the sweep directory); a rerun says
#       "present". The sweep campaign is never run (plan only).
# Usage: OMP_THREAD_LIMIT=1 OMP_DYNAMIC=true C8_PACKAGE=... RUNDIR=<SCRATCH>/c8-d2/y2-<sha12> SEED=<fresh> \
#          SWEEP=<SCRATCH>/c8-d2/y13sweep-<sha12> SWEEP_SEED=<fresh> \
#          sbatch --export=ALL --dependency=afterok:<s2build> -J c8d2-s2y2 s2y2.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}" "${RUNDIR:?}" "${SEED:?}" "${SWEEP:?}" "${SWEEP_SEED:?}" "${C8_SEEDS:?}"
D=<SCRATCH>/c8d2; TAG=$(basename "$C8_PACKAGE"); RUN=s2y2.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$D/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; campaign $RUNDIR; sweep $SWEEP; evidence $E"
{ hostname; lscpu; } > "$E/node.txt" 2>&1; grep -E 'Model name' "$E/node.txt"
env | grep -E '^(OMP|GOMP|KMP)_' | sort | tee "$E/omp_env_at_start.txt"
grep -qx 'OMP_THREAD_LIMIT=1' "$E/omp_env_at_start.txt" && grep -qx 'OMP_DYNAMIC=true' "$E/omp_env_at_start.txt" \
  || { echo "submit with OMP_THREAD_LIMIT=1 OMP_DYNAMIC=true exported"; exit 64; }
export TMPDIR=/tmp/c8d2_$SLURM_JOB_ID OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"
unset C8_INPUTS C8_ALLOW_NO_L8 LD_LIBRARY_PATH
cd "$C8_PACKAGE" || exit 64
P="python3 -B tools/production.py"
sha256sum bin/c8d2_gmp tools/production.py tools/common.py tools/lanes.py tools/sweep.py slurm/run_array.sh "$HOME/c8d2/env.sh" | tee "$E/inputs.sha256"
status=0
expect() {  # expect NAME CODE CMD... : run CMD, log to $E/NAME.log, record (name, wanted, got) in $E/steps.txt
  local name=$1 want=$2; shift 2; local t=$(date +%s)
  "$@" > "$E/$name.log" 2>&1; local c=$?
  echo "$name want=$want got=$c $(( $(date +%s) - t ))s" | tee -a "$E/steps.txt"
  if [ "$want" = nonzero ]; then [ $c -ne 0 ] || status=1; else [ $c -eq "$want" ] || status=1; fi
  tail -2 "$E/$name.log" | cut -c1-400
}
# ---- Y7 and the Y6 survey
expect y7_y6_survey 0 python3 -B - "$E" <<'PY'
import json, os, sys
from pathlib import Path
sys.path.insert(0, 'tools')
import common, lanes
E = Path(sys.argv[1]); cpu = {}; fp = common.fingerprint(Path('bin/c8d2_gmp'), None, cpu); kind = common.elf_kind(Path('bin/c8d2_gmp'))
rec = {'host': os.uname().nodename, 'Y6': {'elf_kind': kind, 'problems': common.fingerprint_problems(fp, kind, cpu), 'cpu_identity': cpu,
       'ldd_error': fp.get('ldd_error'), 'libraries': {k: (v or {}).get('sha256') for k, v in fp['libraries'].items()}}}
lines = Path('/proc/self/cgroup').read_text().splitlines(); levels = []
for line in lines:
    parts = line.split(':', 2)
    if len(parts) != 3: continue
    ctrl, path = parts[1], parts[2]
    if ctrl == '': base, name = Path('/sys/fs/cgroup'), 'memory.max'
    elif 'memory' in ctrl.split(','): base, name = Path('/sys/fs/cgroup/memory'), 'memory.limit_in_bytes'
    else: continue
    p = base / path.lstrip('/')
    while True:
        try: levels.append({'dir': str(p), 'file': name, 'value': (p / name).read_text().strip()})
        except OSError as e: levels.append({'dir': str(p), 'file': name, 'error': type(e).__name__})
        if p == base: break
        p = p.parent
finite = [int(l['value']) for l in levels if l.get('value') not in (None, '', 'max') and int(l['value']) < 2**60]
lim, src = lanes.memory_limit(dict(os.environ))
rec['Y7'] = {'proc_self_cgroup': lines, 'levels': levels, 'cgroup_memory_limit': lanes.cgroup_memory_limit(), 'memory_limit': [lim, src],
             'min_finite_over_levels': min(finite) if finite else None, 'SLURM_MEM_PER_NODE': os.environ.get('SLURM_MEM_PER_NODE')}
rec['Y7']['equals_min'] = rec['Y7']['cgroup_memory_limit'] == rec['Y7']['min_finite_over_levels']
(E / 'y7_y6_survey.json').write_text(json.dumps(rec, indent=1) + '\n')
print(json.dumps({'Y6_problems': rec['Y6']['problems'], 'Y7': {k: rec['Y7'][k] for k in ('cgroup_memory_limit', 'memory_limit', 'min_finite_over_levels', 'equals_min', 'SLURM_MEM_PER_NODE')}}, indent=1))
sys.exit(0 if not rec['Y6']['problems'] and rec['Y7']['equals_min'] else 3)
PY
# ---- the campaign (test-only), its seed checked against the live log and added after the plan
test ! -e "$RUNDIR" || { echo "$RUNDIR exists; refusing"; exit 64; }
python3 -B tools/seeds.py check "$SEED" > "$E/seed_check.txt" 2>&1 || { echo "seed $SEED refused"; cat "$E/seed_check.txt"; exit 65; }
expect plan 0 $P plan "$RUNDIR" --pilot --test-graphs 2 --test-selection cheapest --points 2048 --replicates 2 --threads 4 \
  --shards 1 --backend gmp --cost-model cost_models/gmp_symmetry_amd_c8.json --seed "$SEED" --forbid-seeds-from "$C8_SEEDS"
[ -e "$RUNDIR/manifest.json" ] || { echo "plan failed"; exit 3; }
python3 -B tools/ledger.py register "$RUNDIR" --role plan > "$E/ledger_register.txt" 2>&1 || status=1
python3 -B tools/seeds.py add "$RUNDIR" > "$E/seeds_add.txt" 2>&1 || status=66
cat "$E/seeds_add.txt"; cp -p "$RUNDIR/manifest.json" "$E/manifest.json"
read -r I1 I2 < <(python3 -c "import json,sys;j=json.load(open(sys.argv[1]))['jobs'];o=sorted(range(len(j)),key=lambda i:-(j[i].get('est_core_seconds')or 0));print(o[0],o[1])" "$RUNDIR/manifest.json")
echo "direct index $I1, array index $I2 (the two largest estimates)" | tee "$E/indices.txt"
# ---- Y6: a failing ldd probe on the first claim: exit 64, nothing pinned, nothing run
FAKE=$TMPDIR/fakeldd; mkdir -p "$FAKE"; printf '#!/bin/sh\necho "ldd: simulated probe failure (Stage-6 fix round 2, Y6)" >&2\nexit 1\n' > "$FAKE/ldd"; chmod +x "$FAKE/ldd"
expect y6_failing_ldd 64 env PATH="$FAKE:$PATH" $P run "$RUNDIR" --index "$I1" --threads 4 --scratch "$TMPDIR"
{ ls "$RUNDIR"/cpu_vendor.json "$RUNDIR"/runtime_identity.json 2>&1; find "$RUNDIR/groups" -path '*checkpoints*' -name '*.json' | wc -l; } > "$E/y6_after.txt"
cat "$E/y6_after.txt"
if [ -e "$RUNDIR/runtime_identity.json" ] || [ -e "$RUNDIR/cpu_vendor.json" ] || [ "$(find "$RUNDIR/groups" -path '*checkpoints*' -name '*.json' | wc -l)" != 0 ]; then
  echo "Y6: SOMETHING WAS PINNED OR RUN" | tee -a "$E/steps.txt"; status=1; fi
grep -h "incomplete\|^claim_io" "$E/y6_failing_ldd.log" | cut -c1-700 | tee "$E/y6_refusal.txt"
# ---- Y2: the direct and array entry points under the inherited controls
expect y2_direct 0 $P run "$RUNDIR" --index "$I1" --threads 4 --scratch "$TMPDIR"
expect y2_array 0 env SLURM_ARRAY_TASK_ID="$I2" C8_INDEX_OFFSET=0 SLURM_CPUS_PER_TASK=4 C8_RUN="$RUNDIR" C8_PACKAGE="$C8_PACKAGE" bash slurm/run_array.sh
grep -h "^omp:\|^C8: index" "$E"/y2_*.log | tee "$E/y2_omp_lines.txt"
expect y2_teams 0 python3 -B - "$RUNDIR" "$E" <<'PY'
import json, sys
from pathlib import Path
run, E = Path(sys.argv[1]), Path(sys.argv[2]); m = json.loads((run / 'manifest.json').read_text())
rows = []
for f in sorted(run.glob('groups/*/checkpoints/*.json')):
    rt = json.loads(f.read_text())['runtime']; t = rt.get('omp_team') or {}
    rows.append({'checkpoint': str(f.relative_to(run)), 'host': (rt.get('fingerprint') or {}).get('host'), **{k: t.get(k) for k in ('requested', 'observed', 'verdict', 'samples', 'seconds')}})
out = {'checkpoints': len(rows), 'verdicts': sorted({r['verdict'] for r in rows}), 'rows': rows}
out['ok'] = bool(rows) and all(r['verdict'] == 'verified' and r['requested'] == 4 and (r['observed'] or 0) >= 4 for r in rows)
(E / 'y2_teams_direct_array.json').write_text(json.dumps(out, indent=1) + '\n'); print(json.dumps({k: out[k] for k in ('checkpoints', 'verdicts', 'ok')}))
sys.exit(0 if out['ok'] else 3)
PY
grep -q "OMP_THREAD_LIMIT=1" "$E/y2_direct.log" || { echo "Y2: the direct run's log does not name the inherited OMP_THREAD_LIMIT" | tee -a "$E/steps.txt"; status=1; }
# ---- Y13: the sweep registers its seed right after its plan
test ! -e "$SWEEP" || { echo "$SWEEP exists; refusing"; exit 64; }
python3 -B tools/seeds.py check "$SWEEP_SEED" > "$E/sweep_seed_check.txt" 2>&1 || { echo "sweep seed $SWEEP_SEED refused"; cat "$E/sweep_seed_check.txt"; exit 65; }
SW="--seed $SWEEP_SEED --points 16 --replicates 2 --threads 4 --bootstrap-chunk 16 --shards 1 --plan-only"
expect y13_no_log nonzero env -u C8_SEEDS python3 -B tools/sweep.py "$SWEEP" $SW
[ ! -e "$SWEEP" ] || { echo "Y13: the refused sweep left $SWEEP" | tee -a "$E/steps.txt"; status=1; }
expect y13_plan_only 0 python3 -B tools/sweep.py "$SWEEP" $SW --seeds-log "$C8_SEEDS"
expect y13_rerun 0 python3 -B tools/sweep.py "$SWEEP" $SW --seeds-log "$C8_SEEDS"
python3 -B - "$C8_SEEDS" "$SWEEP_SEED" "$SWEEP" "$SEED" "$RUNDIR" <<'PY' | tee "$E/seed_entries.json"
import json, sys
log, s, sweep, seed, run = sys.argv[1], int(sys.argv[2]), sys.argv[3], int(sys.argv[4]), sys.argv[5]
d = json.load(open(log)); ent = lambda x: [e for e in d['seeds'] if e['seed'] == x]
print(json.dumps({'log_seeds': len(d['seeds']), 'sweep': ent(s), 'campaign': ent(seed)}, indent=1))
sys.exit(0 if len(ent(s)) == 1 and len(ent(seed)) == 1 else 3)
PY
[ ${PIPESTATUS[0]} -eq 0 ] || status=1
grep -h "added\|present\|NOT registered\|seeds-log" "$E"/y13_*.log | cut -c1-300 | tee "$E/y13_lines.txt"
$P status "$RUNDIR" --json > "$E/status_after_direct_array.json" 2>&1 || true
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $status"; exit $status
