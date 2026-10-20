#!/bin/bash
# Fresh repetitions with the documented seeds. Workdir must not already exist.
# Independent chains are statistically reproducible across compatible builds;
# bitwise identity requires the saved executable hash / standard library.
set -euo pipefail
cd "$(dirname "$0")"
root=$(cd .. && pwd)
work=${1:?Usage: reproduce_pilots.sh /new/output/directory [workers]}
workers=${2:-4}
[[ ! -e "$work" ]] || { echo 'Refusing to overwrite existing output' >&2; exit 1; }
mkdir -p "$work"
work=$(cd "$work" && pwd)
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
python3 prepare.py --out "$work/pilot2d" --dim 2 --s 1.4 --sizes 32 64 128 \
 --centers "$root/reference/largest_pair_crossing_centers.csv" --replicas 2 \
 --measurements 100000 --warmup 10000 --beta-points 3 --beta-halfwidth .0008 \
 --seed-base 928162 --campaign-id precision-v2-local-2d
python3 prepare.py --out "$work/pilot3d" --dim 3 --s 1.8 --sizes 8 16 32 \
 --centers "$root/reference/largest_pair_crossing_centers.csv" --replicas 2 \
 --measurements 100000 --warmup 10000 --beta-points 3 --beta-halfwidth .0004 \
 --seed-base 714692 --campaign-id precision-v2-local-3d
for d in 2 3; do
 s=1.4; [[ "$d" == 3 ]] && s=1.8
 python3 run_pack.py "$work/pilot${d}d" --workers "$workers"
 for b in 1000 2000; do
  python3 pack_histograms.py "$work/pilot${d}d" --block "$b"
  python3 precision_analysis.py "$work/pilot${d}d/hist_b${b}/index.json" \
    --dim "$d" --s "$s" --bootstrap 200 --out "$work/results/pilot${d}d_b${b}"
 done
done
