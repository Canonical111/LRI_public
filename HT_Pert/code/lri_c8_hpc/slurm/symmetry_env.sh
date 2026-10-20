# Common environment of the lri_c8 batch and submit scripts on symmetry. Source it from bash.
# Needs C8_ROOT (code checkout at a FIXED path; do not edit it while a campaign runs: the
# Numba cache index is keyed on source paths and mtimes) and C8_DATA (data root on BeeGFS).
# C8_CACHE_ROLE=node (batch jobs) or login (submit wrapper) selects the Numba cache.
# C8_LOCAL_TEST=1 (tests and mocks only): no module load, no stack check, and the real
# Slurm binaries are NOT put ahead of the test's shims on PATH.
if [[ ${C8_LOCAL_TEST:-0} != 1 ]]; then
  export PATH=/cm/shared/apps/slurm/current/bin:$PATH
  # Save the caller's -e/-u from $- (NOT $(set +o): bash clears errexit inside command
  # substitutions, so that would hand back "set +o errexit").
  __c8_flags=$-
  set +eu   # site module scripts are not written for errexit/nounset
  source /etc/profile.d/modules.sh
  module purge
  module load anaconda3/2023.07-2
  __c8_rc=$?
  [[ $__c8_flags == *e* ]] && set -e
  [[ $__c8_flags == *u* ]] && set -u
  unset __c8_flags
  (( __c8_rc == 0 )) || { echo "module load anaconda3/2023.07-2 failed" >&2; exit 64; }
fi
: "${C8_ROOT:?export C8_ROOT (slurm/submit_defq.sh does)}"
: "${C8_DATA:?export C8_DATA (slurm/submit_defq.sh does)}"
[[ -f $C8_ROOT/src/lri_c8/cli.py ]] || { echo "C8_ROOT=$C8_ROOT is not an lri_c8 checkout" >&2; exit 64; }
command -v python >/dev/null || { echo "no python after module load" >&2; exit 64; }
# sbatch exports the submitting shell's environment: drop inherited Numba, pytest and
# Python interpreter settings (thread caps, JIT switches, test filters, PYTHONHOME, -O).
for __c8_v in $(compgen -e); do
  case $__c8_v in NUMBA_*|PYTEST_*|PYTHONHOME|PYTHONOPTIMIZE|PYTHONSTARTUP|PYTHONINSPECT|PYTHONWARNINGS|PYTHONUSERBASE) unset "$__c8_v" ;; esac
done; unset __c8_v
# Run from source (no pip install on symmetry). No user site-packages, no cwd on sys.path,
# no .pyc writes into the NFS checkout, unbuffered logs, single-threaded BLAS.
export PYTHONPATH="$C8_ROOT/src" PYTHONNOUSERSITE=1 PYTHONSAFEPATH=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
# runtime.threading_layer is part of every checkpoint's configuration: pin it so a silent
# fallback on one node becomes a loud failure instead of an unresumable checkpoint.
# Forced, not inherited: the validated layer is recorded in the receipt and campaign.
export NUMBA_THREADING_LAYER=tbb
C8_STACK=$(python -c 'import platform,numpy,numba,scipy;print(platform.python_version(),numpy.__version__,numba.__version__,scipy.__version__)')
if [[ ${C8_LOCAL_TEST:-0} != 1 && $C8_STACK != "3.11.4 1.24.3 0.57.0 1.10.1" ]]; then
  echo "unexpected Python stack: $C8_STACK ($(command -v python))" >&2; exit 64
fi
C8_SRC16=$(python -c 'from lri_c8.io import source_digest;print(source_digest()[:16])')
# Digest-keyed cache: Numba's own index does not notice edits to _core/basis.py functions
# compiled into residual.py kernels, so a cache never outlives the source it was built from.
export C8_SRC16 NUMBA_CACHE_DIR="$C8_DATA/numba_cache/${C8_CACHE_ROLE:-node}-src-${C8_SRC16}-py${C8_STACK// /-}"
echo "[env] $(command -v python) stack ${C8_STACK}; source ${C8_SRC16}; NUMBA_CACHE_DIR=$NUMBA_CACHE_DIR; layer $NUMBA_THREADING_LAYER"

# First hardware thread of every physical core in this process's allowed CPU set.
c8_phys_cpus() {
  local allowed
  allowed=${C8_TEST_CPUS_ALLOWED:-$(awk '/^Cpus_allowed_list/{print $2}' /proc/self/status)}
  lscpu -p=CPU,CORE | awk -F, -v a="$allowed" '
    BEGIN{n=split(a,r,","); for(i=1;i<=n;i++){m=split(r[i],b,"-"); hi=(m==2?b[2]:b[1]); for(c=b[1];c<=hi;c++) ok[c]=1}}
    !/^#/ && ($1 in ok) && !seen[$2]++ {printf "%s%s", (k++ ? "," : ""), $1} END {print ""}'
}
c8_count() { local IFS=,; set -- $1; echo $#; }
