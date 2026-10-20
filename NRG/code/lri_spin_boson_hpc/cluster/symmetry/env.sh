# Sourced by every symmetry job and by the login-node tools. Requires a frozen code copy.
: "${LRI_SPIN_CODE:?Set LRI_SPIN_CODE to a frozen code directory (with GIT_SHA)}"
if [ ! -f "$LRI_SPIN_CODE/GIT_SHA" ]; then
  echo "Refusing: $LRI_SPIN_CODE has no GIT_SHA (not a frozen copy)" >&2
  return 2 2>/dev/null || exit 2
fi
export LRI_SPIN_BASE="${LRI_SPIN_BASE:-/mnt/beegfs/zzheng1/lri_spin}"
_lri_u=$-; set +u
source /etc/profile.d/modules.sh
module load python/3.13-mamba
source "$LRI_SPIN_BASE/venv/bin/activate"
case $_lri_u in *u*) set -u;; esac; unset _lri_u
export PATH=/cm/shared/apps/slurm/current/bin:$PATH
export PYTHONPATH="$LRI_SPIN_CODE/src"
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_NUM_THREADS=1
# Keep the frozen code directory free of caches.
export PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS="-p no:cacheprovider"
