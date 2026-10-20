#!/bin/bash
# refit72: fetch the cluster analysis outputs (small JSON/TXT; grid.json and npz stay on symmetry) and logs.
set -eo pipefail
HERE=$(cd "$(dirname "$0")" && pwd); O=$HERE/../out; R=<SCRATCH>/dconn_refit72_mi
mkdir -p $O $HERE/../logs
ssh symmetry "cd $R/out && tar czf - --exclude=grid.json --exclude='*.npz' --exclude=members_full.json --exclude=members_prop_index.json --exclude=accel.json ." | tar xzf - -C $O
scp -q "symmetry:$R/logs/*" $HERE/../logs/
du -sh $O
