#!/bin/bash
# One Slurm job of lri_d2_coeff_hpc on Expanse or symmetry: LRI_COEFF_JOB=validate or task.
#
# Submit only with scripts/submit.py. It sets every resource on the command line (partition, CPUs or
# --exclusive, --mem, --time, --signal=B:USR1@900, --no-requeue, absolute --output and --chdir) and
# exports, with --export=ALL:
#   LRI_COEFF_SITE, LRI_COEFF_DATA, LRI_COEFF_JOB, LRI_COEFF_RELEASE (release .tar on the data root),
#   LRI_COEFF_RELEASE_SHA256;
#   validate: LRI_COEFF_RECEIPT_BASE;
#   task:     LRI_COEFF_MANIFEST, LRI_COEFF_MANIFEST_SHA256, LRI_COEFF_INDEX, LRI_COEFF_RECEIPT.
#
# The code runs from the checksummed release tar, unpacked into a private node-local job directory, which
# is also the working directory and holds the caches and the solver's checkpoints. Shared writes: the
# result and its lock, one checkpoint archive per task (scripts/ckpt_sync.py), receipts and the log.
# The Python process runs in the background (cluster/forward.sh) so that this shell, the only receiver of
# B:USR1, can forward USR1/TERM/INT to it; the solver then checkpoints at its next complete stage and
# exits 75 (resume = submit the task again).
set -o pipefail
set -e
umask 022   # nothing this job creates is group/other-writable
die() { echo "job: $1" >&2; exit "${2:-2}"; }

: "${SLURM_JOB_ID:?not inside a Slurm job}"
for v in LRI_COEFF_SITE LRI_COEFF_DATA LRI_COEFF_JOB LRI_COEFF_RELEASE LRI_COEFF_RELEASE_SHA256; do
  [[ -n ${!v:-} ]] || die "$v is not set (submit with scripts/submit.py)"
done
case $LRI_COEFF_JOB in
  validate) [[ -n ${LRI_COEFF_RECEIPT_BASE:-} ]] || die "LRI_COEFF_RECEIPT_BASE is not set" ;;
  task)
    for v in LRI_COEFF_MANIFEST LRI_COEFF_MANIFEST_SHA256 LRI_COEFF_INDEX LRI_COEFF_RECEIPT; do
      [[ -n ${!v:-} ]] || die "$v is not set"
    done ;;
  *) die "LRI_COEFF_JOB must be validate or task" ;;
esac
# Node-local job directory: a private (0700) directory made by mktemp under a parent whose whole path is
# trusted (each component a real directory owned by root or by us; group/other-writable only if root-owned
# and sticky, like /local1). Only that directory is removed at the end. Everything runs from inside it.
case $LRI_COEFF_SITE in
  expanse)  parents=("/scratch/$USER/job_$SLURM_JOB_ID" "/scratch/$USER" /scratch) ;;
  symmetry) parents=(/local1) ;;
  *) die "unknown LRI_COEFF_SITE '$LRI_COEFF_SITE'" ;;
