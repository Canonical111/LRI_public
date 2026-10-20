#!/bin/bash
# Amendment A2 (docs/EXTENSION_A2.md): the A1-close job body, shared by 'submit_a2.sh arm' and any manual rerun
# (sbatch -p debugq -N 1 --exclusive --mem=180G -t 01:00:00 --job-name=c8x-a1close -o .../logs/%x_%j.out
#  --wrap "bash .../cluster/symmetry/a1_close_job.sh"). Runs 'submit_a2.sh close' and then, whatever close returned,
# a1_close_combine.sh (which validates the snapshot itself); exits nonzero if either failed.
H=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
bash "$H/submit_a2.sh" close;c=$?
bash "$H/a1_close_combine.sh";d=$?
echo "A1-close job: close status $c, combination status $d"
exit $((c|d))
