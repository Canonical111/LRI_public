#!/bin/bash
#SBATCH -A <ACCOUNT> -p compute -N 1 --ntasks=1 --cpus-per-task=128 --exclusive --mem=240G -t 02:00:00 --no-requeue
#SBATCH -J c8d2-s5e-sweep2
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# Stage 5, J-SWEEP-2E: the cost-model sweep on the FINAL default binary (bin/c8d2_gmp 1d2a2181..., exact path, D1) on
# one whole Expanse compute node (2 x EPYC 7742, 8 NUMA nodes of 16 cores), giving the Expanse cost model
# cost_models/gmp_expanse_amd_c8.json (every campaign:sector:L:graph key, 48,346). slurm/sweep.sh -> tools/sweep.py:
# a test-only plan of all 24,173 graphs, both campaigns, 2 replicates x 512 points, planned with J-SWEEP-1's measured
# cost model (R13; benchmarks/expanse_2026-10-c8/stage3b/sweep1.54641706.0/cost_model.json, Stage-3 baseline) and
# --shards 16 (the sweep is ~7 core-h at Stage-3 costs, so the default 1.5-h index sizing would put each group in
# one index and leave the node idle); --forbid-seeds-from $C8_SEEDS; the ledger registration (role sweep) before any
# index; --threads 8 with C8_LANES unset: 16 x 8 NUMA-pinned process slots (R5b, the P4 shape), heaviest first;
# merge (32 processes); the cost model and the campaign-keyed calibration rows (written to a copy in the evidence,
# never to the export's tools/calibration.json); sweep.sh adds the base seed to $C8_SEEDS. tools/accounting.py runs
# after this job has ended (sacct then has the final elapsed time).
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> SWEEP_SEED=<fresh, checked against both logs> [C8_SWEEP_RUN=<campaign dir>] sbatch --export=ALL [--exclude=<node>] s5e_sweep2.slurm
# (C8_SWEEP_RUN, default $C8_DATA/sweep2e-<sha12>, was added after the export for the rerun on another node; the rerun job
# ran this uploaded copy, whose sha256 is in admission/submitted.txt.)
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}" "${SWEEP_SEED:?}" "${C8_SEEDS:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=s5esweep2.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
W=${C8_SWEEP_RUN:-$C8_DATA/sweep2e-$TAG}
CM1=$C8_PACKAGE/benchmarks/expanse_2026-10-c8/stage3b/sweep1.54641706.0/cost_model.json
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; campaign $W; J-SWEEP-1 cost model $CM1; evidence $E"
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
{ hostname; lscpu; numactl --hardware 2>&1; } > "$E/node.txt" 2>&1; grep -E 'Model name|NUMA node\(s\)' "$E/node.txt"
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS GMP_PREFIX NUMERICS C8_LANES
cd "$C8_PACKAGE" || exit 64
sha256sum bin/c8d2_gmp "$CM1" | tee "$E/binaries.sha256"
[ "$(sha256sum bin/c8d2_gmp | cut -c1-64)" = 1d2a218147ef52b5d0ac37dd8aaead55045ab4fe68e48ec963ea4b8e93024faa ] || { echo "bin/c8d2_gmp is not the final default binary" >&2; exit 3; }
python3 -B tools/seeds.py check "$SWEEP_SEED" > "$E/seed_check_before.txt" 2>&1; sc=$?; cat "$E/seed_check_before.txt"
[ $sc -eq 0 ] || { echo "SWEEP_SEED=$SWEEP_SEED is forbidden or unreadable (seeds.py check exit $sc); nothing planned" >&2; exit 64; }
cp "$C8_SEEDS" "$E/seeds_before.json"
cp tools/calibration.json "$E/calibration_before.json"; cp tools/calibration.json "$E/calibration.json"
S=/scratch/$USER/job_$SLURM_JOB_ID; [ -d "$S" ] || S=${TMPDIR:-/tmp}; echo "node-local scratch $S"
t0=$(date +%s); status=0
bash slurm/sweep.sh "$W" --seed "$SWEEP_SEED" --points 512 --replicates 2 --threads 8 --cost-model "$CM1" --shards 16 \
  --forbid-seeds-from "$C8_SEEDS" --merge-jobs 32 --cost-model-out "$E/cost_model.json" --calibration "$E/calibration.json" --scratch "$S" \
  > "$E/sweep.stdout" 2>&1 || status=$?
echo "sweep exit $status after $(( $(date +%s) - t0 )) s"; tail -25 "$E/sweep.stdout"
cp "$W/manifest.json" "$E/manifest.json"; cp "$W/submissions.jsonl" "$E/submissions.jsonl"; cp "$C8_SEEDS" "$E/seeds_after.json"
python3 -B tools/production.py status "$W" --json > "$E/status.json" 2>&1 || true
python3 -B tools/ledger.py list "$W" > "$E/ledger_list.txt" 2>&1 || true
python3 - "$E/cost_model.json" <<'PY' || status=3
import json, sys
m = json.load(open(sys.argv[1])); k = m['seconds_per_point']
print(json.dumps({'keys': len(k), 'keys_field': m.get('keys'), 'executable_sha256': m.get('executable_sha256'), 'lane_width': m.get('lane_width'),
                  'cpu_models': m.get('cpu_models'), 'hosts': m.get('hosts'), 'job_ids': m.get('job_ids'), 'cpu_class_factors': m.get('cpu_class_factors')}))
sys.exit(0 if len(k) == 48346 and m.get('executable_sha256', '').startswith('1d2a2181') else 3)
PY
echo "finished $(date -Is), status $status"
exit $status