esac
trusted_path() {
  local p=$1 owner mode me
  me=$(id -u)
  while :; do
    [[ -d $p && ! -L $p ]] || return 1
    read -r owner mode < <(stat -c '%u %a' -- "$p") || return 1
    [[ $owner == 0 || $owner == "$me" ]] || return 1
    if (( 8#$mode & 8#022 )); then [[ $owner == 0 ]] && (( 8#$mode & 8#1000 )) || return 1; fi
    [[ $p == / ]] && return 0
    p=$(dirname -- "$p")
  done
}
JOBDIR=
for parent in "${parents[@]}"; do
  if trusted_path "$parent" && JOBDIR=$(mktemp -d "$parent/lri_coeff.$SLURM_JOB_ID.XXXXXX" 2>/dev/null); then break; fi
  JOBDIR=
done
[[ -n $JOBDIR ]] || die "no trusted node-local directory among: ${parents[*]}" 74
[[ -d $JOBDIR && ! -L $JOBDIR && -O $JOBDIR ]] || die "unexpected job directory $JOBDIR" 74
cleanup() {
  cd /
  if [[ -e $JOBDIR/UNPUBLISHED ]]; then   # scripts/ckpt_sync.py could not publish the newest checkpoint
    echo "job: keeping $JOBDIR on $(hostname): its newest checkpoint was not published (node-local storage" \
      "is wiped by the site after the job)" >&2
  else
    rm -rf -- "$JOBDIR"
  fi
}
trap cleanup EXIT
mkdir "$JOBDIR/tmp" "$JOBDIR/work" "$JOBDIR/checkpoints"
cd "$JOBDIR/work"
echo "job: $LRI_COEFF_JOB on $(hostname) job $SLURM_JOB_ID partition ${SLURM_JOB_PARTITION:-?}" \
  "cpus_on_node ${SLURM_CPUS_ON_NODE:-?} mem_per_node ${SLURM_MEM_PER_NODE:-?}M at $(date '+%Y-%m-%dT%H:%M:%S%z')"
echo "job: cpu $(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2- | sed 's/^ *//')"

# Stage: copy the tar once, checksum the node-local copy, unpack it, then check every file.
cp -- "$LRI_COEFF_RELEASE" "$JOBDIR/release.tar" || die "cannot copy $LRI_COEFF_RELEASE" 74
got=$(sha256sum "$JOBDIR/release.tar" | cut -d' ' -f1)
[[ $got == "$LRI_COEFF_RELEASE_SHA256" ]] || die "release checksum $got != $LRI_COEFF_RELEASE_SHA256" 74
tar -xf "$JOBDIR/release.tar" -C "$JOBDIR" || die "cannot unpack the release" 74
CODE=$JOBDIR/lri_d2_coeff_hpc
[[ -f $CODE/cluster/site.sh ]] || die "release has no lri_d2_coeff_hpc/cluster/site.sh" 74
source "$CODE/cluster/site.sh" || die "site environment failed"
[[ $- == *e* ]] || die "errexit lost after sourcing site.sh"
python "$CODE/tests/verify_manifest.py" || die "staged tree does not match MANIFEST.sha256" 74

# Threads = distinct physical cores in this process's allowed CPU set, capped by the allocation.
phys_alloc() {
  local a
  a=$(grep -m1 Cpus_allowed_list /proc/self/status | cut -f2)
  lscpu -p=CPU,CORE | grep -v '^#' | awk -F, -v a="$a" '
    BEGIN { n = split(a, r, ","); for (i = 1; i <= n; i++) { m = split(r[i], b, "-"); lo = b[1]; hi = (m == 2 ? b[2] : b[1]); for (c = lo; c <= hi; c++) ok[c] = 1 } }
    ($1 in ok) && !($2 in seen) { seen[$2] = 1; k++ }
    END { print k + 0 }'
}
pa=$(phys_alloc)
cap=${SLURM_CPUS_ON_NODE:-1}
threads=$(( pa < cap ? pa : cap ))
(( threads >= 1 )) || die "no usable cores (physical $pa, allocated $cap)"
echo "job: $threads threads (physical cores in affinity $pa, SLURM_CPUS_ON_NODE $cap)"
export LRI_COEFF_THREADS=$threads OMP_PLACES=cores OMP_PROC_BIND=close PYTHONUNBUFFERED=1
export NUMBA_CACHE_DIR=$JOBDIR/numba_cache LRI_COEFF_NATIVE_CACHE=$JOBDIR/native_cache TMPDIR=$JOBDIR/tmp
export LRI_COEFF_LOCAL_CHECKPOINT=$JOBDIR/checkpoints   # task mode: see scripts/ckpt_sync.py

case $LRI_COEFF_JOB in
  validate)
    python "$CODE/scripts/stack.py" --pins || die "software stack differs from the tested pins" 3
    cmd=(python -u "$CODE/scripts/validate_cluster.py" --receipt-base "$LRI_COEFF_RECEIPT_BASE" --work "$JOBDIR/work") ;;
  task)
    python "$CODE/scripts/stack.py" --pins --match "$LRI_COEFF_RECEIPT" \
      || die "software stack differs from the validated one in $LRI_COEFF_RECEIPT" 3
    cmd=(python -u "$CODE/scripts/run_task.py" --manifest "$LRI_COEFF_MANIFEST" --index "$LRI_COEFF_INDEX") ;;
esac

source "$CODE/cluster/forward.sh"
run_forwarding "${cmd[@]}" && rc=0 || rc=$?
echo "job: exit $rc at $(date '+%Y-%m-%dT%H:%M:%S%z')"
exit "$rc"
