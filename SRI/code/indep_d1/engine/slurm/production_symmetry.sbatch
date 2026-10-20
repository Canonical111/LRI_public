#!/bin/bash
#SBATCH -p amdq
#SBATCH -N 1 --exclusive
#SBATCH -t 23:50:00
#SBATCH --mem=240G
#SBATCH -J sri_eng_prod
#SBATCH -o <SCRATCH>/sri_c6c7/engine/logs/%x_%A_%a.out
# Production array on symmetry amdq (64 physical cores per node, whole node).
#   sbatch --array=1-NTASK%MAXRUN production_symmetry.sbatch RUNDIR LINES_PER_TASK [LISTFILE]
# Task i runs cfg lines [(i-1)*L+1, i*L] of RUNDIR/LISTFILE (default cfglist.txt, sorted longest first)
# sequentially, each with all 64 cores.  Outputs are published atomically and end with "complete": true; a
# finished cfg is skipped, so the same array can be resubmitted after a TIMEOUT/FAILED (only after sacct
# confirms it; never resubmit a PENDING/requeued task).  Non-zero exit if any cfg failed.
ROOT=<SCRATCH>/sri_c6c7/engine
RUNDIR=$1; L=${2:-1}; LIST=${3:-cfglist.txt}
i=${SLURM_ARRAY_TASK_ID:-1}
FIRST=$(( (i-1)*L + 1 )); LAST=$(( i*L ))
bash $ROOT/slurm/run_list.sh "$ROOT/$RUNDIR" "$ROOT/$RUNDIR/$LIST" "$FIRST" "$LAST"
