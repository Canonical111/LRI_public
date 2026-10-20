#!/bin/bash
#SBATCH -p sharedq -N 1 -n 1 -c 8 --mem=15G -t 01:00:00 --no-requeue
#SBATCH -o /mnt/beegfs/zzheng1/c8d2/logs/%x_%j.out
# C8(2) PRODUCTION preparation on symmetry (2026-10-06): plan the production campaign in a plan job, exactly as the
# runbook says (docs/HPC.md "Plan jobs", docs/DESIGN.md "Production batches" and step 5 of "After the pilot"): one
# batch (K = 1) of the route-(b) bundle chosen by the user (USER DECISION 2026-10-06: 2.5e-4, dd+mp256, 8 nodes),
#   slurm/plan.sh RUN --design BUNDLE --numerics dd+mp256 --approved-numerics-change REF --cost-model <profile model>
#                 --backend gmp --threads 8 --checkpoint-tasks 256 --index-hours 1.5 --forbid-seeds-from $C8_SEEDS --seed SEED
# (task-seconds, min-chunk and max-task-seconds at their defaults 60 s, 256 points and 120 s: the freeze's caps sizing;
# the same arguments as J-DES-5 and the route-(b) re-freeze 570579 apart from --test-graphs). The arguments live in this
# file so that the approval reference reaches production.py byte for byte (no quoting through ssh and sbatch).
# plan.sh publishes the campaign atomically, the non-test plan registers its seed in $C8_SEEDS under the log's lock
# before publishing (Z15; plan.sh's own add then says "present"), and the job is registered in the campaign ledger
# (role plan). Before the plan: the campaign must not exist; the bundle's design_meta.json, the profile cost model, the
# gated executable and its build record are hashed. After it: the manifest's route-(b) record, the plan's sizing and
# scale, `production.py status --fast` and the seed log are recorded; nothing is submitted.
# Evidence: /mnt/beegfs/zzheng1/c8d2/evidence/<sha12>/prplan.<jobid>.<restart>/
# Usage: C8_PACKAGE=... C8_RUN=... sbatch --export=ALL -J c8d2-plan-prod prplan.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}" "${C8_RUN:?}" "${C8_SEEDS:?}"
export C8_ENV_SETUP=$HOME/c8d2/env.sh OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
D=/mnt/beegfs/zzheng1/c8d2; TAG=$(basename "$C8_PACKAGE"); E=$D/evidence/$TAG/prplan.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
SEED=6274393056071737300
BUNDLE=/mnt/beegfs/zzheng1/c8-d2/designs/pilot1-20261006-ddmp256-2.5e-4
REF="user check-in 2026-10-05 (dd+mp256 approved for production after the pilot) and user decision 2026-10-06 (production at 2.5e-4, dd+mp256, 8 nodes)"
CM=$C8_PACKAGE/cost_models/gmp_symmetry_amd_c8_dd+mp256.json
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE ($(cat "$C8_PACKAGE.commit")); campaign $C8_RUN; evidence $E"
test "$(cat "$C8_PACKAGE.commit")" = ba68f401e46e4071ca5593ae40ec92a1755dcc98 || { echo "export is not ba68f40; refusing" >&2; exit 64; }
test ! -e "$C8_RUN" || { echo "$C8_RUN exists; refusing (a plan needs a new campaign directory)" >&2; exit 64; }
{ sha256sum "$BUNDLE/design_meta.json" "$BUNDLE/design.json" "$CM" "$C8_PACKAGE/bin/c8d2_gmp_dd+mp256" "$C8_PACKAGE/bin/c8d2_gmp_dd+mp256.build.json" \
    "$C8_PACKAGE/benchmarks/symmetry_2026-10-c8/s6fix4/s4flag.570574.0/jflag_dd+mp256/numerics_flags.json" "$C8_PACKAGE/inputs/manifest.json" "$HOME/c8d2/env.sh"
  sha256sum "$C8_SEEDS"; } | tee "$E/inputs_before.sha256"
python3 -B -c "import json,sys;print(len(json.load(open(sys.argv[1]))['seeds']),'seeds in',sys.argv[1])" "$C8_SEEDS" | tee "$E/seed_log_before.txt"
printf '%s\n' "$REF" > "$E/approval_reference.txt"
echo "== plan $(date -Is)"
s=0
/usr/bin/time -v -o "$E/time_plan.txt" bash "$C8_PACKAGE/slurm/plan.sh" "$C8_RUN" --design "$BUNDLE" --numerics dd+mp256 --approved-numerics-change "$REF" \
  --cost-model "$CM" --backend gmp --threads 8 --checkpoint-tasks 256 --index-hours 1.5 --forbid-seeds-from "$C8_SEEDS" --seed "$SEED" \
  > >(tee "$E/plan.stdout") 2> >(tee "$E/plan.stderr" >&2) || s=$?
