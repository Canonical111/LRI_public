#!/bin/bash
#SBATCH -p amdq
#SBATCH -N 1 --exclusive
#SBATCH -t 23:50:00
#SBATCH --mem=240G
#SBATCH -J sri_eng_c8pilot
#SBATCH -o <SCRATCH>/sri_c6c7/engine/logs/%x_%A_%a.out
# C8 pilot on symmetry (amdq first; defq if amdq is down/full: pass -p defq --mem=180G on the sbatch line).
# Task i runs line i of RUNDIR/LISTFILE (one cfg per task, all cores of the node).
#   sbatch --array=1-NT%MAX slurm/pilot_C8_symmetry.sbatch RUNDIR LISTFILE
ROOT=<SCRATCH>/sri_c6c7/engine
RUNDIR=$1; LIST=${2:-cfglist.txt}
i=${SLURM_ARRAY_TASK_ID:-1}
bash $ROOT/slurm/run_list.sh "$ROOT/$RUNDIR" "$ROOT/$RUNDIR/$LIST" "$i" "$i"
