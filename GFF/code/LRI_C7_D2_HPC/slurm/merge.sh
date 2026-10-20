#!/usr/bin/env bash
#SBATCH --job-name=lri-c7-merge
#SBATCH --cpus-per-task=1
#SBATCH --time=01:00:00
#SBATCH --mem=4G
set -euo pipefail
: "${C7_PACKAGE:?}" "${C7_RUN:?}"
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
python3 "$C7_PACKAGE/tools/production.py" merge "$C7_RUN" --scratch "${SLURM_TMPDIR:-${TMPDIR:-/tmp}}"
python3 "$C7_PACKAGE/tools/assemble.py" "$C7_RUN" --bootstrap 4096
