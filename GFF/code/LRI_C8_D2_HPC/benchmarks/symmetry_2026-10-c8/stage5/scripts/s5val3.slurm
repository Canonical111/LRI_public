#!/bin/bash
#SBATCH -p amdq --exclude=cn112 -N 1 -n 1 --exclusive --mem=245G -t 03:00:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# Final J-VAL-3 and A-RPL-7 on symmetry (PLAN template, -t 03:00:00). Each command writes its own record; every one runs,
# and the job fails if any fails.
#   l2_control        tests/validate.py --l2-control (A-IN-6(b)) with a FRESH seed C8_L2_SEED drawn for this job and
#                     registered in both sites' seed logs and the mirror BEFORE submission (checked here: seeds.py check
#                     must say forbidden).
#   thread_identity   tests/thread_identity.py (A-RPL-6): L8 free and power blocks at 1, 8, 16, 64 threads and 8 x 8 lanes.
#   bk8               tests/validate.py --bk8 (A-RPL-4): L7 and L8, 400 kernels per sector, decimal against gmp.
#   l8self            tests/validate.py --l8self bin/baseline (A-RPL-7 G-L8SELF): the L8 sample against the symmetry
#                     Stage-3 baseline built from tag c8-stage3 in s5build; exact.
#   forced_tiers      tests/forced_tiers.py (A-RPL-5).
#   quad_differential tests/quad_differential.py (R3a's differential proof on this GCC 11.4 build).
#   merge_scale       tests/merge_scale.py --rows 1000000 (A-ORC-6).
#   assembly_checks   tests/assembly_checks.py --exact (A-ASM-4, cluster part).
# Usage: C8_PACKAGE=... C8_L2_SEED=<fresh registered seed> sbatch --export=ALL --dependency=afterok:<s5build> -J c8d2-s5val3 s5val3.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}" "${C8_L2_SEED:?}"
D=<SCRATCH>/c8d2; TAG=$(basename "$C8_PACKAGE"); RUN=s5val3.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$D/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E"
{ hostname; lscpu; numactl --hardware 2>&1; df -h /tmp; } > "$E/node.txt" 2>&1; grep -E 'Model name|NUMA node\(s\)' "$E/node.txt"
sha256sum "$HOME/c8d2/env.sh" | tee "$E/env.sha256"
export TMPDIR=/tmp/c8d2_$SLURM_JOB_ID OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"
unset C8_INPUTS CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS GMP_PREFIX NUMERICS
python3 -B "$C8_PACKAGE/tools/seeds.py" check "$C8_L2_SEED" > "$E/l2_seed_check.txt" 2>&1; sc=$?
cat "$E/l2_seed_check.txt"; [ $sc -eq 1 ] || { echo "C8_L2_SEED=$C8_L2_SEED is not in the forbidden-seed log $C8_SEEDS (seeds.py check exit $sc); refusing an unregistered seed" >&2; exit 64; }
cd "$C8_PACKAGE" || exit 64
sha256sum bin/c8d2_decimal bin/c8d2_gmp bin/baseline/c8d2_decimal bin/baseline/c8d2_gmp bin/c8d2_quad_differential bin/c8d2_quad_ranges | tee "$E/binaries.sha256"
status=0
run() { local name=$1; shift; local t=$(date +%s); echo "== $name $(date -Is)"; "$@" > "$E/$name.stdout" 2>&1; local c=$?
        echo "== $name exit $c after $(( $(date +%s) - t )) s"; tail -3 "$E/$name.stdout" | cut -c1-300; [ $c -eq 0 ] || status=1; return 0; }
run l2_control python3 -B tests/validate.py --only none --l2-control --l2-seed "$C8_L2_SEED" --threads 64 --output "$E/l2_control.json"
run thread_identity python3 -B tests/thread_identity.py --output "$E/thread_identity.json"
run bk8 python3 -B tests/validate.py --only none --bk8 --jobs 16 --threads 4 --output "$E/bk8.json"
run l8self python3 -B tests/validate.py --only none --l8self bin/baseline --jobs 16 --threads 4 --output "$E/l8self.json"
run forced_tiers python3 -B tests/forced_tiers.py --threads 64 --output "$E/forced_tiers.json"
run quad_differential python3 -B tests/quad_differential.py --output "$E/quad_differential.json" --threads 64 --scratch "$TMPDIR"
run merge_scale python3 -B tests/merge_scale.py --rows 1000000 --jobs 16 --run-jobs 16 --shards 16 --output "$E/merge_scale.json"
run assembly_checks python3 -B tests/assembly_checks.py --exact --output "$E/assembly_checks_exact.json" --provenance "$E/exact_check_provenance.json"
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $status"
exit $status
