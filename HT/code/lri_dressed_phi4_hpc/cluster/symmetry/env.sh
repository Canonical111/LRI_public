# Source from a symmetry login or batch shell:  source <code>/cluster/symmetry/env.sh
# Sets Slurm PATH, modules, the tested venv, single-threaded BLAS and a node-local Numba cache.
export PATH=/cm/shared/apps/slurm/current/bin:$PATH
# Site and venv scripts reference unset variables: relax nounset while sourcing them.
_lri_u=0; case $- in *u*) _lri_u=1; set +u;; esac
[ -f /etc/profile.d/modules.sh ] && source /etc/profile.d/modules.sh
export LRI_CODE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export LRI_ROOT="${LRI_ROOT:-/mnt/beegfs/zzheng1/lri_dressed}"
export LRI_VENV="${LRI_VENV:-$HOME/lri_dressed/venv}"
source "$LRI_VENV/bin/activate"
[ "$_lri_u" = 1 ] && set -u; unset _lri_u
export PYTHONPATH="$LRI_CODE/src${PYTHONPATH:+:$PYTHONPATH}"
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_NUM_THREADS=1
if [ -n "${SLURM_JOB_ID:-}" ] && [ -d /local1 ] && [ -w /local1 ]; then
  export NUMBA_CACHE_DIR="/local1/numba_${SLURM_JOB_ID}"
else
  export NUMBA_CACHE_DIR="${TMPDIR:-/tmp}/numba_${USER}_${SLURM_JOB_ID:-login}"
fi
mkdir -p "$NUMBA_CACHE_DIR"
