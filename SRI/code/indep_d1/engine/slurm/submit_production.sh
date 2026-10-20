#!/bin/bash
# Production submission recipe (v2).  NOT run by the engine agent: production needs the user's go-ahead.
#   bash slurm/submit_production.sh 6digit|8digit [MAXRUN]
# Run on the symmetry login node from <SCRATCH>/sri_c6c7/engine after `bash slurm/build.sh`
# (built in a job or on a compute node; x86-64-v3).  amdq first; defq only if amdq is full; never longq.
set -euo pipefail
TIER=${1:-6digit}; MAXRUN=${2:-8}
ROOT=<SCRATCH>/sri_c6c7/engine
RUN=runs/prod_$TIER
export PATH=/cm/shared/apps/slurm/current/bin:$PATH
cd $ROOT
# 1. plan on a compute node (lattice searches for N ~ 1e6-4e6 take ~1-2 min each); seeds = hash(tier, group, k,
#    chunk); seedcheck against every earlier production tier so that no two tiers share a random shift.
if [ ! -f $RUN/cfglist.txt ]; then
  OTHERS=$(ls -d runs/prod_* 2>/dev/null | grep -v "^$RUN\$" | tr '\n' ' ' || true)
  jid=$(sbatch --parsable -p amdq -N 1 --exclusive -t 02:00:00 --mem=64G -J sri_eng_plan_$TIER \
        -o $ROOT/logs/%x_%j.out --wrap "source /etc/profile.d/modules.sh; module load anaconda3/2023.07-2; cd $ROOT; \
          python py/campaign.py plan specs/production_$TIER.json $RUN && python py/campaign.py seedcheck $RUN $OTHERS")
  echo "planning job $jid (log $ROOT/logs/sri_eng_plan_${TIER}_$jid.out); rerun this script after it finishes"; exit 0
fi
# 2. one array task per cfg line; cfglist.txt is sorted by estimated cost, so the longest cfgs start first
NT=$(wc -l < $RUN/cfglist.txt)
sinfo -h -p amdq -o '%t %D'
sbatch --array=1-${NT}%${MAXRUN} $ROOT/slurm/production_symmetry.sbatch $RUN 1
echo "logs: $ROOT/logs/sri_eng_prod_<jobid>_<task>.out ; per-cfg logs: $ROOT/$RUN/<cfg>.log"
cat <<EOT
after completion (sacct shows every task COMPLETED; never resubmit PENDING tasks):
  python py/campaign.py collect $RUN                       # per-replicate assembly, floor, explicit zeros
  python py/outliers.py $RUN --T 5e-5 --json $RUN/flags.json   # exit 1 = relevant flagged sectors
  python py/campaign.py refine $RUN $RUN/flags.json        # if flagged: more points (srun on a compute node if
                                                           # the refined N needs a new Korobov lattice search)
  sbatch --array=1-\$(wc -l < $RUN/cfglist_refine.txt)%${MAXRUN} slurm/production_symmetry.sbatch $RUN 1 cfglist_refine.txt
  python py/campaign.py collect $RUN && python py/outliers.py $RUN --T 5e-5    # repeat until exit 0
  # on the Mac (../framework is not on symmetry), after copying results.json + framework_input.json back:
  python3 tests/e2e_framework.py $RUN/results.json --out results/e2e_$TIER.json   # C6, C7 with replicate errors
EOT
