#!/bin/bash
#SBATCH -A yun124 -p compute -N 1 --ntasks=1 --cpus-per-task=128 --exclusive --mem=240G -t 00:45:00 --no-requeue
#SBATCH -J c8d2-g4b-val2
#SBATCH -o /expanse/lustre/scratch/zzheng8/temp_project/c8d2/logs/%x_%j.out
# Stage 4b, G4b: the plan's J-VAL-2 on the final default binary, one exclusive Expanse compute node (2 x EPYC 7742,
# site deviation U1). Exactly the plan's command, `make test-full OUTPUT=<evidence>/val2`:
#   tests/validate.py --full   A-KER-1/2/3/5, G-REF/G-C7/G-JET = A-RPL-1/2/3 on the L=2 graph and all 3,773 L3-L7
#                              kernels with both backends (against make c7ref), the chunk and layout part of A-RPL-6,
#                              class B, the diagnostic builds (32 jobs x 4 threads on 128 cores);
#   tests/check_points.py      450-digit point checks L3-L8 (< 1e-280);
#   tests/check_inputs.py, tests/workflow.py, tests/staging.py.
# Executables from final_build.slurm in the same export; their sha256 are recorded before and after (make must not
# rebuild them). Scratch (TMPDIR) on node-local NVMe.
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> sbatch --export=ALL --dependency=afterok:<build job> g4b_val2.slurm
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=g4bval2.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E"
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
{ hostname; lscpu; numactl --hardware 2>&1; } > "$E/node.txt" 2>&1; grep -E 'Model name|NUMA node\(s\)' "$E/node.txt"
L=/scratch/$USER/job_$SLURM_JOB_ID; [ -d "$L" ] || { echo "no node-local scratch $L" >&2; exit 69; }
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 TMPDIR=$L/tmp; mkdir -p "$TMPDIR"
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS GMP_PREFIX
cd "$C8_PACKAGE" || exit 64
X="bin/c8d2_decimal bin/c8d2_gmp bin/c8d2_gmp_prof bin/c8d2_gmp_ratiohist bin/c8d2_inspect bin/ref/c7d2_decimal bin/ref/c7d2_gmp"
sha256sum $X | tee "$E/binaries_before.sha256"
t=$(date +%s); echo "== make test-full $(date -Is)"
make test-full OUTPUT="$E/val2" > "$E/make_test_full.log" 2>&1; c=$?
echo "== make test-full exit $c after $(( $(date +%s) - t )) s"
grep -E 'passed in|passed|FAILED|Error|error' "$E/make_test_full.log" | cut -c1-300 | head -60
sha256sum $X > "$E/binaries_after.sha256"
if cmp -s "$E/binaries_before.sha256" "$E/binaries_after.sha256"; then echo "executables unchanged by make test-full"; else echo "executables CHANGED during make test-full" >&2; c=3; fi
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $c"
exit $c
