# Environment for lri_1d_c4_exact on symmetry. Source from bash; needs C4_ROOT (immutable code snapshot) and
# C4_DATA (BeeGFS data root). Keeps the caller's -e/-u (saved from $-, not $(set +o), which reports errexit off).
export PATH=/cm/shared/apps/slurm/current/bin:$PATH
__c4_flags=$-
set +eu
source /etc/profile.d/modules.sh
module purge
module load anaconda3/2023.07-2
__c4_rc=$?
[[ $__c4_flags == *e* ]] && set -e
[[ $__c4_flags == *u* ]] && set -u
unset __c4_flags
(( __c4_rc == 0 )) || { echo "module load anaconda3/2023.07-2 failed" >&2; exit 64; }
: "${C4_ROOT:?export C4_ROOT}" "${C4_DATA:?export C4_DATA}"
[[ -f $C4_ROOT/c4lib1d.py && -f $C4_ROOT/c4_run1d.py ]] || { echo "C4_ROOT=$C4_ROOT is not the lri_1d_c4_exact checkout" >&2; exit 64; }
for __v in $(compgen -e); do case $__v in PYTHONHOME|PYTHONPATH|PYTHONOPTIMIZE|PYTHONSTARTUP|PYTHONWARNINGS|PYTHONUSERBASE) unset "$__v";; esac; done; unset __v
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MPLBACKEND=Agg
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_NUM_THREADS=1 NUMBA_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
C4_STACK=$(python -c 'import platform,numpy,scipy,numba,mpmath,pytest;print(platform.python_version(),numpy.__version__,scipy.__version__,numba.__version__)')
[[ $C4_STACK == "3.11.4 1.24.3 1.10.1 0.57.0" ]] || { echo "unexpected stack '$C4_STACK'" >&2; exit 64; }
echo "[env] $(command -v python) $C4_STACK; C4_ROOT=$C4_ROOT C4_DATA=$C4_DATA"
