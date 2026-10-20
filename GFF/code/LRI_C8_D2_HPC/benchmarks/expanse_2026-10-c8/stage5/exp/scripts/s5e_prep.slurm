#!/bin/bash
#SBATCH -A <ACCOUNT> -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=16 --mem=32G -t 00:30:00 --no-requeue
#SBATCH -J c8d2-s5e-prep
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# Stage 5 on Expanse: the three test campaigns of J-EXP-2..4 (A-EXP-3), planned inside this job (as slurm/plan.sh does:
# production.py plan, then tools/ledger.py register RUN --role plan), each base seed added to the Expanse $C8_SEEDS
# (tools/seeds.py add RUN). Exact default path (D1); measured costs from J-SWEEP-1's cost model (Stage-3 baseline, so
# the estimates are conservative by about x1.65 for the final binary).
#   t2  J-EXP-2, the `shared` ARRAY smoke: --threads 32 (CPUs per element follow the plan's threads), 64 graphs per
#       group (stratified), 2 x 4096 points, the default 1.5-h index sizing (one index per group, 24 indices). A plan
#       always has the 24 groups, so a 2-element array is made by completing 22 indices here first: this job runs every
#       index of t2 except the two heaviest (production.py run --index I, 16 threads; checkpoints carry this job's id,
#       which the ledger records as the plan job with a note). `slurm/submit.sh` then submits exactly the two incomplete
#       indices as one 2-element array, and the afterok merge on `shared` (plain array mode, A-EXP-3).
#   t3  J-EXP-3, the `debug` lane worker (C8_LANES=numa: 8 lanes x 16 cores): --threads 16, 1,024 graphs per group
#       (stratified), 2 x 4096 points, --index-hours 0.05 (about 10 core-h at Stage-3 costs).
#   t4  J-EXP-4, the `compute` lane job (default lanes 16 x 8): --threads 8, the same sample, --index-hours 0.1.
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> C8_S5E=$C8_DATA/s5e-<sha12> S2=<seed> S3=<seed> S4=<seed> sbatch --export=ALL s5e_prep.slurm
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}" "${C8_S5E:?}" "${S2:?}" "${S3:?}" "${S4:?}" "${C8_SEEDS:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=s5eprep.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
CM1=$C8_PACKAGE/benchmarks/expanse_2026-10-c8/stage3b/sweep1.54641706.0/cost_model.json
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; campaigns under $C8_S5E; evidence $E"
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS GMP_PREFIX NUMERICS
cd "$C8_PACKAGE" || exit 64
[ "$(sha256sum bin/c8d2_gmp | cut -c1-64)" = 1d2a218147ef52b5d0ac37dd8aaead55045ab4fe68e48ec963ea4b8e93024faa ] || { echo "bin/c8d2_gmp is not the final default binary" >&2; exit 3; }
mkdir -p "$C8_S5E"; cp "$C8_SEEDS" "$E/seeds_before.json"
for s in "$S2" "$S3" "$S4"; do python3 -B tools/seeds.py check "$s" >> "$E/seed_checks.txt" 2>&1 || { echo "seed $s is forbidden (seeds.py check); nothing planned" >&2; cat "$E/seed_checks.txt"; exit 64; }; done
COMMON="--pilot --points 4096 --replicates 2 --test-selection stratified --backend gmp --cost-model $CM1"
status=0
plan() {  # plan <name> <seed> <arguments...>
  local n=$1 s=$2; shift 2; local d=$C8_S5E/$n
  echo "== plan $n $(date -Is): $COMMON $* --seed $s"
  python3 -B tools/production.py plan "$d" $COMMON "$@" --seed "$s" > "$E/plan_$n.json" 2> "$E/plan_$n.stderr" || { echo "plan $n FAILED"; cat "$E/plan_$n.stderr"; status=3; return 1; }
  python3 -B tools/ledger.py register "$d" --role plan --note "Stage 5 J-EXP test campaign $n: planned by the prep job${NOTE:+; $NOTE}" | tee -a "$E/ledger_register.txt"
  python3 -B tools/seeds.py add "$d" | tee -a "$E/seeds_add.txt"
  python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print({k:d[k] for k in ('jobs','tasks','checkpoints','estimated_core_hours','max_index_wall_seconds','projected_files','array_mem_suggestion_mb')})" "$E/plan_$n.json"
}
NOTE="it also ran 22 of the 24 indices (all but the two heaviest) so that slurm/submit.sh submits a 2-element array" plan t2 "$S2" --test-graphs 64 --threads 32
NOTE= plan t3 "$S3" --test-graphs 1024 --threads 16 --checkpoint-tasks 256 --index-hours 0.05
NOTE= plan t4 "$S4" --test-graphs 1024 --threads 8 --checkpoint-tasks 256 --index-hours 0.1
cp "$C8_SEEDS" "$E/seeds_after.json"
echo "== t2: run every index except the two heaviest $(date -Is)"
python3 - "$C8_S5E/t2" > "$E/t2_prerun_indices.json" <<'PY'
import json, sys
m = json.load(open(f'{sys.argv[1]}/manifest.json')); js = sorted(m['jobs'], key=lambda j: (-j['est_core_seconds'], j['id']))
print(json.dumps({'left_for_the_array': sorted(j['id'] for j in js[:2]), 'prerun': sorted(j['id'] for j in js[2:]),
                  'left_detail': [{k: j[k] for k in ('id', 'group', 'tasks', 'est_core_seconds')} for j in js[:2]]}))
PY
cat "$E/t2_prerun_indices.json"
for i in $(python3 -c "import json,sys;print(' '.join(map(str,json.load(open(sys.argv[1]))['prerun'])))" "$E/t2_prerun_indices.json"); do
  python3 -B tools/production.py run "$C8_S5E/t2" --index "$i" --threads 16 >> "$E/t2_prerun.log" 2>&1 || { echo "t2 index $i FAILED"; status=3; }
done
python3 -B tools/production.py status "$C8_S5E/t2" > "$E/t2_status_after_prerun.txt" 2>&1; echo "t2 status exit $? (2 incomplete indices expected)"; tail -8 "$E/t2_status_after_prerun.txt"
echo "finished $(date -Is), status $status"
exit $status
