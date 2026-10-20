#!/bin/bash
# Build the hosted C7(1) record archive from the production tree, then run the Tier 2 replay on the unpacked
# archive in node-local scratch, exactly as a reader would after `make -f public.mk fetch-data`.
# Placeholders: <ACCOUNT>, <PARTITION>, <SCRATCH> (durable shared filesystem holding the production tree c7_hpc/),
# <ENV_SETUP> (a script that loads Python >= 3.8 with numpy, e.g. modules plus a venv), <GFF> (the public GFF/ checkout).
# Size: 1 node, 4 CPUs, 16 GB; about 1-2 h in total (archive 30-60 min on Lustre, replay 20-40 min; estimates).
#SBATCH --job-name=c7-1-archive-replay
#SBATCH --account=<ACCOUNT>
#SBATCH --partition=<PARTITION>
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=04:00:00
#SBATCH --output=c7-1-archive-replay-%j.log
set -eo pipefail
source <ENV_SETUP>
set -u
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
TREE=<SCRATCH>/c7_hpc                  # production tree: batches/b001..b400, primitive/P1
OUT=<SCRATCH>/c7_1_public_archive      # archive output (kept; this is what gets hosted)
PKG=<GFF>/code/LRI_C7_HPC
LOCAL=${SLURM_TMPDIR:-${TMPDIR:-/tmp}}/c7_1_replay_$SLURM_JOB_ID
mkdir -p "$OUT" "$LOCAL/data/C7_1"
python3 "$PKG/public/make_data_archive.py" --tree "$TREE" --results "<GFF>/results/C7_1" --out "$OUT"
tar -xzf "$OUT/C7_1_merged_records.tar.gz" -C "$LOCAL/data/C7_1"
cd "$PKG"
python3 public/replay7.py --results ../../results/C7_1 --work "$LOCAL/work"
python3 public/replay7_full.py --data "$LOCAL/data/C7_1" --results ../../results/C7_1 --work "$LOCAL/work" --jobs 4
cp "$LOCAL/work/replay7_tier1.txt" "$LOCAL/work/replay7_full.json" "$OUT/"
echo "archive and replay reports in $OUT"