sleep 2
echo "== plan.sh exit $s $(date -Is)"; grep -E 'Maximum resident|Elapsed \(wall' "$E/time_plan.txt"
if (( s )); then echo "plan FAILED (exit $s); nothing more" >&2; exit $s; fi
sha256sum "$C8_RUN/manifest.json" | tee "$E/manifest.sha256"
cp "$C8_RUN/manifest.json" "$E/manifest.json"; cp "$C8_RUN/submissions.jsonl" "$E/submissions.jsonl"
sha256sum "$C8_SEEDS" | tee "$E/seed_log_after.sha256"; cp "$C8_SEEDS" "$E/seed_log_after.json"
python3 -B "$C8_PACKAGE/tools/seeds.py" check "$SEED" | tee "$E/seed_check_after.txt" || true
python3 -B - "$C8_RUN" "$E" "$SEED" "$REF" "$BUNDLE" <<'PY' || s=4
import hashlib, json, os, sys
from pathlib import Path
run, E, seed, ref, bundle = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3]), sys.argv[4], sys.argv[5]
m = json.loads((run / 'manifest.json').read_bytes()); nr = m.get('numerics_route') or {}
meta_sha = hashlib.sha256(Path(bundle, 'design_meta.json').read_bytes()).hexdigest()
gates = nr.get('gates') or []
chk = {
    'test_only_false': m.get('test_only') is False,
    'numerics_dd+mp256': m.get('numerics') == 'dd+mp256',
    'route_b': nr.get('route') == 'b',
    'executable_gated': nr.get('executable_gated') is True,
    'executable_a46f3060': m.get('executable') == 'c8d2_gmp_dd+mp256' and m.get('executable_sha256', '').startswith('a46f3060a27f') and nr.get('executable_sha256') == m.get('executable_sha256'),
    'gate_570574_42e6d2d8': any(g.get('sha256', '').startswith('42e6d2d80a48') and g.get('profile_executable_sha256') == m.get('executable_sha256') for g in gates),
    'gate_gmp_library_4dc20a90': any(str(x).startswith('4dc20a901c69') for x in nr.get('gate_gmp_library') or []),
    'bundle_6afb6dd6': (m.get('design') or {}).get('meta_sha256') == meta_sha and meta_sha.startswith('6afb6dd66216') and (m.get('allocation') or {}).get('meta_sha256') == meta_sha,
    'bundle_path': os.path.realpath(str((m.get('design') or {}).get('bundle'))) == os.path.realpath(bundle),
    'plan_approval_is_ref': m.get('approved_numerics_change') == ref and nr.get('plan_approval') == ref,
    'bundle_approval_recorded': bool(nr.get('bundle_approval')),
    'cost_model_18e50440': str(m.get('cost_model_sha256')).startswith('18e50440e649') and m.get('cost_model_numerics') == 'dd+mp256',
    'seed': m.get('seed') == seed,
    'seed_log': os.path.realpath(str(m.get('seed_log'))) == os.path.realpath('/mnt/beegfs/zzheng1/c8-d2/forbidden_seeds.json'),
    'threads_8': m.get('threads') == 8, 'checkpoint_tasks_256': m.get('checkpoint_tasks') == 256,
    'index_hours_1.5': (m.get('index_sizing') or {}).get('index_hours') == 1.5,
    'task_seconds_60': (m.get('chunking') or {}).get('task_seconds') == 60.0 and (m.get('chunking') or {}).get('min_chunk') == 256 and (m.get('chunking') or {}).get('max_task_seconds') == 120.0,
    'batches_1': (m.get('design') or {}).get('batches') == 1,
    'r_128_everywhere': set(((m.get('design') or {}).get('r') or {}).values()) == {128},
}
rec = {'checks': chk, 'all_ok': all(chk.values()), 'numerics_route': nr, 'design': m.get('design'), 'allocation': m.get('allocation'),
       'scale': {k: v for k, v in (m.get('scale') or {}).items() if k != 'merge'}, 'merge': (m.get('scale') or {}).get('merge'),
       'estimates': {k: v for k, v in (m.get('estimates') or {}).items()}, 'chunking': m.get('chunking'), 'index_sizing': m.get('index_sizing'),
       'executable': m.get('executable'), 'executable_sha256': m.get('executable_sha256'), 'seed': m.get('seed'), 'seed_log': m.get('seed_log'),
       'cost_model_sha256': m.get('cost_model_sha256'), 'inputs_manifest_sha256': m.get('inputs_manifest_sha256'), 'threads': m.get('threads'),
       'checkpoint_tasks': m.get('checkpoint_tasks'), 'approved_numerics_change': m.get('approved_numerics_change'), 'jobs': len(m.get('jobs') or []),
       'largest_est_peak_bytes': max(j['est_peak_bytes'] for j in m['jobs']), 'largest_est_core_seconds': max(j['est_core_seconds'] for j in m['jobs'])}
(E / 'plan_checks.json').write_text(json.dumps(rec, indent=1, sort_keys=True) + '\n')
print(json.dumps(chk, sort_keys=True)); print('all checks:', rec['all_ok'])
sys.exit(0 if rec['all_ok'] else 4)
PY
echo "== status --fast $(date -Is)"
python3 -B "$C8_PACKAGE/tools/production.py" status "$C8_RUN" --fast > "$E/status_before_submit.txt" 2>&1; echo "status exit $?" | tee -a "$E/status_before_submit.txt"
head -40 "$E/status_before_submit.txt"
echo "finished $(date -Is), status $s"; exit $s
