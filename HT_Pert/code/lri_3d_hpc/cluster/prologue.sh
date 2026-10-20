# Common job prologue, sourced by every cluster/*.sbatch after ht3d_boot has copied and
# verified the release tarball locally and authenticated this file and stage.sh against the
# expected release manifest. Requires HT3D_SITE, HT3D_RELEASE_LOCAL, HT3D_RELEASE_SHA256,
# HT3D_EXPECT_FINGERPRINT, HT3D_BOOT and HT3D_NODE_DIR. Stages the release, loads the
# environment, checks the allocation. Returns 74 (staging), 70 (environment) or 3 (allocation).
source "$HT3D_BOOT/cluster/stage.sh" || return 74
source "$HT3D_STAGED/cluster/env.sh" || return 70
ht3d_check_allocation || return 3
echo "release $HT3D_GIT_SHA fingerprint $HT3D_RELEASE_FINGERPRINT staged at $HT3D_STAGED"
echo "python $(command -v python); CXX $CXX; node scratch $HT3D_NODE_SCRATCH"
