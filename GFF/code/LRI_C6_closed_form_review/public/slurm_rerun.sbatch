#!/bin/bash
# Fresh execution of the 49 check commands of the independent C6(1) review, then the replay on the fresh outputs.
# One core, < 2 GB; about 10-25 min. Submit from GFF/code/LRI_C6_closed_form_review:
#   sbatch public/slurm_rerun.sbatch
#SBATCH --job-name=c6review-rerun
#SBATCH --account=<ACCOUNT>
#SBATCH --partition=<PARTITION>
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=01:00:00
#SBATCH --output=<SCRATCH>/c6review-rerun-%j.out
set -euo pipefail
# environment: Python >= 3.10 with mpmath 1.3.0, sympy, numpy, scipy, e.g.
#   source <SCRATCH>/venv-c6/bin/activate
make -f public.mk rerun WORK=<SCRATCH>/c6review-work PY=python3
