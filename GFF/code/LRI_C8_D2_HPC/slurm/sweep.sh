#!/bin/bash
#SBATCH --job-name=c8d2-sweep
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --exclusive
#SBATCH --time=02:00:00
#SBATCH --no-requeue
#SBATCH --output=c8d2-sweep-%j.log
# The cost-model sweep job (J-SWEEP-1/2; PLAN component D, P5) on one whole node: tools/sweep.py plans the test-only
# sweep campaign (all graphs, both campaigns), registers its base seed in $C8_SEEDS and this job in its ledger (role
# sweep; both right after the plan, before any index runs: a sweep stopped or failing later still forbids its seed, Y13),
# runs every index on NUMA-pinned process slots, merges, writes the measured cost model and the campaign-keyed
# calibration rows; this script then adds the seed again (idempotent: 'present'). Synchronize the seed logs afterwards
# (benchmarks/symmetry_2026-10-c8/stage5/scripts/seedsync.sh). Run tools/accounting.py on the campaign after the job
# has ended (sacct then has its final elapsed time).
#   sbatch [site options] slurm/sweep.sh RUN <tools/sweep.py arguments>
#   J-SWEEP-1 (no cost model yet, R13): ... slurm/sweep.sh $RUN --seed <fresh> --points 512 --replicates 2 --threads T \
#       --bootstrap-chunk 512 --shards 8 --cost-model-out $RUN.cost_model.json
#   J-SWEEP-2: the same with --cost-model <J-SWEEP-1's cost model> instead of --bootstrap-chunk/--shards.
#   symmetry (8 x 8 lanes): sbatch -p amdq --exclude=cn112 --exclusive --mem=245G -t 02:00:00 slurm/sweep.sh ... --threads 8
#   Expanse (8 x 16):       sbatch -A yun124 -p compute --ntasks=1 --cpus-per-task=128 --mem=240G -t 02:00:00 slurm/sweep.sh ... --threads 16
#   (Expanse with --threads 8: 16 x 8 process slots, the P4 shape.)
# --threads is the slot width: with C8_LANES unset each AMD NUMA node is split into the fewest equal slots of at most
# --threads cores (R5b); with an explicit C8_LANES each slot gets at most --threads CPUs of its lane.
set -eo pipefail
if [[ -n "${C8_ENV_SETUP:-}" ]]; then [[ -r "$C8_ENV_SETUP" ]] || { echo "C8: cannot read C8_ENV_SETUP=$C8_ENV_SETUP" >&2; exit 64; }; source "$C8_ENV_SETUP"; fi
set -u
PY="${C8_PYTHON:-python3}"
: "${C8_PACKAGE:?Set C8_PACKAGE to the package directory}"
: "${C8_SEEDS:?Set C8_SEEDS to the forbidden-seed log (tools/seeds.py init creates it)}"
[[ $# -ge 1 ]] || { echo "usage: slurm/sweep.sh RUN <tools/sweep.py arguments>" >&2; exit 64; }
run="$1"; shift
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
echo "C8: sweep job ${SLURM_JOB_ID:-local} on $(hostname) at $(date -u +%FT%TZ); package $C8_PACKAGE; run $run"
"$PY" -B "$C8_PACKAGE/tools/sweep.py" "$run" --seeds-log "$C8_SEEDS" "$@"
"$PY" -B "$C8_PACKAGE/tools/seeds.py" add "$run"
echo "C8: sweep finished at $(date -u +%FT%TZ); next: python3 -B $C8_PACKAGE/tools/accounting.py $run --output <file> (after the job has ended)"
