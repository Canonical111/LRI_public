#!/bin/bash
# Validation receipt for one release on one site/partition (single node).
# Submit only through `cluster/submit.py validate`; it passes the resources (one node,
# --ntasks=4 --cpus-per-task=4: srun MPI tests need the tasks) and exports HT3D_SITE
# HT3D_RELEASE_TAR HT3D_RELEASE_SHA256 HT3D_EXPECT_*. The receipt goes to
# $HT3D_DATA/validation/<git12>_<jobid>/receipt.json.
set -o pipefail
: "${HT3D_SITE:?}" "${HT3D_RELEASE_TAR:?}" "${HT3D_RELEASE_SHA256:?}" "${HT3D_EXPECT_FINGERPRINT:?}"
echo "ht3d validate job ${SLURM_JOB_ID} on $(hostname) start $(date -Is)"
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
python "$HT3D_STAGED/cluster/receipt.py" --out "$HT3D_DATA/validation/${HT3D_GIT_SHA:0:12}_$SLURM_JOB_ID" \
  --work "$HT3D_NODE_SCRATCH/work"
rc=$?
echo "ht3d validate exit $rc at $(date -Is)"
exit $rc
