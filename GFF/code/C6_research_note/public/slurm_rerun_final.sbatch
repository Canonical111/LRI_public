#!/bin/bash
# Fresh run of the 22 final-method tasks of the C6(1) analytic package, then the comparison with the shipped records.
# One core, < 1 GB; about 2-4 min (the delivering sandbox needed 70 s of task time). Submit from GFF/code/C6_research_note:
#   sbatch public/slurm_rerun_final.sbatch
#SBATCH --job-name=c6analytic-rerun
#SBATCH --account=<ACCOUNT>
#SBATCH --partition=<PARTITION>
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:30:00
#SBATCH --output=<SCRATCH>/c6analytic-rerun-%j.out
set -euo pipefail
# environment: Python >= 3.10 with mpmath 1.3.0 and sympy 1.14.0 (requirements.txt), e.g.
#   source <SCRATCH>/venv-c6/bin/activate
make -f public.mk rerun-final WORK=<SCRATCH>/c6analytic-work PY=python3
