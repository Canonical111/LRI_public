#!/bin/bash
# One ht3d lane (cutoff continuation for one x) per array element. Submitted ONLY by
# campaign.py submit/resubmit, which passes -A/-p/--nodes/--cpus-per-task/--mem/-t/
# --signal/-J/-o/--array and exports HT3D_MANIFEST, HT3D_RELEASE_TAR(_SHA256).
# No `set -u`: the site bashrc/module init is not nounset-safe.
#
# Stops (--signal=B:USR1@lead, scancel --signal, TERM): the trap is installed FIRST, so a
# stop during staging is remembered. The runner starts with stop signals ignored (it
# installs its own handler before loading anything), and while a stop is pending this
# shell re-sends USR1 every 5 s until the runner exits; the runner ignores stop signals
# again once it has finished, so a late re-send cannot kill it.
set -o pipefail
stop=0; child=
forward() { stop=1; [ -n "$child" ] && kill -USR1 "$child" 2>/dev/null; return 0; }
trap forward USR1 TERM INT
: "${HT3D_MANIFEST:?}" "${HT3D_RELEASE_TAR:?}" "${HT3D_RELEASE_TAR_SHA256:?}" "${SLURM_ARRAY_TASK_ID:?}"
echo "ht3d lane $SLURM_ARRAY_TASK_ID job $SLURM_JOB_ID (array $SLURM_ARRAY_JOB_ID) on $(hostname) cpus=$SLURM_CPUS_PER_TASK start $(date -Is)"
# Verify the tarball first, then stage with the scripts inside it (not a mutable tree).
[ "$(sha256sum "$HT3D_RELEASE_TAR" | cut -d' ' -f1)" = "$HT3D_RELEASE_TAR_SHA256" ] || { echo "release tarball checksum mismatch" >&2; exit 74; }
_tmp=/scratch/$USER/job_$SLURM_JOB_ID/boot; mkdir -p "$_tmp" || exit 74
tar -xf "$HT3D_RELEASE_TAR" -C "$_tmp" cluster/expanse/stage.sh || exit 74
source "$_tmp/cluster/expanse/stage.sh" || exit 74
source "$HT3D_STAGED/cluster/expanse/env.sh" || exit 70
export NUMBA_NUM_THREADS=${SLURM_CPUS_PER_TASK:-1}
if [ "$stop" = 1 ]; then echo "ht3d lane $SLURM_ARRAY_TASK_ID: stop requested before launch; exit 75"; exit 75; fi
( trap '' USR1 TERM INT; exec python "$HT3D_STAGED/cluster/expanse/lanes.py" run --manifest "$HT3D_MANIFEST" --lane "$SLURM_ARRAY_TASK_ID" ) &
child=$!
while kill -0 "$child" 2>/dev/null; do
  sleep 5 & wait $! 2>/dev/null
  [ "$stop" = 1 ] && kill -USR1 "$child" 2>/dev/null
done
wait "$child"; rc=$?
echo "ht3d lane $SLURM_ARRAY_TASK_ID exit $rc at $(date -Is)"
exit "$rc"
