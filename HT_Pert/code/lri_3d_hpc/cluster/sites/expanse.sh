# Expanse (SDSC) site profile; sourced by cluster/env.sh, never executed.
# Verified 2026-10-08: login and compute nodes are AMD EPYC 7742; Lustre scratch is mounted
# with cluster-wide flock; node-local NVMe scratch is /scratch/$USER/job_$SLURM_JOB_ID.
HT3D_SITE=expanse
HT3D_DATA=${HT3D_DATA:-/expanse/lustre/scratch/$USER/temp_project/ht3d_pert}
HT3D_VENV=${HT3D_VENV:-$HT3D_DATA/venv-py3129-np253-sp1170-nb0680}
HT3D_LOCK_ROOT=${HT3D_LOCK_ROOT:-$HT3D_DATA/locks}       # Lustre: flock is cluster-wide
HT3D_ACCOUNT=${HT3D_ACCOUNT:-yun124}
HT3D_MODULES="cpu/0.21.2a gcc/13.3.0 openmpi/4.1.8 slurm/expanse/23.02.7"
# MPI launchers tried in this order by the validation receipt (the first that gives a
# correct world size is recorded and used by MPI solves).
HT3D_MPI_LAUNCHERS="srun --mpi=pmix;srun --mpi=pmi2"   # pmix works, pmi2 does not (receipt 54763995)

ht3d_site_init() {
  if ! type module >/dev/null 2>&1; then
    # shellcheck disable=SC1091
    source /etc/profile.d/modules.sh || { echo "env: cannot initialise modules" >&2; return 70; }
  fi
  module purge || { echo "env: module purge failed" >&2; return 70; }
  local m
  for m in $HT3D_MODULES; do   # one at a time: a combined load can fail silently
    module load "$m" || { echo "env: module load $m failed" >&2; return 70; }
  done
  return 0
}

ht3d_node_scratch() {   # created and removed by Slurm for every job (array tasks included)
  echo "/scratch/$USER/job_${SLURM_JOB_ID:?}"
}
