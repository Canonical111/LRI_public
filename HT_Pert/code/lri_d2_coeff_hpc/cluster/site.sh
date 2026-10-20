# shellcheck shell=bash
# Per-site software environment of lri_d2_coeff_hpc. Source it from bash with LRI_COEFF_SITE set:
#
#   LRI_COEFF_SITE=expanse  source cluster/site.sh     # or symmetry
#
# cluster/job.sbatch sources the staged copy on the compute node; on a login node source it before
# running scripts/*.py. It
#   - loads the compiler and Python stack (Expanse: Lmod modules; symmetry: system g++, Slurm on PATH),
#   - clears inherited Python, pytest, Numba, OpenMP and BLAS settings and activates the dedicated venv
#     LRI_COEFF_VENV (default ~/lri2d_coeff/venv; LRI_COEFF_NO_VENV=1 skips this, for setup_venv.sh),
#   - exports the shared data root LRI_COEFF_DATA (default per site),
#   - keeps the caller's errexit/nounset options, and returns non-zero (never exits) on failure.
# Paths say lri2d_coeff, never lri2d: on Expanse ~/lri2d and temp_project/lri2d belong to another project.

__lri_coeff_site() {
  local v gxx
  case ${LRI_COEFF_SITE:-} in
    expanse)
      : "${LRI_COEFF_DATA:=/expanse/lustre/scratch/$USER/temp_project/lri2d_coeff}"
      : "${LRI_COEFF_VENV:=$HOME/lri2d_coeff/venv}"
      # Lmod must run in this shell (a pipe or $(...) would load the modules in a subshell).
      declare -F module >/dev/null || { echo "site.sh: Lmod 'module' is unavailable" >&2; return 2; }
      # One module per call: a multi-module load on one line has been seen to fail silently on Expanse.
      module purge >/dev/null 2>&1
      for v in cpu/0.21.2a gcc/13.3.0 python/3.11.9 slurm/expanse/23.02.7; do
        module load "$v" >/dev/null 2>&1 || { echo "site.sh: module load $v failed" >&2; return 2; }
      done
      gxx=$(command -v g++) || { echo "site.sh: no g++ after module load" >&2; return 2; }
      [[ $(g++ -dumpfullversion 2>/dev/null) == 13.3.0 ]] \
        || { echo "site.sh: expected gcc 13.3.0 from the modules, got $gxx" >&2; return 2; }
      LRI_COEFF_BASE_PYTHON=$(command -v python3.11) \
        || { echo "site.sh: no python3.11 after module load" >&2; return 2; }
      ;;
    symmetry)
      : "${LRI_COEFF_DATA:=/mnt/beegfs/$USER/lri2d_coeff}"
      : "${LRI_COEFF_VENV:=$HOME/lri2d_coeff/venv}"
      case :$PATH: in
        *:/cm/shared/apps/slurm/current/bin:*) ;;
        *) PATH=/cm/shared/apps/slurm/current/bin:$PATH ;;
      esac
      gxx=/usr/bin/g++
      [[ -x $gxx ]] || { echo "site.sh: $gxx missing" >&2; return 2; }
      LRI_COEFF_BASE_PYTHON=/cm/shared/apps/anaconda3/2023.07-2/bin/python3.11
      ;;
    *)
      echo "site.sh: set LRI_COEFF_SITE=expanse or symmetry (got '${LRI_COEFF_SITE:-}')" >&2
      return 2 ;;
  esac
  # Inherited settings must not change imports, threading, compilation or test selection.
  for v in $(compgen -e); do
    case $v in
      PYTHON*|PYTEST_*|NUMBA_*|OMP_*|GOMP_*|KMP_*|MKL_*|OPENBLAS_*|VIRTUAL_ENV|CONDA_PREFIX|LRI_COEFF_NATIVE_CACHE)
        unset "$v" ;;
    esac
  done
  export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
  export CXX=$gxx PATH
  export LRI_COEFF_SITE LRI_COEFF_DATA LRI_COEFF_VENV LRI_COEFF_BASE_PYTHON
  if [[ ${LRI_COEFF_NO_VENV:-0} != 1 ]]; then
    [[ -f $LRI_COEFF_VENV/bin/activate ]] \
      || { echo "site.sh: no venv at $LRI_COEFF_VENV (run cluster/setup_venv.sh once)" >&2; return 2; }
    source "$LRI_COEFF_VENV/bin/activate"
    [[ $(command -v python) == "$LRI_COEFF_VENV/bin/python" ]] \
      || { echo "site.sh: python is not the venv's after activation" >&2; return 2; }
  fi
  return 0
}

__lri_coeff_opts=$-
set +eu
# At top level, not inside the function: declarations in the profile scripts must stay global.
if [[ ${LRI_COEFF_SITE:-} == expanse ]] && ! declare -F module >/dev/null; then
  source /etc/profile >/dev/null 2>&1
fi
__lri_coeff_site
__lri_coeff_rc=$?
case $__lri_coeff_opts in *e*) set -e ;; esac
case $__lri_coeff_opts in *u*) set -u ;; esac
unset __lri_coeff_opts
unset -f __lri_coeff_site
return "$__lri_coeff_rc"
