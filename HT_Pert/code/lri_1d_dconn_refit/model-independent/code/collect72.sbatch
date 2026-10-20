#!/bin/bash
#SBATCH -N 1 --exclusive
#SBATCH --mem=180G
#SBATCH -J mi72-collect
# refit72: post-processing on the cluster (float64, seconds per step): full analysis of the primary and comparison runs,
# light analysis of every run (incl. quantile reruns), members_analyze, summarize, headline, selection sensitivity.
# Every analysis uses the same data file and smooth central as its grid run (analyze_core asserts it).
source /etc/profile.d/modules.sh
module load anaconda3/2023.07-2
set -eo pipefail
W=${W:-<SCRATCH>/dconn_refit72_mi}; O=$W/out; C=$W/code
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
CORR0=$W/data/corrected.json; VARS0=$W/data/variants.json
FULL=" run2_fmedoid run1 run_mimedoid run_fmean run_s46 run0_repro "
echo "host $(hostname)"; date
while read -r TAG CEN CORR VARS RAWC; do      # no pipe: the loop must run in this shell so that wait sees the jobs
  [ -z "$TAG" ] && continue
  CC=$CORR0; VV=$VARS0; [ -n "$CORR" ] && [ "$CORR" != - ] && CC=$CORR; [ -n "$VARS" ] && [ "$VARS" != - ] && VV=$VARS
  [ -f $O/$TAG/grid.json ] || { echo "MISSING $TAG"; continue; }
  env DCONN_CENTRAL=$CEN DCONN_CORRECTED=$CC DCONN_VARIANTS=$VV MI_LIGHT=1 MI_OUT=analysis_light python3 $C/analyze.py $O/$TAG > $O/$TAG/analysis_light.txt 2>&1 &
  if [[ "$FULL" == *" $TAG "* ]]; then
    env DCONN_CENTRAL=$CEN DCONN_CORRECTED=$CC DCONN_VARIANTS=$VV python3 $C/analyze.py $O/$TAG > $O/$TAG/analysis.txt 2>&1 &
  fi
done < <(cat $C/runlist72_main.txt $C/runlist72_q.txt)
wait
echo "analyses done $(date +%T)"
export DCONN_CORRECTED=$CORR0 DCONN_VARIANTS=$VARS0 DCONN_CENTRAL=k6:53,k7:74,k8:79 MI_PRIMARY=run2_fmedoid
for s in "10 1e-3 1e-3" "10 1e-4 0.7e-3" "10 1e-4 2e-3" "10 3e-5 1e-3" "20 1e-4 1e-3" "3 3e-5 1e-3" "5 1e-4 1e-3" "10 3e-4 1e-3" "10 1e-4 1e-3"; do
  set -- $s
  MI_FAC=$1 MI_NOISE=$2 MI_BMAX=$3 MI_LIGHT=1 MI_OUT=sel_$1_$2_$3 python3 $C/analyze.py $O/run2_fmedoid > /dev/null 2>&1 &
  env DCONN_CENTRAL=median DCONN_CORRECTED=$W/data/floormean_s46.json MI_FAC=$1 MI_NOISE=$2 MI_BMAX=$3 MI_LIGHT=1 MI_OUT=sel_$1_$2_$3 python3 $C/analyze.py $O/run_s46 > /dev/null 2>&1 &
done
wait
python3 $C/members_analyze.py $O/run2_fmedoid $O/mem1 > $O/mem1/members_analysis.txt 2>&1
python3 $C/summarize.py $O > $O/final_summary.txt 2>&1
python3 $C/headline.py $O > $O/headline.txt 2>&1
ls -la $O/*/analysis*.json | wc -l
date; echo DONE
