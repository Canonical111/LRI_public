#!/bin/bash
#SBATCH -p amdq
#SBATCH -N 1 --exclusive
#SBATCH -t 08:00:00
#SBATCH --mem=240G
#SBATCH -J sri_eng_regress_v2
#SBATCH -o <SCRATCH>/sri_c6c7/engine/logs/%x_%j.out
# v2 regression on ONE amdq node (prepared locally by tests/regress_prepare.py; see README section 9).
# Builds the v2 and the phase-1 engine from source with the same compiler, then runs (in this order)
#   direct_v1 / direct_v2 (bitwise identity), replay5 (vs stored pilot5), strict (floor calibration),
#   new (complete campaign, hashed seeds, end-to-end), replay4 (planner reference, vs stored pilot4).
# Each list is restartable (run_list.sh skips completed outputs).
set -uo pipefail
ROOT=<SCRATCH>/sri_c6c7/engine
R=$ROOT/runs/regress_v2
cd $ROOT
bash slurm/build.sh || exit 1
SRC=legacy/lri_engine_phase1.cpp OUT=bin/lri_engine_phase1 bash slurm/build.sh || exit 1
md5sum bin/lri_engine bin/lri_engine_phase1 bin/lri_engine_phase1_orig 2>/dev/null
rc=0
LRI_ENGINE=$ROOT/bin/lri_engine_phase1 bash slurm/run_list.sh $R/direct_v1 $R/direct_v1/cfglist.txt || rc=1
for d in direct_v2 replay5 strict new replay4; do
  echo "##### $d $(date -Is)"
  bash slurm/run_list.sh $R/$d $R/$d/cfglist.txt || rc=1
done
echo "##### all done $(date -Is) rc=$rc"
exit $rc
