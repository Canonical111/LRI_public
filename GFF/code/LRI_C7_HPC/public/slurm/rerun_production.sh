#!/bin/bash
# Full C7(1) production rerun with the package's own tools and Slurm templates (cluster/*.slurm), as run on SDSC Expanse
# in September 2026. Cost: about 2.6e5 core-hours (about 640 per batch x 399 batches, 20 for the primitive campaign,
# 60 for the final combination). Run this driver on a login node: planning is metadata only (seconds per batch).
# Placeholders: <ACCOUNT>, <PARTITION> (a shared partition with 16-CPU allocations), <SCRATCH> (durable filesystem
# shared by all nodes), <ENV_SETUP> (modules + venv; Python >= 3.8 with numpy/scipy/mpmath, GCC >= 9 with quadmath,
# Boost multiprecision headers), <GFF> (the public GFF/ checkout).
#
# SEED_TAG=C7-expanse-2026-09 replays the published random streams (same seeds; replicate values identical only with
# the same binary build, executable sha256 33bab738..., and the same SciPy for the Sobol nets; file hashes also depend on
# the absolute executable path that the manifests record). Any other tag gives an independent rerun of the same design.
# The production submitted batches in waves of at most 20 active batches until the pre-registered stop (400 batches,
# or 2026-09-29 06:00 PDT, or 300,000 SU); b215 was never submitted (truncated input copy at planning) and is excluded.
set -euo pipefail
ACCOUNT=${ACCOUNT:-<ACCOUNT>}; PARTITION=${PARTITION:-<PARTITION>}; W=${W:-<SCRATCH>/c7_hpc}
SEED_TAG=${SEED_TAG:-C7-expanse-2026-09}; FIRST=${FIRST:-1}; LAST=${LAST:-400}; SKIP=${SKIP:-215}
export C7_ROOT=${C7_ROOT:-<GFF>/code/LRI_C7_HPC} C7_ENV_SETUP=${C7_ENV_SETUP:-<ENV_SETUP>}
source "$C7_ENV_SETUP"
DESIGN="$C7_ROOT/../../results/C7_1/design_v1.json"   # frozen design, sha256 fd356a15ec4cc8eaa829ee9d4a6cfbc8d2e592ce10c1739769a0700fb668fb0e
mkdir -p "$W/batches" "$W/primitive" "$W/logs"
make -C "$C7_ROOT" RPATH=1                              # e.g. CPPFLAGS=-I$BOOST_ROOT/include for a module Boost
seed_of() { python3 -c "import hashlib,sys;print(int.from_bytes(hashlib.sha256(sys.argv[1].encode()).digest()[:8],'little'))" "$1"; }

# 1. batches: 55 array elements of 16 CPUs each (3 h wall limit), then an afterany merge (fails closed if incomplete)
for k in $(seq "$FIRST" "$LAST"); do
  [[ " $SKIP " == *" $k "* ]] && continue
  b=$(printf 'b%03d' "$k"); export C7_PRODUCTION="$W/batches/$b"
  python3 "$C7_ROOT/tools/production.py" plan "$C7_PRODUCTION" --seed "$(seed_of "$SEED_TAG:batch:$k")" --label "$b" \
      --threads 16 --design "$DESIGN" --refine7 --extra-inputs "$C7_ROOT/inputs_extra"
  JOBS=$(python3 -c 'import json,os;print(len(json.load(open(os.environ["C7_PRODUCTION"]+"/production.json"))["jobs"]))')
  JOB=$(sbatch --parsable -A "$ACCOUNT" -p "$PARTITION" --nodes=1 --ntasks=1 --cpus-per-task=16 --mem=16G -t 03:00:00 \
      --array="0-$((JOBS-1))" --export=ALL --output="$W/logs/c7-%A_%a.log" "$C7_ROOT/cluster/production.slurm")
  sbatch -A "$ACCOUNT" -p "$PARTITION" --nodes=1 --ntasks=1 --cpus-per-task=1 --mem=8G -t 01:00:00 --export=ALL \
      --dependency="afterany:${JOB%%;*}" --output="$W/logs/merge-%j.log" "$C7_ROOT/cluster/merge.slurm"
done

# 2. direct primitive campaign P1: 44 L7 primitive classes, 2^23 points each, 64 replicates (360,448 work units)
PS=$(seed_of "${SEED_TAG}:primitive")
python3 "$C7_ROOT/tools/campaign.py" plan --out "$W/primitive/P1" --mode qmc --L 7 --selection primitive \
    --points 8388608 --replicates 64 --seed "$PS" --matrix-seed "$((PS ^ 0x17219317))" --rate .8 \
    --shards 16 --threads 16 --chunk-points 65536
export C7_CAMPAIGN="$W/primitive/P1"
PJOB=$(sbatch --parsable -A "$ACCOUNT" -p "$PARTITION" --nodes=1 --ntasks=1 --cpus-per-task=16 --mem=16G -t 03:00:00 \
    --array=0-15 --export=ALL --output="$W/logs/p1-%A_%a.log" "$C7_ROOT/cluster/campaign.slurm")
sbatch -A "$ACCOUNT" -p "$PARTITION" --nodes=1 --ntasks=1 --cpus-per-task=1 --mem=8G -t 01:00:00 \
    --dependency="afterany:${PJOB%%;*}" --output="$W/logs/p1-merge-%j.log" \
    --wrap "source $C7_ENV_SETUP && python3 $C7_ROOT/tools/campaign.py merge $W/primitive/P1"

# 3. after every merge has succeeded (resubmit failed elements once with --array=<ids>, then rerun the merge):
#   sbatch -A <ACCOUNT> -p <PARTITION> --nodes=1 --ntasks=1 --cpus-per-task=16 --mem=32G -t 04:00:00 \
#     --wrap "source <ENV_SETUP> && cd $W && python3 $C7_ROOT/tools/combine.py batches/b* --primitive primitive/P1 \
#             --output final/v2 --jobs 16"
# The output directory must lie two levels below $W for the relative paths of the published C7_final.json.
# Compare final/v2/C7_final.json with <GFF>/results/C7_1/C7_final.json (same seeds, nets and binary: every number equal).
echo "planned and submitted batches $FIRST-$LAST (skip $SKIP) and P1 under $W"
