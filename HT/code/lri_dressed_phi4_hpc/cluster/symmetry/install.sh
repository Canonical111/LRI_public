#!/bin/bash
# Freeze a git revision of this repository on symmetry. Code lands read-only in $HOME/lri_dressed/code/<sha>.
#   From the Mac (two steps):
#     git archive --prefix=<sha>/ <sha> | ssh symmetry 'mkdir -p ~/lri_dressed/incoming && tar -x -C ~/lri_dressed/incoming'
#     ssh symmetry 'bash ~/lri_dressed/incoming/<sha>/cluster/symmetry/install.sh --from-dir ~/lri_dressed/incoming/<sha> <sha>'
#   Inside a git clone on symmetry:  cluster/symmetry/install.sh REV [GIT_DIR]
set -euo pipefail
if [ "${1:-}" = "--from-dir" ]; then
  src="${2:?--from-dir DIR SHA}"; sha="${3:?--from-dir DIR SHA}"; dest="$HOME/lri_dressed/code/$sha"
  [ -e "$dest" ] && { echo "exists: $dest"; exit 0; }
  mkdir -p "$(dirname "$dest")"; cp -a "$src" "$dest.tmp"; echo "$sha" > "$dest.tmp/GIT_SHA"
else
  rev="${1:?usage: install.sh REV [GIT_DIR] | --from-dir DIR SHA}"; gitdir="${2:-.}"
  sha=$(git -C "$gitdir" rev-parse "$rev"); dest="$HOME/lri_dressed/code/$sha"
  [ -e "$dest" ] && { echo "exists: $dest"; exit 0; }
  mkdir -p "$dest.tmp"; git -C "$gitdir" archive "$sha" | tar -x -C "$dest.tmp"; echo "$sha" > "$dest.tmp/GIT_SHA"
fi
chmod -R a-w "$dest.tmp"; mv "$dest.tmp" "$dest"
source "$dest/cluster/symmetry/env.sh"
python - <<'PY'
import importlib.metadata as m,pathlib,os
want={l.split('==')[0]:l.split('==')[1].strip() for l in pathlib.Path(os.environ['LRI_CODE'],'requirements-tested.txt').read_text().splitlines() if '==' in l}
for k,v in want.items():
    have=m.version(k);print(f'{k:14s} tested {v:10s} venv {have}'+('' if have==v else '   <-- differs'))
from lri_dressed.io import release_fingerprint,source_fingerprint,runtime
print('runtime',runtime());print('release',release_fingerprint());print('source ',source_fingerprint())
PY
echo "installed $dest"
