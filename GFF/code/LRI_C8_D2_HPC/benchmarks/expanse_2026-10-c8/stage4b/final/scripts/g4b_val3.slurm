#!/bin/bash
#SBATCH -A yun124 -p compute -N 1 --ntasks=1 --cpus-per-task=128 --exclusive --mem=240G -t 01:00:00 --no-requeue
#SBATCH -J c8d2-g4b-val3
#SBATCH -o /expanse/lustre/scratch/zzheng8/temp_project/c8d2/logs/%x_%j.out
# Stage 4b, G4b: the plan's J-VAL-3 and A-RPL-7 on the final default binary, one exclusive Expanse compute node
# (site deviation U1). Each command writes its own record; every one runs, and the job fails if any fails.
#   l2_control        tests/validate.py --l2-control (A-IN-6(b)) with the REGISTERED seed C8_L2_SEED of Stage 3
#                     (7082694491065029298, in $C8_SEEDS): the same sample as job 54637264, so the record must also
#                     equal Stage 3's (checked offline by summarize_final.py); no new seed is drawn.
#   thread_identity   tests/thread_identity.py (A-RPL-6): L8 free and power blocks at 1, 8, 16, 64 threads and 8 x 8 lanes.
#   bk8               tests/validate.py --bk8 (A-RPL-4): L7 and L8, 400 kernels per sector, decimal against gmp.
#   l8self            tests/validate.py --l8self bin/baseline (A-RPL-7): the L8 sweep sample against the Stage-3 baseline.
#   forced_tiers      tests/forced_tiers.py (A-RPL-5).
#   quad_differential tests/quad_differential.py (R3a's proof on this build; 2^32 pairs per operation, edge lists).
#   merge_scale       tests/merge_scale.py --rows 1000000 (A-ORC-6), as Stage 3b's 54643361 (16 jobs, 16 shards).
#   assembly_checks   tests/assembly_checks.py --exact (A-ASM-4, cluster part).
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> C8_L2_SEED=<registered seed> sbatch --export=ALL --dependency=afterok:<build> g4b_val3.slurm
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}" "${C8_L2_SEED:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=g4bval3.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E"
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
{ hostname; lscpu; numactl --hardware 2>&1; } > "$E/node.txt" 2>&1; grep -E 'Model name|NUMA node\(s\)' "$E/node.txt"
L=/scratch/$USER/job_$SLURM_JOB_ID; [ -d "$L" ] || { echo "no node-local scratch $L" >&2; exit 69; }
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 TMPDIR=$L/tmp; mkdir -p "$TMPDIR"
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS GMP_PREFIX
python3 -B "$C8_PACKAGE/tools/seeds.py" check "$C8_L2_SEED" > "$E/l2_seed_check.txt" 2>&1; sc=$?
cat "$E/l2_seed_check.txt"; [ $sc -eq 1 ] || { echo "C8_L2_SEED=$C8_L2_SEED is not in the forbidden-seed log (seeds.py check exit $sc); refusing to draw an unregistered seed" >&2; exit 64; }
cd "$C8_PACKAGE" || exit 64
sha256sum bin/c8d2_decimal bin/c8d2_gmp bin/baseline/c8d2_decimal bin/baseline/c8d2_gmp bin/c8d2_quad_differential bin/c8d2_quad_ranges | tee "$E/binaries.sha256"
status=0
run() { local name=$1; shift; local t=$(date +%s); echo "== $name $(date -Is)"; "$@" > "$E/$name.stdout" 2>&1; local c=$?
        echo "== $name exit $c after $(( $(date +%s) - t )) s"; tail -3 "$E/$name.stdout" | cut -c1-300; [ $c -eq 0 ] || status=1; return 0; }
run l2_control python3 -B tests/validate.py --only none --l2-control --l2-seed "$C8_L2_SEED" --threads 64 --output "$E/l2_control.json"
run thread_identity python3 -B tests/thread_identity.py --output "$E/thread_identity.json"
run bk8 python3 -B tests/validate.py --only none --bk8 --jobs 32 --threads 4 --output "$E/bk8.json"
run l8self python3 -B tests/validate.py --only none --l8self bin/baseline --jobs 32 --threads 4 --output "$E/l8self.json"
run forced_tiers python3 -B tests/forced_tiers.py --threads 128 --output "$E/forced_tiers.json"
run quad_differential python3 -B tests/quad_differential.py --output "$E/quad_differential.json" --threads 128 --scratch "$TMPDIR"
run merge_scale python3 -B tests/merge_scale.py --rows 1000000 --jobs 16 --run-jobs 16 --shards 16 --output "$E/merge_scale.json"
run assembly_checks python3 -B tests/assembly_checks.py --exact --output "$E/assembly_checks_exact.json" --provenance "$E/exact_check_provenance.json"
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $status"
exit $status
