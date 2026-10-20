# drill env: production env plus a per-job scratch on BeeGFS so leftovers are visible from the login node
source $HOME/c7d2_prod/env.sh
export TMPDIR=<SCRATCH>/c7d2_fix/scratch_drill/${SLURM_JOB_ID:-nojob}_${SLURM_ARRAY_TASK_ID:-x}
mkdir -p "$TMPDIR"
