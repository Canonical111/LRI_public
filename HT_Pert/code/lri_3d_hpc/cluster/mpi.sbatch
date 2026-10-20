#!/bin/bash
# Multi-node MPI job: HT3D_MPI_MODE=validate (multi-node receipt: launcher, cross-node flock,
# check_mpi_backend, L14 MPI solves vs serial) or solve (production MPI solves from a store).
# Submit only through cluster/submit.py (validate-mpi | solve-mpi); it passes the resources
# (--nodes N --ntasks-per-node R --cpus-per-task C, whole nodes) and exports HT3D_SITE
# HT3D_RELEASE_TAR HT3D_RELEASE_SHA256 HT3D_MPI_MODE HT3D_EXPECT_* and, by mode, HT3D_STORE
# HT3D_SERIAL_GATES (validate) or HT3D_CAMPAIGN HT3D_CUTOFF HT3D_SOLVE_CUTOFFS HT3D_SCHEMES (solve).
set -o pipefail
: "${HT3D_SITE:?}" "${HT3D_RELEASE_TAR:?}" "${HT3D_RELEASE_SHA256:?}" "${HT3D_EXPECT_FINGERPRINT:?}" "${HT3D_MPI_MODE:?}"
echo "ht3d mpi-$HT3D_MPI_MODE job ${SLURM_JOB_ID} on ${SLURM_JOB_NODELIST} start $(date -Is)"
case $HT3D_SITE in
  expanse) HT3D_NODE_DIR=/scratch/$USER/job_$SLURM_JOB_ID ;;
  symmetry) HT3D_NODE_DIR=/local1/$USER/ht3d_$SLURM_JOB_ID ;;
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
nodes=$SLURM_JOB_NUM_NODES
if [ "$HT3D_SITE" = symmetry ]; then
  trap 'srun --nodes=$nodes --ntasks=$nodes --ntasks-per-node=1 -c 1 bash -c "chmod -R u+w $HT3D_NODE_DIR; rm -rf $HT3D_NODE_DIR" >/dev/null 2>&1' EXIT
fi
# Stage the release and create the node-local caches on every node (same paths everywhere).
# Every node copies, verifies and authenticates on its own before sourcing (ht3d_boot).
export -f ht3d_boot
srun --nodes="$nodes" --ntasks="$nodes" --ntasks-per-node=1 -c 1 bash -c '
  mkdir -p "$NUMBA_CACHE_DIR" "$HT3D_NATIVE_CACHE" "$TMPDIR" || exit 74
  ht3d_boot || exit 74
  source "$HT3D_BOOT/cluster/stage.sh" || exit 74
  echo "staged $(hostname) $HT3D_RELEASE_FINGERPRINT"' || { echo "per-node staging failed" >&2; exit 74; }
set +e
python "$HT3D_STAGED/cluster/ht3d_mpi.py" "$HT3D_MPI_MODE"
rc=$?
echo "ht3d mpi-$HT3D_MPI_MODE exit $rc at $(date -Is)"
exit $rc
