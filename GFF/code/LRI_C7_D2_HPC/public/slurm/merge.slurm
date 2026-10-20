#!/bin/bash
#SBATCH -p <PARTITION>
#SBATCH -A <ACCOUNT>
#SBATCH -N 1
#SBATCH --exclusive
#SBATCH --mem=200G
#SBATCH -t 06:00:00
#SBATCH -J c7d2-merge
# Merge and assembly of the 2026 C7(2) production (Claude Code session C62d; the version after the 2026-10-01 fix of a
# stray grep; paths replaced by variables). Submit after the node workers, e.g. --dependency=afterany:<jobs>.
# It checks that every block is committed, merges the 20 groups in parallel (groups already merged are skipped: the
# merge of fb64c47 is not idempotent, never rerun a merged group), then assembles C7_result.json with 4,096 bootstrap
# resamples. In 2026: 20 merges in one job (566287), assembly 4.8 s (566530). Requires C7_RUN, C7_PACKAGE, C7_ENV_SETUP.
set -eo pipefail
source "$C7_ENV_SETUP"
set -u
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
cd "$C7_PACKAGE"
python3 public/slurm/status.py "$C7_RUN" || { echo "campaign incomplete: not merging"; exit 65; }
W=${TMPDIR:-/tmp}/c7merge_$SLURM_JOB_ID; mkdir -p "$W"
for g in $(python3 -c "import json;print(' '.join(x['name'] for x in json.load(open('$C7_RUN/manifest.json'))['groups']))"); do
  if [[ -f "$C7_RUN/groups/$g/merged.json" ]]; then echo "already merged: $g"; continue; fi
  ( mkdir -p "$W/$g"; python3 -B tools/production.py merge "$C7_RUN" --group "$g" --scratch "$W/$g" > "$C7_RUN/lanes/merge-$g.log" 2>&1 && echo "merged $g" || echo "MERGE FAILED $g" ) &
done
wait
for g in $(python3 -c "import json;print(' '.join(x['name'] for x in json.load(open('$C7_RUN/manifest.json'))['groups']))"); do [[ -f "$C7_RUN/groups/$g/merged.json" ]] || { echo "missing merged.json for $g"; exit 1; }; done
python3 -B tools/assemble.py "$C7_RUN" --bootstrap 4096
rm -rf "$W"
