#!/bin/bash
# One manifest item per array task: critical search, exact alpha-derivative and window audit, written to
# <OUTPUT_DIR>/<item id>/result.json. Re-submitting the same array resumes from the checkpoints (--resume).
# Template: replace the <...> placeholders (slurm/README.md). Submit with --array=0-<number of items - 1>.
# Threads: the manifest fixes each item's thread count (1 if K*n_b <= 1000, 2 if < 1600, else 4); request at least the
# largest one. Memory: the largest production item peaked at 495 MiB. Wall time: the longest item took 2.7 h on one
# AMD EPYC 7543 core group.
#SBATCH --job-name=nrg-items
#SBATCH --account=<ACCOUNT>
#SBATCH --partition=<PARTITION>
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=4G
#SBATCH --time=06:00:00
#SBATCH --signal=B:USR1@300
#SBATCH --no-requeue
#SBATCH --output=nrg-items-%A_%a.log
set -euo pipefail
<LOAD_MODULES>                                   # the same environment as the validation job
CODE=<CODE_DIR>                                  # the same read-only code copy that issued the receipt
MANIFEST=<MANIFEST>                              # frozen by scripts/make_manifest.py against RECEIPT
RECEIPT=<SCRATCH>/nrg/validation/<VALIDATION_JOB_ID>/receipt.json
OUTPUT_DIR=<SCRATCH>/nrg/runs/<CAMPAIGN>
mkdir -p "$OUTPUT_DIR"
export PYTHONPATH="$CODE/src" OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
# exec: the solver itself receives Slurm's USR1 warning, checkpoints and exits with code 75 before the wall limit.
exec python -m lri_spin item --manifest "$MANIFEST" --validation-receipt "$RECEIPT" --output-dir "$OUTPUT_DIR" --resume
