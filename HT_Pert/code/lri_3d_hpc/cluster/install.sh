#!/bin/bash
# Build or check the pinned Python environment of this site (login node; light work).
#     bash cluster/install.sh [--check]
# Creates, once, under $HT3D_DATA (see sites/<site>.sh):
#   tools/uv      uv 0.12.23 (official installer, pinned version)
#   python/       CPython 3.12.9, the generic x86_64-gnu build (runs on Intel and AMD nodes)
#   <venv>        numpy 2.5.3, scipy 1.17.0, numba 0.68.0, llvmlite 0.50.0, threadpoolctl 3.6.0
#                 from cluster/requirements.lock (hash-pinned wheels), plus mpi4py 4.1.2 built
#                 from source against the site MPI (Expanse openmpi/4.1.8 module, symmetry
#                 /usr/bin/mpicc = Debian OpenMPI 4.1.2)
# and writes <venv>/ht3d-env.json. With --check nothing is installed; the pins are verified.
# No `set -u` before the site init (module scripts are not nounset-safe).
set -eo pipefail
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
check=0; [ "${1:-}" = --check ] && check=1
if [ -d /expanse/lustre ]; then site=expanse
elif [ -d /mnt/beegfs ] && [ -d /cm/shared/apps/slurm ]; then site=symmetry
else echo "install: unsupported site" >&2; exit 2; fi
[ -z "${HT3D_SITE:-}" ] || [ "$HT3D_SITE" = "$site" ] || { echo "install: HT3D_SITE=$HT3D_SITE on $site" >&2; exit 2; }
source "$here/sites/$site.sh"
ht3d_site_init
D=$HT3D_DATA; V=$HT3D_VENV
export UV_PYTHON_INSTALL_DIR=$D/python UV_CACHE_DIR=$D/uvcache PYTHONNOUSERSITE=1
if [ "$check" = 0 ]; then
  mkdir -p "$D/tools" "$D/python"
  if [ ! -x "$D/tools/uv" ]; then
    curl -LsSf https://astral.sh/uv/0.12.23/install.sh | env UV_INSTALL_DIR="$D/tools" INSTALLER_NO_MODIFY_PATH=1 sh
  fi
  "$D/tools/uv" python install cpython-3.12.9-linux-x86_64-gnu
  [ -d "$V" ] || "$D/tools/uv" venv --python cpython-3.12.9-linux-x86_64-gnu "$V"
  "$D/tools/uv" pip sync --python "$V/bin/python" --require-hashes "$here/requirements.lock"
  MPICC=$(command -v mpicc) "$D/tools/uv" pip install --python "$V/bin/python" --no-binary mpi4py --no-cache mpi4py==4.1.2
fi
"$V/bin/python" -I - "$here/requirements.lock" "$V/ht3d-env.json" "$check" <<'PY'
import json, re, sys, sysconfig, platform
from importlib import metadata
lock, out, check = sys.argv[1], sys.argv[2], sys.argv[3] == '1'
pins = dict(re.findall(r'^([A-Za-z0-9_.-]+)==([^\s\\]+)', open(lock).read(), re.M))
pins['mpi4py'] = '4.1.2'
have = {name: metadata.version(name) for name in pins}
bad = {n: (pins[n], have[n]) for n in pins if have[n] != pins[n]}
import numpy, mpi4py
from mpi4py import MPI
record = dict(python=sys.version, executable=sys.executable, platform=platform.platform(),
              cflags=sysconfig.get_config_var('CFLAGS'), packages=have,
              longdouble_nmant=int(numpy.finfo(numpy.longdouble).nmant),
              mpi_library=MPI.Get_library_version().strip(), mpi4py_config=mpi4py.get_config())
if bad or record['longdouble_nmant'] != 63 or not sys.version.startswith('3.12.9'):
    sys.exit(f'install: environment does not match the pins: {bad}, nmant {record["longdouble_nmant"]}, {sys.version}')
if not check:
    open(out, 'w').write(json.dumps(record, indent=1, default=str) + '\n')
print(json.dumps(dict(ok=True, packages=have, mpi=record['mpi_library'].splitlines()[0])))
PY
