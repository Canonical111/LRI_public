#!/bin/bash
#SBATCH -p amdq
#SBATCH -N 1 --exclusive
#SBATCH -t 12:00:00
#SBATCH --mem=240G
#SBATCH -J sri_eng_plan_run
#SBATCH -o <SCRATCH>/sri_c6c7/engine/logs/%x_%j.out
# Plan (lattice searches run here, not on the login node) and run a spec: sbatch plan_and_run_symmetry.sbatch SPEC RUNDIR
ROOT=<SCRATCH>/sri_c6c7/engine
SPEC=$1; RUNDIR=$2
source /etc/profile.d/modules.sh; module load anaconda3/2023.07-2
cd $ROOT && python py/campaign.py plan "$SPEC" "$RUNDIR" || exit 1
bash $ROOT/slurm/run_list.sh "$ROOT/$RUNDIR" "$ROOT/$RUNDIR/cfglist.txt" 1 1000000
