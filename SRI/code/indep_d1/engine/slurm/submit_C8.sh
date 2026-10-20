#!/bin/bash
# C8 production submission recipe (phase 3).  NOT run by the engine agent: production needs the user's go-ahead.
#   bash slurm/submit_C8.sh A|B|C [MAXRUN] [SPECFILE]
# SPECFILE defaults to specs/production_C8_tier<X>.json; an alternative (e.g. specs/production_C8_tierC_sigma0.3.json,
# tier name c8tierC_s0.3, own seeds) runs in runs/<its tier name>.
# Run on the symmetry login node from <SCRATCH>/sri_c6c7/engine after `bash slurm/build.sh` (built in a
# job or on a compute node; x86-64-v3) and after copying specs/production_C8_tier<X>.json there.
# amdq first; defq only if amdq is down or full (then add -p defq --mem=180G; Intel nodes have 40 cores);
# never longq.  Keep at most MAXRUN (default 8) of our nodes busy: the user runs other jobs on symmetry too.
set -euo pipefail
T=${1:?tier A, B or C}; MAXRUN=${2:-8}; SPEC=${3:-specs/production_C8_tier$T.json}
ROOT=<SCRATCH>/sri_c6c7/engine
cd $ROOT
[ -f $SPEC ] || { echo "missing $SPEC"; exit 2; }
TNAME=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['tier'])" $SPEC)   # c8tierA, c8tierC_s0.3, ...
RUN=runs/$TNAME
export PATH=/cm/shared/apps/slurm/current/bin:$PATH
# 1. plan on a compute node (new Korobov lattices for N >= ~5e5 take minutes each in 7D): seeds = hash of
#    (tier name c8tier<X>, group, k, chunk); seedcheck against every earlier campaign of this engine.
if [ ! -f $RUN/cfglist.txt ]; then
  OTHERS=$(ls -d runs/prod_* runs/poles1 runs/kplus1 runs/conv1 runs/c8val runs/c8conv runs/c8kplus1 runs/c8tier* 2>/dev/null \
           | grep -v "^$RUN\$" | tr '\n' ' ' || true)
  jid=$(sbatch --parsable -p amdq -N 1 --exclusive -t 04:00:00 --mem=64G -J sri_eng_plan_c8$T \
        -o $ROOT/logs/%x_%j.out --wrap "source /etc/profile.d/modules.sh; module load anaconda3/2023.07-2; cd $ROOT; \
          python py/campaign.py plan $SPEC $RUN && python py/campaign.py seedcheck $RUN $OTHERS")
  echo "planning job $jid (log $ROOT/logs/sri_eng_plan_c8${T}_$jid.out); rerun this script after it finishes"; exit 0
fi
# 2. one array task per cfg line (cfglist.txt is sorted by estimated cost: longest first)
NT=$(wc -l < $RUN/cfglist.txt)
sinfo -h -p amdq -o '%t %D'
squeue -u $USER -h -o '%T' | sort | uniq -c
sbatch --array=1-${NT}%${MAXRUN} -J sri_eng_c8$T $ROOT/slurm/production_symmetry.sbatch $RUN 1
echo "logs: $ROOT/logs/sri_eng_c8${T}_<jobid>_<task>.out ; per-cfg logs: $ROOT/$RUN/<cfg>.log"
cat <<EOT
after completion (sacct shows every task COMPLETED; never resubmit PENDING tasks):
  python py/campaign.py collect $RUN --need specs/production_C8_need.json    # beyond-D4 scalars only
  python py/outliers.py $RUN --grad specs/gradients_C8.json --T 1e-3 --json $RUN/flags.json   # tier A: --T 1e-5
  python py/campaign.py refine $RUN $RUN/flags.json   # if flagged; then run cfglist_refine.txt and collect again
  # on the Mac (../framework is not on symmetry), after copying results.json + framework_input.json back:
  python3 tests/validate_C8.py --run runs/c8val --run $RUN                  # poles, higher logs, RG logs
  python3 ../framework/run_framework.py --order C8 --independent-files \\
      --raw runs/prod_6digit/framework_input_final.json --raw runs/c8tierA/framework_input.json [--raw ...B, C]
EOT
