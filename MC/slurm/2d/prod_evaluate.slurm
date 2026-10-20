#!/bin/bash
#SBATCH -J lri2d_eval
#SBATCH -A <ACCOUNT>
#SBATCH -p <PARTITION_SHARED>
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=2 --mem=16G
#SBATCH -t 02:00:00
#SBATCH -o <SCRATCH>/lri2d/logs/prod_eval_%j.out
# FIT_MODEL_2D §4: evaluator over the 8 primary (b=2000) and 16 reblock (b=1000, 4000) records; fresh immutable output directory.
set -uo pipefail
source /etc/profile.d/modules.sh; module purge >/dev/null 2>&1; <LOAD_MODULES> || exit 1  # site modules: gcc >= 10, Python 3 with NumPy/SciPy
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
cd <CODE_2D> || exit 1
CAMP=<SCRATCH>/lri2d/prod2d
P=(); R=(); for s in 1.05 1.1 1.2 1.3 1.4 1.5 1.6 1.7; do P+=($CAMP/analysis_b2000_s$s); R+=($CAMP/analysis_b1000_s$s $CAMP/analysis_b4000_s$s); done
miss=0; for d in "${P[@]}" "${R[@]}"; do [ -s $d/results.json ] || { echo "missing $d/results.json"; miss=$((miss+1)); }; done
echo "$(date) records missing: $miss (evaluator labels missing reblocks REBLOCKING UNAVAILABLE; missing primaries stop here)"
for d in "${P[@]}"; do [ -s $d/results.json ] || { echo "a primary record is missing; exit 67"; exit 67; }; done
OUT=$CAMP/evaluation_$(date +%Y%m%d_%H%M%S)
python3 evaluate_2d.py --primary "${P[@]}" --reblock "${R[@]}" --plan <CODE_2D>/FIT_MODEL_2D.md --manifest $CAMP/manifest.json --centers <CODE_2D>/production_centers.csv --out $OUT
rc=$?; echo "$(date) evaluate exit $rc -> $OUT"; ls $OUT 2>/dev/null; exit $rc
