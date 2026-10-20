#!/bin/bash
# One HT3D campaign job: cluster/ht3d_stage.py run (pipeline stages, gate, solves).
# Submit only through cluster/submit.py, which passes every resource on the command line and
# exports HT3D_SITE HT3D_RELEASE_TAR HT3D_RELEASE_SHA256 HT3D_CAMPAIGN HT3D_CUTOFF HT3D_STAGES
# HT3D_LANES HT3D_THREADS HT3D_BLAS_THREADS HT3D_SHARDS [HT3D_SOLVE_CUTOFFS HT3D_SCHEMES]
# and HT3D_EXPECT_*. Array tasks run shard SLURM_ARRAY_TASK_ID of HT3D_SHARDS.
# No `set -u` before the site environment (module init is not nounset-safe).
set -o pipefail
: "${HT3D_SITE:?}" "${HT3D_RELEASE_TAR:?}" "${HT3D_RELEASE_SHA256:?}" "${HT3D_EXPECT_FINGERPRINT:?}" "${HT3D_CAMPAIGN:?}" \
  "${HT3D_CUTOFF:?}" "${HT3D_STAGES:?}" "${HT3D_LANES:?}" "${HT3D_THREADS:?}" \
  "${HT3D_BLAS_THREADS:?}" "${HT3D_SHARDS:?}"
echo "ht3d stages job ${SLURM_JOB_ID} (array ${SLURM_ARRAY_JOB_ID:-none}_${SLURM_ARRAY_TASK_ID:-}) on $(hostname) start $(date -Is)"
case $HT3D_SITE in
  expanse) HT3D_NODE_DIR=/scratch/$USER/job_$SLURM_JOB_ID ;;
  symmetry) HT3D_NODE_DIR=/local1/$USER/ht3d_$SLURM_JOB_ID
            trap 'chmod -R u+w "$HT3D_NODE_DIR" 2>/dev/null; rm -rf "$HT3D_NODE_DIR"' EXIT ;;
  *) echo "unknown site $HT3D_SITE" >&2; exit 2 ;;
esac
export HT3D_NODE_DIR
# Bootstrap (identical in every cluster/*.sbatch): copy the release tarball to node-local
# scratch, verify that copy, and authenticate the two bootstrap scripts against the release
# manifest whose fingerprint submit.py bound this job to, all before sourcing anything.
ht3d_boot() {
  local d=$HT3D_NODE_DIR/boot
  mkdir -p "$d" || return 74
  cp "$HT3D_RELEASE_TAR" "$d/release.tar.$$" || { echo "boot: cannot copy $HT3D_RELEASE_TAR" >&2; return 74; }
  [ "$(sha256sum "$d/release.tar.$$" | cut -d' ' -f1)" = "$HT3D_RELEASE_SHA256" ] \
    || { echo "boot: release tarball checksum mismatch" >&2; return 74; }
  mv -f "$d/release.tar.$$" "$d/release.tar" || return 74
  rm -rf "$d/x" && mkdir "$d/x" && tar -xf "$d/release.tar" -C "$d/x" RELEASE.sha256 cluster/stage.sh cluster/prologue.sh \
    || { echo "boot: cannot extract the bootstrap" >&2; return 74; }
  [ "$(sha256sum "$d/x/RELEASE.sha256" | cut -d' ' -f1)" = "$HT3D_EXPECT_FINGERPRINT" ] \
    || { echo "boot: release manifest is not the expected one" >&2; return 74; }
  [ "$(grep -cE '^[0-9a-f]{64}  cluster/(stage|prologue)\.sh$' "$d/x/RELEASE.sha256")" = 2 ] \
    && ( cd "$d/x" && grep -E '^[0-9a-f]{64}  cluster/(stage|prologue)\.sh$' RELEASE.sha256 | sha256sum -c --quiet --strict - ) \
    || { echo "boot: bootstrap scripts fail the release manifest" >&2; return 74; }
  export HT3D_RELEASE_LOCAL=$d/release.tar HT3D_BOOT=$d/x
}
ht3d_boot || exit 74
# shellcheck disable=SC2320  # $? is the status of source (prologue returns 74/70/3 on failure)
source "$HT3D_BOOT/cluster/prologue.sh" || exit $?
set -euo pipefail
shard=${SLURM_ARRAY_TASK_ID:-0}
args=(run --campaign "$HT3D_CAMPAIGN" --cutoff "$HT3D_CUTOFF" --stages "$HT3D_STAGES"
      --lanes "$HT3D_LANES" --threads "$HT3D_THREADS" --blas-threads "$HT3D_BLAS_THREADS"
      --shard "$shard/$HT3D_SHARDS")
if [ -n "${HT3D_SOLVE_CUTOFFS:-}" ]; then read -r -a c <<<"$HT3D_SOLVE_CUTOFFS"; args+=(--solve-cutoffs "${c[@]}"); fi
if [ -n "${HT3D_SCHEMES:-}" ]; then read -r -a s <<<"$HT3D_SCHEMES"; args+=(--schemes "${s[@]}"); fi
set +e
python "$HT3D_STAGED/cluster/ht3d_stage.py" "${args[@]}"
rc=$?
echo "ht3d stages exit $rc at $(date -Is)"
exit $rc
