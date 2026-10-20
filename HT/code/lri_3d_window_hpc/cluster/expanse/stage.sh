# Stage the immutable release tarball into node-local scratch and verify it (source; do not execute).
#   HT3D_RELEASE_TAR, HT3D_RELEASE_TAR_SHA256 must be set; sets HT3D_STAGED to the verified copy.
#   Returns 74 on any mismatch (fail closed: never run on a bad copy; see hpc-clusters expanse notes).
_ht3d_stage() {
  local tar=${HT3D_RELEASE_TAR:?} want=${HT3D_RELEASE_TAR_SHA256:?}
  local node=/scratch/$USER/job_${SLURM_JOB_ID:?not inside a Slurm job}
  local dest=$node/rel
  mkdir -p "$dest" || { echo "stage: cannot create $dest" >&2; return 74; }
  local got; got=$(sha256sum "$tar" | cut -d' ' -f1) || { echo "stage: cannot read $tar" >&2; return 74; }
  [ "$got" = "$want" ] || { echo "stage: tarball sha256 $got != $want" >&2; return 74; }
  tar -xf "$tar" -C "$dest" || { echo "stage: extraction failed" >&2; return 74; }
  ( cd "$dest" && sha256sum -c --quiet --strict RELEASE.sha256 ) || { echo "stage: staged release corrupted" >&2; return 74; }
  export HT3D_STAGED=$dest
  return 0
}
_ht3d_stage; _ht3d_src=$?; unset -f _ht3d_stage
if [ "$_ht3d_src" != 0 ]; then unset _ht3d_src; return 74; fi
unset _ht3d_src
