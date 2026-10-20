#!/bin/bash
#SBATCH -p sharedq -N 1 -n 1 -c 2 --mem=3G -t 00:30:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# After a sweep job has ended: tools/accounting.py on the sweep campaign (every sacct -X --duplicates record of every
# ledger job, physical cores, eta_node; R10, A-ORC-9 on real data) and tools/ledger.py list, into the sweep's evidence.
# Usage: C8_PACKAGE=... C8_RUN=<campaign> ACCT_OUT=<evidence dir> sbatch --export=ALL --dependency=afterany:<sweep> -J c8d2-s5acct s5acct.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}" "${C8_RUN:?}" "${ACCT_OUT:?}"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); campaign $C8_RUN; output $ACCT_OUT"
cd "$C8_PACKAGE" || exit 64
python3 -B tools/ledger.py list "$C8_RUN" | tee "$ACCT_OUT/ledger_list.txt"
python3 -B tools/accounting.py "$C8_RUN" --output "$ACCT_OUT/accounting.json"; s=$?
python3 -B tools/seeds.py list > "$ACCT_OUT/seeds_after.txt" 2>&1
echo "finished $(date -Is), status $s"
exit $s
