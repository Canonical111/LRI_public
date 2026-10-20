#!/bin/bash
# Amendment A3 (docs/EXTENSION_A3.md), symmetry: verify imported Expanse batches in the staging directory
# runs/ext1_a3_import before anything is installed: a3_tree.py check-import (file manifest equals Expanse's, planned
# files unchanged, only checkpoints/ and merged/ added, every campaign merged), then production8.py merge on the staged
# copy, which only re-validates every merged campaign (all are audited) and writes nothing. Args: labels.
# Submitted through submit_sym.sh check (sharedq, 8 cores; import.sh calls it). Required: C8X_A3.
set -eo pipefail
source /mnt/beegfs/zzheng1/c8_hpc/code/symmetry/env_symmetry.sh
set -u
W=/mnt/beegfs/zzheng1/c8_hpc;R=$W/runs/ext1;I=$W/runs/ext1_a3_import
[[ "${C8X_A3:?}" == $W/code/*/cluster/a3 && -f $C8X_A3/a3_tree.py ]] || { echo "C8X_A3 not a deployed cluster/a3" >&2; exit 64; }
cmp -s "$0" "$C8X_A3/a3_check.slurm" || { echo "this job script differs from $C8X_A3/a3_check.slurm: submit with submit_sym.sh of that revision" >&2; exit 64; }
[[ "$(env | grep '^C8X_' | sort | tr '\n' '|')" == "C8X_A3=$C8X_A3|" ]] || { echo "unexpected C8X_* variables" >&2; exit 64; }
[[ ! -e $R/A3_CLOSE.lock ]] || { echo "the A3 close has begun: nothing is checked or staged any more" >&2; exit 64; }
for b in "$@"; do
  "$C8_PYTHON" $C8X_A3/a3_tree.py check-import $R/$b $I/$b $I/$b.expanse_manifest.txt
  "$C8_PYTHON" $C8_ROOT/tools/production8.py merge $I/$b
  echo "$b: staged copy verified"
done
