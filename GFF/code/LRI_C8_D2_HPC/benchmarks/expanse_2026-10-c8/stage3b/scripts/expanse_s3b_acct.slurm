#!/bin/bash
#SBATCH -A <ACCOUNT> -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=2 --mem=4G -t 00:30:00 --no-requeue
#SBATCH -J c8d2-s3b-acct
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# After J-SWEEP-1 has ended: tools/accounting.py on the sweep campaign (every sacct -X --duplicates record of every
# ledger job, physical cores, eta_node; R10) and tools/ledger.py list; the record goes to the sweep's evidence directory.
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> SWEEP_EVIDENCE=<sweep evidence dir> sbatch --export=ALL --dependency=afterany:<sweep job> ...
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}" "${SWEEP_EVIDENCE:?}"
TAG=$(basename "$C8_PACKAGE"); W=$C8_DATA/sweep1-$TAG
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); campaign $W"
cd "$C8_PACKAGE"
python3 -B tools/ledger.py list "$W" | tee "$SWEEP_EVIDENCE/ledger_list.txt"
python3 -B tools/accounting.py "$W" --output "$SWEEP_EVIDENCE/accounting.json"; s=$?
python3 -B tools/seeds.py list | tee "$SWEEP_EVIDENCE/seeds_after.txt"
echo "finished $(date -Is), status $s"
exit $s
