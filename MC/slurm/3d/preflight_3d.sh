#!/bin/bash
# 3D preflight (FIT_MODEL_3D §7): the 8 points × L ∈ {64, 128} × 5 production β (frozen D3 centres + w(L) = 1e-3 (L/16)^-1) × 2 replicas × 5e4 sweeps
# = 160 chains, run on whole nodes with the production pinning: L=128 one chain per CCX (taskset 0-127:4, 32 workers), L=64 packed (128 workers).
# Measures the 64->128 bracket position and ESS, the L=128 rate under production packing, and exercises the plan/array path. Login node: prepare only.
set -euo pipefail
source /etc/profile.d/modules.sh; <LOAD_MODULES> >/dev/null 2>&1  # site modules: gcc >= 10, Python 3 with NumPy/SciPy
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
C3=<SCRATCH>/lri3d; cd <CODE_2D>/code; mkdir -p $C3/logs
CAMP=$C3/preflight
[ -e $CAMP ] || python3 prepare.py --out $CAMP --dim 3 --s 1.55 1.6 1.7 1.75 1.8 1.85 1.9 1.95 --sizes 64 128 --centers <CODE_3D>/production_centers_3d.csv \
   --replicas 2 --measurements 50000 --warmup 5000 --beta-points 5 --beta-halfwidth 0.001 --window-exponent 1.0 --reference-length 16 \
   --seed-base 2026092150 --campaign-id preflight-3d-20260921 --sampler hybrid --record extended > $C3/logs/preflight_prepare.log 2>&1
echo "prepared $(ls $CAMP/chains | wc -l) chains"
# launch plans: array A = L=128 chains in slots of 32 (one per CCX); array B = the L=64 chains in 1 slot (128 workers)
python3 <CODE_3D>/make_plan.py $CAMP --lbig 128 --slot-big 32 --nslot-small 1 2>&1 | tail -3
ls $CAMP/logs/
