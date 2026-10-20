#!/bin/bash
#SBATCH -A <ACCOUNT> -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=4 --mem=16G -t 00:15:00 --no-requeue
#SBATCH -J c8d2-s4c-exp1-probecheck
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# R4c `exp1` development pre-check of the probe (never evidence of a gate): in a working-tree copy C8_PRECHECK already
# built by s4c_precheck.slurm (bin/c8d2_gmp and bin/c8d2_gmp_exp1 with their build records), compile
# dev_exp1/scripts/exp1_probe.cpp with each executable's compile command (exp1_probe.py --compile-only).
# Usage: C8_PRECHECK=<tree> sbatch --export=ALL exp1_probecheck.slurm   (submit_exp1.sh probecheck does this)
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PRECHECK:?}"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); tree $C8_PRECHECK"
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS C8_INPUTS GMP_PREFIX NUMERICS
cd "$C8_PRECHECK" || exit 64
python3 -B benchmarks/expanse_2026-10-c8/stage4c/dev_exp1/scripts/exp1_probe.py --compile-only --output "$C8_PRECHECK/probecheck_$SLURM_JOB_ID"; st=$?
echo "finished $(date -Is), status $st"; exit $st
