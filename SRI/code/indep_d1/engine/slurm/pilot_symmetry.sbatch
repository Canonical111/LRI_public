#!/bin/bash
#SBATCH -p amdq
#SBATCH -N 1 --exclusive
#SBATCH -t 06:00:00
#SBATCH --mem=240G
#SBATCH -J sri_engine_pilot
#SBATCH -o <SCRATCH>/sri_c6c7/engine/logs/%x_%j.out
# usage: sbatch [-J name] pilot_symmetry.sbatch RUNDIR FIRST LAST
ROOT=<SCRATCH>/sri_c6c7/engine
RUNDIR=$1; FIRST=${2:-1}; LAST=${3:-1000000}
bash $ROOT/slurm/run_list.sh "$ROOT/$RUNDIR" "$ROOT/$RUNDIR/cfglist.txt" "$FIRST" "$LAST"
