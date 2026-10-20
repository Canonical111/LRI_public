#!/bin/bash
#SBATCH -p amdq
#SBATCH -N 1 --exclusive
#SBATCH -t 23:50:00
#SBATCH --mem=240G
#SBATCH -J sri_eng_packed
#SBATCH -o <SCRATCH>/sri_c6c7/engine/logs/%x_%A_%a.out
# Packed array on symmetry amdq: task i runs lines [(i-1)*L+1, i*L] of RUNDIR/LISTFILE concurrently with NPAR
# workers (slurm/run_packed.sh).  For strict re-checks / refinements made of many single-sector cfgs.
#   sbatch -J NAME --array=1-NTASK slurm/packed_symmetry.sbatch RUNDIR LINES_PER_TASK NPAR [LISTFILE]
ROOT=<SCRATCH>/sri_c6c7/engine
RUNDIR=$1; L=${2:-1000}; NPAR=${3:-8}; LIST=${4:-cfglist.txt}
i=${SLURM_ARRAY_TASK_ID:-1}
FIRST=$(( (i-1)*L + 1 )); LAST=$(( i*L ))
bash $ROOT/slurm/run_packed.sh "$ROOT/$RUNDIR" "$ROOT/$RUNDIR/$LIST" "$NPAR" "$FIRST" "$LAST"
