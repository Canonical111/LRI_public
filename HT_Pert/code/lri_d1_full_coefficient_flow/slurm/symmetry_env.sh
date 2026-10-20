# Environment for the S10 extension on symmetry. Source from bash; needs S10_ROOT (fixed code checkout) and
# S10_DATA (output root on BeeGFS). Keeps the caller's -e/-u (saved from $-, not $(set +o), which reports errexit off).
if [[ ${S10_LOCAL_TEST:-0} != 1 ]]; then
  export PATH=/cm/shared/apps/slurm/current/bin:$PATH
  __s10_flags=$-
  set +eu
  source /etc/profile.d/modules.sh
  module purge
  module load anaconda3/2023.07-2
  __s10_rc=$?
  [[ $__s10_flags == *e* ]] && set -e
  [[ $__s10_flags == *u* ]] && set -u
  unset __s10_flags
  (( __s10_rc == 0 )) || { echo "module load anaconda3/2023.07-2 failed" >&2; exit 64; }
fi
: "${S10_ROOT:?export S10_ROOT}" "${S10_DATA:?export S10_DATA}"
[[ -f $S10_ROOT/code/ragged_quotient.py ]] || { echo "S10_ROOT=$S10_ROOT is not the S10 checkout" >&2; exit 64; }
for __v in $(compgen -e); do case $__v in PYTHONHOME|PYTHONPATH|PYTHONOPTIMIZE|PYTHONSTARTUP|PYTHONWARNINGS|PYTHONUSERBASE) unset "$__v";; esac; done; unset __v
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MPLBACKEND=Agg
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
S10_STACK=$(python -c 'import platform,numpy,scipy;print(platform.python_version(),numpy.__version__,scipy.__version__)')
if [[ ${S10_LOCAL_TEST:-0} != 1 && $S10_STACK != "3.11.4 1.24.3 1.10.1" ]]; then echo "unexpected stack $S10_STACK" >&2; exit 64; fi
echo "[env] $(command -v python) $S10_STACK; S10_ROOT=$S10_ROOT S10_DATA=$S10_DATA"
