#!/usr/bin/env bash
# The streaming assembly of a completed campaign (tools/assemble_streaming.py), as a job. Submit with
# tools/submit.py assemble. Outputs go to new files in the campaign directory (never over an earlier result).
#SBATCH --job-name=c8opt-assemble
#SBATCH --output=c8opt-assemble-%j.out
set -euo pipefail
: "${C8OPT_ENV_SETUP:?Set C8OPT_ENV_SETUP to the site env file}"
: "${C8OPT_RUN:?Set C8OPT_RUN to a completely finished campaign directory}"
unset C8OPT_ENV_COMPLETE
source "$C8OPT_ENV_SETUP" || { echo "c8opt: sourcing $C8OPT_ENV_SETUP failed" >&2; exit 65; }
source "$C8OPT_PACKAGE/slurm/site.sh"
c8opt_site
c8opt_check_env
c8opt_scratch
cd "$C8OPT_PACKAGE"
export OPENBLAS_NUM_THREADS=${SLURM_CPUS_PER_TASK:-1}
tag=${SLURM_JOB_ID:-local}
"$C8OPT_PYTHON" -B tools/campaign.py status "$C8OPT_RUN"
exec "$C8OPT_PYTHON" -B tools/assemble_streaming.py "$C8OPT_RUN" --bootstrap "${C8OPT_BOOTSTRAP:-4096}" \
     --output "$C8OPT_RUN/C8_result_${tag}.json" --graph-statistics "$C8OPT_RUN/graph_statistics_${tag}.json"
