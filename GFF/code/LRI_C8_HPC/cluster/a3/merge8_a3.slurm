#!/bin/bash
#SBATCH --account=yun124
#SBATCH --partition=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=04:00:00
# Amendment A3 (docs/EXTENSION_A3.md), Expanse: check that every planned checkpoint of the batch is present (else exit
# without writing), merge and verify every campaign of one A3 batch (production8.py merge, as cluster/merge8.slurm),
# then write the batch's file manifest runs/ext1/<label>.expanse_manifest.txt (no-clobber;
# an existing one must match), which the copy back to symmetry is checked against.
# Required: C8_ENV_SETUP, C8_ROOT, C8_PRODUCTION, C8_A3 (cluster/a3 of the A3 commit).
set -eo pipefail
source "${C8_ENV_SETUP:?}"
set -u
scratch_args=()
if [[ -n "${SLURM_TMPDIR:-}" ]]; then scratch_args=(--scratch "$SLURM_TMPDIR"); fi
# completeness of the whole batch first (lane8.checkpoints_complete of the A3 commit: manifests and hash-checked task
# plans), so an incomplete batch is refused before the frozen merger creates any output
"${C8_PYTHON:-python3}" - "${C8_A3:?}/../../tools" "${C8_PRODUCTION:?}" <<'PY'
import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);import lane8
ok,have,need=lane8.checkpoints_complete(Path(sys.argv[2]))
if not ok:sys.exit(f'C8: {have}/{need} checkpoints present: batch incomplete, nothing merged')
print(f'C8: all {need} planned checkpoints present')
PY
"${C8_PYTHON:-python3}" "${C8_ROOT:?}/tools/production8.py" merge "${C8_PRODUCTION:?}" ${scratch_args[@]+"${scratch_args[@]}"}
B=$(cd "$C8_PRODUCTION" && pwd)
"${C8_PYTHON:-python3}" "${C8_A3:?}/a3_tree.py" manifest "$B" --out "$(dirname "$B")/$(basename "$B").expanse_manifest.txt"
