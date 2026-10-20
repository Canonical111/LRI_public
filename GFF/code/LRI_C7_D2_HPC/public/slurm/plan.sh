#!/bin/bash
# Plan a C7(2) campaign with the flags of the 2026 production (run1-20260930-m4096). Run on a login or compute node.
#   C7_PACKAGE   this package (GFF/code/LRI_C7_D2_HPC at fb64c47, after `make -f public.mk setup` and `make && make gmp`)
#   C7_RUN       a new directory on a shared file system that every compute node sees, e.g. <SCRATCH>/c7-d2/run1
#   C7_SEED      a fresh random seed: python3 -c 'import secrets; print(secrets.randbelow(2**63))'
#                (8885400701634497064 with the identical binary reproduces the 2026 checkpoints)
#   C7_COST      a per-graph cost model for task placement only (the 2026 one: GFF/data/C7_2/run1-20260930-m4096/cost_model.json)
set -eo pipefail
source "$C7_ENV_SETUP"
set -u
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
cd "$C7_PACKAGE"
sha256sum bin/c7d2_gmp
python3 -B tools/production.py plan "$C7_RUN" --seed "$C7_SEED" --backend gmp --replicates 64 --multiplier 4096 \
  --primitive-mode recompute --primitive-points 16384 --shards 64 --threads 64 --checkpoint-tasks 1024 --chunk-points 1048576 \
  --cost-model "$C7_COST"
python3 public/slurm/queue.py "$C7_RUN"      # RUN/lanes/queue.txt: 1,280 work indices, heaviest first
