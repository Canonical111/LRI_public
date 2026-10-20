#!/usr/bin/env bash
# The original array mode (one `campaign.py run --job` per element) is disabled on symmetry and Expanse:
# tools/submit.py admits no array (its elements would bypass the caps, the ledger and the lock owners), and
# symmetry's partitions are exclusive whole nodes. Use packed lanes (tools/submit.py lanes, slurm/run_hpc.sh).
# Locally, `python3 -B tools/campaign.py run RUN --workers W --threads T` remains the package's own workflow.
#SBATCH --job-name=c8opt-array
#SBATCH --output=c8opt-array-%A_%a.out
echo "c8opt: array mode is not supported on the clusters; use tools/submit.py lanes (docs/CLUSTERS.md)" >&2
exit 64
