#!/bin/bash
# One-time creation of the dedicated venv on a login node (light work: pip downloads wheels).
#   LRI_COEFF_SITE=expanse bash cluster/setup_venv.sh      # or symmetry; venv at $LRI_COEFF_VENV
# Base Python: Expanse module python/3.11.9 (with gcc/13.3.0); symmetry anaconda3/2023.07-2 Python 3.11.4.
# The venv lives in home (thousands of small files do not belong on Lustre/BeeGFS). Refuses to touch an
# existing venv. Versions are the tested pins (cluster/requirements-cluster.txt); afterwards
# scripts/stack.py --pins must pass (the 80-bit long double check needs an x86-64 node).
set -o pipefail
set -e
here=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
export LRI_COEFF_NO_VENV=1
source "$here/cluster/site.sh"
[[ $- == *e* ]] || { echo "setup_venv: errexit lost" >&2; exit 2; }
venv=$LRI_COEFF_VENV
[[ ! -e $venv ]] || { echo "setup_venv: $venv exists; remove it yourself or set LRI_COEFF_VENV" >&2; exit 2; }
[[ -x $LRI_COEFF_BASE_PYTHON ]] || { echo "setup_venv: no base Python $LRI_COEFF_BASE_PYTHON" >&2; exit 2; }
echo "setup_venv: $LRI_COEFF_BASE_PYTHON ($("$LRI_COEFF_BASE_PYTHON" --version 2>&1)) -> $venv"
mkdir -p "$(dirname "$venv")"
"$LRI_COEFF_BASE_PYTHON" -m venv "$venv"
"$venv/bin/python" -m pip install --no-cache-dir -r "$here/cluster/requirements-cluster.txt"
unset LRI_COEFF_NO_VENV
source "$here/cluster/site.sh"
python "$here/scripts/stack.py" --pins
echo "setup_venv: done"
