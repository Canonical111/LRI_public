#!/bin/bash
# Submitted by scripts/symmetry_submit.py validate (partition, node, time and output on the command line).
set -euo pipefail
: "${LRI_SPIN_CODE:?}"
source "$LRI_SPIN_CODE/cluster/symmetry/env.sh"
out="$LRI_SPIN_BASE/validation/$SLURM_JOB_ID"; mkdir -p "$out"
cp "$LRI_SPIN_CODE/GIT_SHA" "$out/GIT_SHA"
hostname > "$out/host.txt"; lscpu > "$out/lscpu.txt"
python -c 'import json,lri_spin,threadpoolctl;print(json.dumps(threadpoolctl.threadpool_info(),indent=1))' > "$out/threadpool_info.json"
cd "$LRI_SPIN_CODE"
python tests/verify_manifest.py
python scripts/validate_release.py --output "$out/receipt.json"
echo "Receipt: $out/receipt.json"
