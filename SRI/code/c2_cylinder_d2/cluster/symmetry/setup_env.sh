#!/bin/bash
# Create the pinned Python environment for this package on symmetry (Perimeter).
# Run on the LOGIN node <NODE> (needs network to PyPI). Idempotent: an existing
# environment with the exact versions is verified and left alone.
#
#   bash cluster/symmetry/setup_env.sh          # default: $HOME/envs/lri_c2/py3.13-mamba
#   LRI_ENV=/path bash cluster/symmetry/setup_env.sh
#
# A venv in $HOME (NFS, code-only, 100 GB quota; the environment is ~0.5 GB) built
# from the cluster's module python/3.13-mamba (CPython 3.13.3; the tested
# packaging environment used 3.13.5) with the exact requirements-tested.txt pins.
# No system-wide pip installs. The jobs load the same module (profile "modules")
# and re-check every pinned version on the compute node (exit 78 on mismatch).
# Existing project venvs in $HOME were checked on 2026-10-12: none has all five
# pinned packages (matplotlib is missing everywhere), so this one is separate.
# If the pinned wheels cannot be installed, the script stops; it never
# substitutes other versions.
set -eo pipefail
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PKG=$(cd "$HERE/../.." && pwd)
REQ="$PKG/requirements-tested.txt"
LRI_PY_MODULE=${LRI_PY_MODULE:-python/3.13-mamba}
LRI_ENV=${LRI_ENV:-$HOME/envs/lri_c2/py3.13-mamba}

[[ -f "$REQ" ]] || { echo "missing $REQ" >&2; exit 66; }
if [[ -n "${SLURM_JOB_ID:-}" ]]; then
    echo "note: running inside job $SLURM_JOB_ID; PyPI downloads need network access from this node" >&2
fi
# shellcheck disable=SC1091
source /etc/profile.d/modules.sh
module load "$LRI_PY_MODULE"
BASE_PY=$(command -v python3)
echo "base interpreter: $BASE_PY ($("$BASE_PY" --version 2>&1))"
unset PYTHONPATH PYTHONHOME VIRTUAL_ENV
export PYTHONNOUSERSITE=1

check() {   # exact versions; writes the receipt; status 0 only if everything matches
    "$LRI_ENV/bin/python" "$PKG/cluster/sitekit/jobtools.py" check-env --requirements "$REQ" \
        --out "$LRI_ENV/lri_env_receipt.json" > /dev/null
}

if [[ -x "$LRI_ENV/bin/python" ]] && check; then
    echo "OK: existing environment $LRI_ENV matches requirements-tested.txt"
    echo "LRI_ENV=$LRI_ENV"
    exit 0
fi
if [[ -e "$LRI_ENV" ]]; then
    echo "$LRI_ENV exists but does not match requirements-tested.txt; inspect or remove it first" >&2
    exit 65
fi
mkdir -p "$(dirname "$LRI_ENV")"
"$BASE_PY" -m venv "$LRI_ENV"
"$LRI_ENV/bin/python" -m pip install --no-cache-dir --disable-pip-version-check --only-binary=:all: -r "$REQ"
if ! check; then
    echo "pinned versions could not be installed exactly; see $LRI_ENV/lri_env_receipt.json (no substitution made)" >&2
    exit 78
fi
"$LRI_ENV/bin/python" -m pip freeze --all > "$LRI_ENV/pip_freeze.txt"
echo "OK: created $LRI_ENV (module $LRI_PY_MODULE)"
echo "LRI_ENV=$LRI_ENV"
