#!/usr/bin/env bash
# Run every lane of a dispatch index: one tools/hpc_dispatch.py lane per Slurm task, 16 lanes x 8 threads per
# 128-core node (prod1: 6 exclusive AMD EPYC 7742 nodes, 12 h 44 min; 1,989 of 1,994 jobs, the last 5 deferred at
# the deadline and finished by a second, smaller index, see index_tail.slurm). Resubmitting this script on the same
# index continues a campaign: receipted jobs are verified and skipped.
#   --signal=TERM@600 and C8OPT_GRACE=600: a lane stops 10 min before the limit, releases its locks and exits 143.
#   C8_DEADLINE_FACTOR=6: the index costs are pilot-host seconds; the EPYC 7742 needed about 3.8x that per point.
#SBATCH --job-name=c8opt-lanes
#SBATCH --account=<ACCOUNT>
#SBATCH --partition=<PARTITION_NODE>
#SBATCH --nodes=<NODES> --ntasks-per-node=16 --cpus-per-task=8 --exclusive --mem=<NODE_MEM>
#SBATCH --time=13:00:00
#SBATCH --signal=TERM@600
#SBATCH --no-requeue
#SBATCH --output=c8opt-lanes-%j.out
set -euo pipefail
source "${C8_ENV:?set C8_ENV to your filled env.sh}"; [[ "${C8_ENV_OK:-}" == 1 ]] || exit 65
NAME="<NAME>"
for v in "$NAME" ${SEED:+"$SEED"} ${LANES:+"$LANES"}; do [[ "$v" != *"<"* ]] || { echo "fill the placeholders first" >&2; exit 64; }; done
cd "$C8_PACKAGE"
DISPATCH="$C8_ROOT/dispatch/$NAME"
export C8OPT_GRACE=600 C8_DEADLINE_FACTOR=6
export OPENBLAS_NUM_THREADS=1 OMP_DYNAMIC=FALSE OMP_PROC_BIND=close OMP_PLACES=cores C8_GRAPH_BATCH=8
echo "lanes: job $SLURM_JOB_ID nodes $SLURM_JOB_NODELIST tasks $SLURM_NTASKS x $SLURM_CPUS_PER_TASK; $(date -u +%FT%TZ)"
set +e
srun --cpu-bind=cores --kill-on-bad-exit=0 bash -c '
  set -euo pipefail
  S="$C8_LOCAL_SCRATCH/job_$SLURM_JOB_ID"; mkdir -p "$S/tmp"; export TMPDIR="$S/tmp"
  exec "$C8_PYTHON" -B tools/hpc_dispatch.py run "'"$DISPATCH"'" --lane "$SLURM_PROCID" \
       --threads "$SLURM_CPUS_PER_TASK" --scratch "$S"
'
rc=$?
echo "lanes: srun exit $rc; $(date -u +%FT%TZ); lane summaries in $DISPATCH/runs/"
exit $rc
