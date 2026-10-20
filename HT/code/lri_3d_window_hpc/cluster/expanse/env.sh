# Expanse environment for ht3d jobs and login-node tools. Source it, never execute it:
#     source "$HT3D_RELEASE/cluster/expanse/env.sh" || exit 70
# The site bashrc/module init is not nounset-safe, so nounset is relaxed while sourcing
# and restored afterwards. Every required step is checked; any failure returns non-zero.
_ht3d_env() {
  module purge || { echo "env.sh: module purge failed" >&2; return 70; }
  local m
  for m in cpu/0.21.2a gcc/13.3.0 python/3.11.9 slurm/expanse/23.02.7; do
    module load "$m" || { echo "env.sh: module load $m failed" >&2; return 70; }
  done
  export HT3D_ACCOUNT=${HT3D_ACCOUNT:-yun124}
  export HT3D_DATA=${HT3D_DATA:-/expanse/lustre/scratch/$USER/temp_project/ht3d}
  export HT3D_VENV=${HT3D_VENV:-$HT3D_DATA/venv-py3119-np235-sp1170-nb0651}
  [ -f "$HT3D_VENV/bin/activate" ] || { echo "env.sh: no venv at $HT3D_VENV (run install.sh)" >&2; return 70; }
  # shellcheck disable=SC1091
  source "$HT3D_VENV/bin/activate" || { echo "env.sh: venv activation failed" >&2; return 70; }
  local py; py=$(command -v python) || { echo "env.sh: no python on PATH" >&2; return 70; }
  case "$py" in "$HT3D_VENV"/*) ;; *) echo "env.sh: python resolves to $py, not inside $HT3D_VENV" >&2; return 70;; esac
  export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_NUM_THREADS=1 BLIS_NUM_THREADS=1
  export MPLBACKEND=Agg PYTHONDONTWRITEBYTECODE=1
  # Node-local scratch for staging and the Numba JIT cache (never Lustre or NFS).
  if [ -n "${SLURM_JOB_ID:-}" ]; then
    export HT3D_NODE_SCRATCH=/scratch/$USER/job_$SLURM_JOB_ID
  else
    export HT3D_NODE_SCRATCH=${TMPDIR:-/tmp}/ht3d_$USER
  fi
  export NUMBA_CACHE_DIR=$HT3D_NODE_SCRATCH/numba_cache MPLCONFIGDIR=$HT3D_NODE_SCRATCH/mpl
  mkdir -p "$NUMBA_CACHE_DIR" "$MPLCONFIGDIR" || { echo "env.sh: cannot create $HT3D_NODE_SCRATCH" >&2; return 70; }
  return 0
}
_ht3d_u=0; case $- in *u*) _ht3d_u=1; set +u;; esac
_ht3d_env; _ht3d_rc=$?
[ "$_ht3d_u" = 1 ] && set -u
unset _ht3d_u; unset -f _ht3d_env
if [ "$_ht3d_rc" != 0 ]; then unset _ht3d_rc; return 70; fi
unset _ht3d_rc
