#!/bin/bash
# Freeze the density-basis (keep-24 artifacts trained at L=24) campaign manifests: dens16 lo/mid/hi8/hi16 + dens24 controls.
set -euo pipefail
export LRI_CODE_DIR=$HOME/lri_dressed/code/basisint-038c630d
source "$LRI_CODE_DIR/cluster/symmetry/env.sh"
cd "$LRI_CODE_DIR"; R=$LRI_ROOT; B=$R/bases/dens_v1
files=$(ls $B/x*_L24_teacher48_keep24_o384_*.json | grep -E "_[0-9a-f]{12}\.json$")
[ -f $B/index.json ] || python scripts/index_bases.py --files $files --output $B/index.json
D="0.249 0.24 0.225 0.2 0.175 0.15 0.125 0.1 0.075 0.05 0.025 0.01 0.001"
common="--pack --osc 384 --windows vacuum:consistent --split points --backend ladder --basis-index $B/index.json --seed-dir $R/seeds/dens_v1_all"
mk(){ c=$1; shift; mkdir -p $R/campaigns/$c; python scripts/make_campaign.py $common --campaign $c --out $R/campaigns/$c/manifest.json "$@"; }
mk dens16_lo   --nz 16 --deltas $D --bath-cuts 12 14 16 18 20 22 24 26 28 --threads 1  --mem-gib 4  --est-seconds 3600
mk dens16_mid  --nz 16 --deltas $D --bath-cuts 30 32                      --threads 4  --mem-gib 6  --est-seconds 10800
mk dens16_hi8  --nz 16 --deltas $D --bath-cuts 34 36                      --threads 8  --mem-gib 8  --est-seconds 21600
mk dens16_hi16 --nz 16 --deltas $D --bath-cuts 38 40                      --threads 16 --mem-gib 12 --est-seconds 36000
mk dens24_ctl  --nz 24 --deltas 0.1 0.05 0.025 0.01 --bath-cuts 36 40     --threads 16 --mem-gib 12 --est-seconds 36000
