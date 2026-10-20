#!/bin/bash
# Export gated campaign results on Expanse (export_results.py applies check_result) and copy them here, plus a
# local copy of the raw per-cutoff outputs under ../../results/expanse/ (git-ignored).
# Usage: bash analysis/extended/fetch_results.sh [code revision on Expanse, default f0a7084]
set -eo pipefail
REV=${1:-f0a7084}
H=<SCRATCH>/temp_project/lri_ht
HERE=$(cd "$(dirname "$0")" && pwd)
# Every exported row must carry the campaign's source fingerprint (campaign/plan.json), review IR-003.
ssh expanse "source $H/code/$REV/cluster/expanse/env.sh >/dev/null 2>&1; cd $H/code/$REV && mkdir -p $H/exported &&
  SRC=\$(python -c 'import json;print(json.load(open(\"$H/campaign/plan.json\"))[\"source\"])') &&
  python export_results.py $H/results/thermal_d7 --task thermal --degree 7 --source \$SRC --prefix $H/exported/thermal_new &&
  python export_results.py $H/results/phi6_d5 --task phi6 --degree 5 --source \$SRC --prefix $H/exported/phi6_d5_new &&
  python export_results.py $H/results/phi6_d3 --task phi6 --degree 3 --source \$SRC --prefix $H/exported/phi6_d3_new" 2>&1 | grep -v Pseudo
for f in thermal_new phi6_d5_new phi6_d3_new; do scp -q expanse:$H/exported/$f.json expanse:$H/exported/$f.csv "$HERE/"; done
mkdir -p "$HERE/../../results/expanse"
rsync -a --exclude checkpoints expanse:$H/results/ "$HERE/../../results/expanse/"
rsync -a expanse:$H/campaign/ "$HERE/../../results/expanse/campaign/"
ls -la "$HERE"/*_new.json
