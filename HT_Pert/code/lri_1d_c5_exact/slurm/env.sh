# Environment for lri_1d_c5_exact on symmetry (the lri_1d_c4_exact layer with C5 names). Source from bash; needs
# C5_ROOT (immutable read-only code snapshot) and C5_DATA (BeeGFS data root). Keeps the caller's -e/-u (saved from
# $-, not $(set +o), which reports errexit off). Also pins the C4P production result compared by gate A6e and defines
# the socket helpers c5_numa / c5_cores used by every job script (whole exclusive two-socket nodes; on the AMD nodes
# (NPS=4) a package spans four NUMA domains, on Intel one).
export PATH=/cm/shared/apps/slurm/current/bin:$PATH
__c5_flags=$-
set +eu
source /etc/profile.d/modules.sh
module purge
module load anaconda3/2023.07-2
__c5_rc=$?
[[ $__c5_flags == *e* ]] && set -e
[[ $__c5_flags == *u* ]] && set -u
unset __c5_flags
(( __c5_rc == 0 )) || { echo "module load anaconda3/2023.07-2 failed" >&2; exit 64; }
unset __c5_rc
: "${C5_ROOT:?export C5_ROOT}" "${C5_DATA:?export C5_DATA}"
[[ -f $C5_ROOT/run5.py && -d $C5_ROOT/lib5 ]] || { echo "C5_ROOT=$C5_ROOT is not the lri_1d_c5_exact checkout" >&2; exit 64; }
for __v in $(compgen -e); do case $__v in PYTHONHOME|PYTHONPATH|PYTHONOPTIMIZE|PYTHONSTARTUP|PYTHONWARNINGS|PYTHONUSERBASE) unset "$__v";; esac; done; unset __v
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MPLBACKEND=Agg
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_NUM_THREADS=1 NUMBA_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
C5_STACK=$(python -c 'import platform,numpy,scipy,numba,mpmath,pytest;print(platform.python_version(),numpy.__version__,scipy.__version__,numba.__version__)')
[[ $C5_STACK == "3.11.4 1.24.3 1.10.1 0.57.0" ]] || { echo "unexpected stack '$C5_STACK'" >&2; exit 64; }
# A6e reference (PLAN A6e): C4P production result, lri_1d_c4_exact snapshot a8b57b2e8475, gate record gates_L2000.txt.
# The path may be overridden; the sha256 may not (assemble.slurm and submit.sh check it before every use).
export C5_C4REF=${C5_C4REF:-<SCRATCH>/lri_1d_c4/results/a8b57b2e8475/c4_1d_L2000.npz}
export C5_C4REF_SHA256=62720cf5ac097f5e7f93250bc38e592c4de269b703abb5dd2544fb53994b51d2
c5_numa() {   # c5_numa S: comma-separated NUMA domains of package S (numactl --cpunodebind/--membind argument)
  lscpu -p=NODE,SOCKET | grep -v '^#' | awk -F, -v s="$1" '$2==s{print $1}' | sort -un | paste -sd, -
}
c5_cores() {  # c5_cores S: physical cores of package S (distinct CORE ids; hyperthreads not counted)
  lscpu -p=CORE,SOCKET | grep -v '^#' | awk -F, -v s="$1" '$2==s{print $1}' | sort -u | wc -l | tr -d ' '
}
echo "[env] $(command -v python) $C5_STACK; C5_ROOT=$C5_ROOT C5_DATA=$C5_DATA"
