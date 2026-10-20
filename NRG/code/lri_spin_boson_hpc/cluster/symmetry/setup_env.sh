#!/bin/bash
# Run once on the login node: venv over python/3.13-mamba plus pytest from local wheels.
# Usage: bash setup_env.sh <wheel directory>   (pytest, pluggy, iniconfig wheels; no network needed)
set -euo pipefail
WHEELS="${1:?wheel directory}"
BASE="${LRI_SPIN_BASE:-/mnt/beegfs/zzheng1/lri_spin}"
set +u; source /etc/profile.d/modules.sh; module load python/3.13-mamba; set -u
mkdir -p "$BASE/env"
[ -x "$BASE/venv/bin/python" ] || python -m venv --system-site-packages "$BASE/venv"
"$BASE/venv/bin/python" -m pip install --no-index --find-links "$WHEELS" pytest
"$BASE/venv/bin/python" - "$BASE/env/ENV.json" <<'PY'
import json,platform,subprocess,sys
import numpy,scipy,scipy.linalg,threadpoolctl,pytest,mpmath
info={'python':platform.python_version(),'executable':sys.executable,'numpy':numpy.__version__,
      'scipy':scipy.__version__,'threadpoolctl':threadpoolctl.__version__,'pytest':pytest.__version__,
      'mpmath':mpmath.__version__,'module':'python/3.13-mamba','host':platform.node(),
      'threadpool_info':threadpoolctl.threadpool_info(),
      'pip_freeze':subprocess.run([sys.executable,'-m','pip','freeze','--local'],capture_output=True,text=True).stdout.split()}
open(sys.argv[1],'w').write(json.dumps(info,indent=2)+'\n');print(json.dumps({k:info[k] for k in ('python','numpy','scipy','pytest')}))
PY
echo "Environment record: $BASE/env/ENV.json"
