#!/bin/bash
# refit72 joint lens post-processing on symmetry (sbatch -t 02:00:00 run_py_shared.sbatch bash post_r72.sh [skipchecks])
set -eo pipefail
PY=<HOME>/kgen_vbjet/venv/bin/python
R=../out/r72
$PY tabulate.py $R
for DS in dconn dconn_w dconn_s46 dconn_old; do
  $PY analyze_low.py $R $DS > $R/analyze_low_$DS.txt 2> $R/analyze_low_$DS.err
  $PY analyze_c8.py $R $DS > $R/analyze_c8_$DS.txt 2> $R/analyze_c8_$DS.err
done
JOINT_RMSKEY=rms $PY analyze_low.py $R dconn > $R/analyze_low_dconn_plaincrit.txt 2>/dev/null
$PY analyze_r72.py $R > $R/analyze_r72.txt 2> $R/analyze_r72.err
for P in dconn dconn_w dconn_s46; do
  JOINT_PRIMARY=$P $PY propagate.py $R > $R/propagate_$P.txt
done
[ "$1" = skipchecks ] || $PY checks.py $R > $R/checks.txt
for P in dconn dconn_w dconn_s46; do
  JOINT_PRIMARY=$P $PY summary.py $R > $R/summary_$P.txt 2> $R/summary_$P.err
done
$PY noise.py > $R/noise.txt && cp ../out/noise.json $R/noise.json
ls -la $R
