#!/bin/bash
# Rerun the model-independent lens on a (re)built delta model, e.g. after the S10 cluster points L = 46..72 arrive:
#   0) delta stage:  python3 ../../delta/code/build_delta.py --extra-dconn NEW.csv --tag delta_v2
#   1) bash rerun.sh submit  CORR_JSON VARS_JSON RUNTAG     (stages code+data on symmetry, submits 3 amddebugq jobs)
#   2) bash rerun.sh collect RUNTAG LOCAL_OUTDIR            (after the jobs finish: fetch, analyze, summarize locally)
# Everything is read-only on the repositories; cluster workspace <SCRATCH>/dconn_fit_mi/<RUNTAG>.
set -eo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
W=<SCRATCH>/dconn_fit_mi
SL='export PATH=/cm/shared/apps/slurm/current/bin:$PATH'
if [ "$1" = submit ]; then
  CORR=$2; VARS=$3; TAG=$4; R=$W/$TAG
  DCONN_CORRECTED=$CORR DCONN_VARIANTS=$VARS python3 $HERE/make_runlist.py $HERE/runlist_$TAG.txt
  ssh symmetry "mkdir -p $R/{code,data,out,logs,delta_code}"
  scp -q $HERE/{common.py,grid.py,accel.py,members_full.py,members_prop.py,run_list.sbatch,run_members.sbatch} symmetry:$R/code/
  scp -q $HERE/runlist_$TAG.txt symmetry:$R/code/runlist.txt
  scp -q $HERE/../../delta/code/{ensemble.py,fitlib.py} symmetry:$R/delta_code/
  scp -q "$CORR" symmetry:$R/data/corrected.json; scp -q "$VARS" symmetry:$R/data/variants.json
  scp -q <PROJECT>/lri_ht_c8_symmetry/results/2026-10_symmetry/extrapolation/data.json symmetry:$R/data/ht_data.json
  printf 'run1 median\n' > /tmp/rl_med_$TAG.txt; printf 'run3_rawc8 medoid\n' > /tmp/rl_raw_$TAG.txt
  scp -q /tmp/rl_med_$TAG.txt symmetry:$R/code/runlist_median.txt; scp -q /tmp/rl_raw_$TAG.txt symmetry:$R/code/runlist_rawc8.txt
  # the sbatch scripts use W=<SCRATCH>/dconn_fit_mi; point them at the tagged workspace
  ssh symmetry "cd $R/code && sed -i 's#^W=.*#W=$R#' run_list.sbatch run_members.sbatch && $SL && \
    export DCONN_CORRECTED=$R/data/corrected.json DCONN_VARIANTS=$R/data/variants.json && \
    sbatch -p amddebugq -t 00:55:00 -o $R/logs/%x_%j.out run_list.sbatch $R/code/runlist.txt && \
    sbatch -p amddebugq -t 00:20:00 -o $R/logs/%x_%j.out run_list.sbatch $R/code/runlist_median.txt && \
    RAW_C07=lri_c8 HT_DATA_JSON=$R/data/ht_data.json sbatch -p amddebugq -t 00:20:00 -o $R/logs/%x_%j.out run_list.sbatch $R/code/runlist_rawc8.txt && \
    sbatch -p amddebugq -t 00:30:00 -o $R/logs/%x_%j.out run_members.sbatch mem1"
elif [ "$1" = collect ]; then
  TAG=$2; O=$3; R=$W/$TAG; mkdir -p $O
  for d in $(ssh symmetry "ls $R/out"); do mkdir -p $O/$d; scp -q "symmetry:$R/out/$d/*.json" $O/$d/ || true; scp -q "symmetry:$R/out/$d/*.npz" $O/$d/ 2>/dev/null || true; done
  export DCONN_CORRECTED=${DCONN_CORRECTED:?set to the local corrected json} DCONN_VARIANTS=${DCONN_VARIANTS:?set to the local variants json}
  python3 $HERE/analyze.py $O/run2_medoid > $O/run2_medoid/analysis.txt
  for d in $O/run2_k*_q* $O/run1 $O/run3_rawc8; do MI_LIGHT=1 MI_OUT=analysis_light python3 $HERE/analyze.py $d > $d/analysis_light.txt; done
  python3 $HERE/members_analyze.py $O/run2_medoid $O/mem1 > $O/mem1/members_analysis.txt
  python3 $HERE/summarize.py $O > $O/final_summary.txt
  echo "summary: $O/final_summary.json"
else
  echo "usage: rerun.sh submit CORR VARS TAG | collect TAG OUTDIR"; exit 2
fi
