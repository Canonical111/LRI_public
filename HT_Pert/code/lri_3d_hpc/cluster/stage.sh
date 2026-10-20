# Stage the immutable release into node-local scratch and verify it.
# Source it (do not execute) after ht3d_boot, with HT3D_RELEASE_LOCAL (the node-local copy of the
# tarball), HT3D_RELEASE_SHA256, HT3D_EXPECT_FINGERPRINT (the release fingerprint submit.py bound
# the job to) and HT3D_NODE_DIR (this job's node-local directory) set. Sets HT3D_STAGED (the verified copy),
# HT3D_RELEASE_FINGERPRINT (sha256 of its RELEASE.sha256) and HT3D_GIT_SHA.
# Idempotent per node; returns 74 on any mismatch (fail closed, never run on a bad copy).
_ht3d_stage() {
  local tar=${HT3D_RELEASE_LOCAL:?} want=${HT3D_RELEASE_SHA256:?} node=${HT3D_NODE_DIR:?}
  local expect=${HT3D_EXPECT_FINGERPRINT:?} dest=$node/rel got
  got=$(sha256sum "$tar" | cut -d' ' -f1) || { echo "stage: cannot read $tar" >&2; return 74; }
  [ "$got" = "$want" ] || { echo "stage: tarball sha256 $got != $want" >&2; return 74; }
  if [ ! -f "$dest/RELEASE.sha256" ]; then
    rm -rf "$dest.tmp.$$" && mkdir -p "$dest.tmp.$$" || { echo "stage: cannot create $dest" >&2; return 74; }
    tar -xf "$tar" -C "$dest.tmp.$$" || { echo "stage: extraction failed" >&2; return 74; }
    mv -T "$dest.tmp.$$" "$dest" 2>/dev/null || rm -rf "$dest.tmp.$$"   # another task on this node won
  fi
  ( cd "$dest" && sha256sum -c --quiet --strict RELEASE.sha256 ) || { echo "stage: staged release corrupted" >&2; return 74; }
  chmod -R a-w "$dest" 2>/dev/null
  HT3D_STAGED=$dest
  HT3D_RELEASE_FINGERPRINT=$(sha256sum "$dest/RELEASE.sha256" | cut -d' ' -f1)
  [ "$HT3D_RELEASE_FINGERPRINT" = "$expect" ] \
    || { echo "stage: release fingerprint $HT3D_RELEASE_FINGERPRINT != expected $expect" >&2; return 74; }
  HT3D_GIT_SHA=$(cat "$dest/GIT_SHA")
  export HT3D_STAGED HT3D_RELEASE_FINGERPRINT HT3D_GIT_SHA
  return 0
}
_ht3d_stage; _ht3d_src=$?; unset -f _ht3d_stage
if [ "$_ht3d_src" != 0 ]; then unset _ht3d_src; return 74; fi
unset _ht3d_src
