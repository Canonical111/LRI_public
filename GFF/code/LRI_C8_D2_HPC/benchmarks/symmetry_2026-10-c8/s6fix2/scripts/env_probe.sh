# C8_ENV_SETUP of the Stage-6 fix-round-2 lane drill (s2.sh lanedrill): the site setup (~/c8d2/env.sh), then a record of
# the OpenMP controls the job inherited from the submitting shell (OMP_*, GOMP_*, KMP_*), written to
# $C8_PROBE_OUT/omp_env_job_<job id>.txt by every job that sources it (the lane worker and the merge). Sourced by
# slurm/lane_worker.sh and slurm/merge.sh under `set -eo pipefail`, before `set -u`.
source "$HOME/c8d2/env.sh"
if [ -n "${C8_PROBE_OUT:-}" ] && [ -n "${SLURM_JOB_ID:-}" ]; then
  { env | grep -E '^(OMP|GOMP|KMP)_' | sort; } > "$C8_PROBE_OUT/omp_env_job_${SLURM_JOB_ID}.txt" || true
fi
