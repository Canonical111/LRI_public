#!/bin/bash
# Validation on a compute node of the target cluster: checksum list of the code, the 85-test suite, then a validation
# receipt that binds the solver source to this node's runtime (Python, NumPy, SciPy, BLAS). Every production item must
# run on nodes with the same runtime as the receipt. Template: replace the <...> placeholders (slurm/README.md).
#SBATCH --job-name=nrg-validate
#SBATCH --account=<ACCOUNT>
#SBATCH --partition=<PARTITION>
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --no-requeue
#SBATCH --output=nrg-validate-%j.log
set -euo pipefail
<LOAD_MODULES>                                   # e.g. a Python >= 3.10 module and a venv with pytest
CODE=<CODE_DIR>                                  # a read-only copy of NRG/code/lri_spin_boson_hpc
OUT=<SCRATCH>/nrg/validation/$SLURM_JOB_ID
mkdir -p "$OUT"
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS="-p no:cacheprovider"
cd "$CODE"
hostname > "$OUT/host.txt"; lscpu > "$OUT/lscpu.txt"
python tests/verify_manifest.py
python scripts/validate_release.py --output "$OUT/receipt.json"   # runs the pytest suite (85 tests), then issues the receipt
echo "Receipt: $OUT/receipt.json"
