# Environment for ht3d jobs and login-node tools on Expanse and symmetry.
# Source it, never execute it:      source "$HT3D_STAGED/cluster/env.sh" || exit 70
# The site is HT3D_SITE (expanse|symmetry) or detected from the file systems; a mismatch
# between the two refuses. Site module init is not nounset-safe, so nounset is relaxed while
# sourcing and restored afterwards. Every required step is checked; failures return 70.
_ht3d_env() {
  local here detected
  here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P) || return 70
  if [ -d /expanse/lustre ]; then detected=expanse
  elif [ -d /mnt/beegfs ] && [ -d /cm/shared/apps/slurm ]; then detected=symmetry
  else detected=unknown; fi
  HT3D_SITE=${HT3D_SITE:-$detected}
  if [ "$HT3D_SITE" != "$detected" ]; then
    echo "env: HT3D_SITE=$HT3D_SITE but this host looks like $detected" >&2; return 70
  fi
  case $HT3D_SITE in expanse|symmetry) ;; *) echo "env: unsupported site $HT3D_SITE" >&2; return 70;; esac
  # shellcheck disable=SC1090
  source "$here/sites/$HT3D_SITE.sh" || { echo "env: cannot read site profile" >&2; return 70; }
  ht3d_site_init || return 70
  export HT3D_SITE HT3D_DATA HT3D_VENV HT3D_LOCK_ROOT HT3D_ACCOUNT HT3D_MPI_LAUNCHERS
  [ -f "$HT3D_VENV/bin/activate" ] || { echo "env: no venv at $HT3D_VENV (see cluster/install.sh)" >&2; return 70; }
  unset PYTHONPATH PYTHONHOME PYTHONSTARTUP PYTHONOPTIMIZE PYTHONWARNINGS PYTHONINSPECT
  # shellcheck disable=SC1091
  source "$HT3D_VENV/bin/activate" || { echo "env: venv activation failed" >&2; return 70; }
  local py; py=$(command -v python) || { echo "env: no python on PATH" >&2; return 70; }
  case "$py" in "$HT3D_VENV"/*) ;; *) echo "env: python resolves to $py, not inside $HT3D_VENV" >&2; return 70;; esac
  export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
  # One BLAS/Numba thread unless a stage asks otherwise; OpenMP threads are set per solve.
  export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 BLIS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 OMP_NUM_THREADS=1
  export OMP_PROC_BIND=close OMP_PLACES=cores OMP_WAIT_POLICY=PASSIVE GOMP_SPINCOUNT=0
  export RDMAV_FORK_SAFE=1 IBV_FORK_SAFE=1   # ranks fork the compiler probe after MPI_Init
  CXX=$(command -v g++) || { echo "env: no g++" >&2; return 70; }
  export CXX
  # Node-local scratch for staging, the Numba JIT cache and the native library cache
  # (never Lustre, BeeGFS or NFS: their flock and mmap semantics differ).
  if [ -n "${SLURM_JOB_ID:-}" ]; then
    HT3D_NODE_SCRATCH=$(ht3d_node_scratch) || return 70
  else
    HT3D_NODE_SCRATCH=${TMPDIR:-/tmp}/ht3d_pert_$USER
  fi
  export HT3D_NODE_SCRATCH
  export NUMBA_CACHE_DIR=$HT3D_NODE_SCRATCH/numba HT3D_NATIVE_CACHE=$HT3D_NODE_SCRATCH/native
  mkdir -p "$NUMBA_CACHE_DIR" "$HT3D_NATIVE_CACHE" "$HT3D_NODE_SCRATCH/tmp" \
    || { echo "env: cannot create $HT3D_NODE_SCRATCH" >&2; return 70; }
  export TMPDIR=$HT3D_NODE_SCRATCH/tmp
  return 0
}
_ht3d_u=0; case $- in *u*) _ht3d_u=1; set +u;; esac
_ht3d_env; _ht3d_rc=$?
[ "$_ht3d_u" = 1 ] && set -u
unset _ht3d_u; unset -f _ht3d_env
if [ "$_ht3d_rc" != 0 ]; then unset _ht3d_rc; return 70; fi
unset _ht3d_rc

# The allocation must be exactly what cluster/submit.py requested: inherited SBATCH_* variables
# override #SBATCH lines and command-line values can be shadowed, so the job checks itself.
ht3d_check_allocation() {
  local bad=0 pair want_var have_var want have
  for pair in PARTITION:SLURM_JOB_PARTITION NODES:SLURM_JOB_NUM_NODES NTASKS:SLURM_NTASKS \
              CPUS:SLURM_CPUS_PER_TASK MEM_MB:SLURM_MEM_PER_NODE; do
    want_var=HT3D_EXPECT_${pair%%:*}; have_var=${pair#*:}
    want=${!want_var:-}; have=${!have_var:-}
    if [ -z "$want" ]; then echo "allocation: $want_var is not set" >&2; bad=1; continue; fi
    [ "$want" = "$have" ] || { echo "allocation: $have_var=$have, expected $want" >&2; bad=1; }
  done
  return $bad
}
