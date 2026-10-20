#!/bin/bash
# Amendment A2 (docs/EXTENSION_A2.md): the A1 result at its deadline. Interim-mode combination (no --closed: A2 lanes run)
# of b1-b4 and exactly the A1 inclusion set recorded in the A1-close snapshot (runs/ext1/extension_A1close.json), into
# results/C8_A1_close/combination. Reproducible at any later time (combine8 rejects any batch outside that set). Run on a
# compute node (the A1-close job, or a debugq job); it fails, changing nothing, if the snapshot or the derived file
# does not verify or an included batch is not merged.
set -eo pipefail
W=/mnt/beegfs/zzheng1/c8_hpc;D=$W/runs/ext1/extension_A1close.json
source $W/code/symmetry/env_symmetry.sh >/dev/null 2>&1
cd $W
[[ -f $D && -f results/C8_A1_close/a1_close_snapshot.json ]] || { echo "A1-close snapshot not published" >&2; exit 64; }
# Verify the saved snapshot and the exact derived-file contents (restart mode of the snapshot script: schema,
# extension.json digest, derived file equal to the one rebuilt from the snapshot; writes nothing, rescans nothing).
"$C8_PYTHON" "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/a1_close_snapshot.py" > /dev/null || { echo "A1-close snapshot or derived file does not verify" >&2; exit 64; }
inc=$("$C8_PYTHON" -c "import json;print(' '.join('runs/ext1/'+x['path'] for x in json.load(open('$D'))['extension']))")
"$C8_PYTHON" code/15a110e/tools/combine8.py runs/prod4/b1 runs/prod4/b2 runs/prod4/b3 runs/prod4/b4 $inc --extension $D \
  --output results/C8_A1_close/combination --affine analysis/v1/full_affine8.json \
  --exact5 runs/exact8_L5/exact_L5/merged/N14.json runs/exact8_L5/exact_L5/merged/N12.json \
  --design-meta designs_frozen/prod4_34000/design_meta.json --jobs 32
