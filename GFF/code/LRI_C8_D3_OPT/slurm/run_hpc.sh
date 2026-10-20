#!/usr/bin/env bash
# The packed-lane worker job: one tools/hpc_dispatch.py lane per Slurm task (docs/CLUSTERS.md). Submit it with
# tools/submit.py lanes, never with plain sbatch: submit sets the partition, account, whole nodes, --mem, --time,
# --no-requeue, the node exclusions, --signal=TERM@<grace> and the caps.
#SBATCH --job-name=c8opt-lanes
#SBATCH --output=c8opt-lanes-%j.out
set -euo pipefail
: "${C8OPT_ENV_SETUP:?Set C8OPT_ENV_SETUP to the site env file (~/c8opt/env.sh)}"
: "${C8OPT_DISPATCH:?Set C8OPT_DISPATCH to the frozen dispatch-index directory}"
unset C8OPT_ENV_COMPLETE
source "$C8OPT_ENV_SETUP" || { echo "c8opt: sourcing $C8OPT_ENV_SETUP failed" >&2; exit 65; }
: "${C8OPT_PACKAGE:?C8OPT_PACKAGE (the env file sets it)}"
source "$C8OPT_PACKAGE/slurm/site.sh"
c8opt_site
c8opt_check_env
cd "$C8OPT_PACKAGE"
# --ntasks must equal the index's lane count (submit checks it too)
"$C8OPT_PYTHON" -c 'import json,os; n=len(json.load(open(os.path.join(os.environ["C8OPT_DISPATCH"],"index.json")))["lanes"]); t=int(os.environ["SLURM_NTASKS"]); assert n==t, ("Slurm tasks", t, "dispatch lanes", n)'
echo "c8opt lanes: job ${SLURM_JOB_ID} nodes ${SLURM_JOB_NODELIST} tasks ${SLURM_NTASKS} x ${SLURM_CPUS_PER_TASK} threads; dispatch $C8OPT_DISPATCH; $(date -u +%FT%TZ)"
# Every task checks its own node's CPU and makes its node-local scratch. One failed lane does not kill the others
# (--kill-on-bad-exit=0): a lane that could not finish exits 3 (deferred, busy or failed bundles) or 143 (signal),
# and the allocation is resubmitted; completed checkpoints are kept and skipped.
set +e
srun --cpu-bind=cores --kill-on-bad-exit=0 bash -c '
  set -euo pipefail
  source "$C8OPT_PACKAGE/slurm/site.sh"
  c8opt_cpu_guard strict
  c8opt_scratch
  c8opt_omp
  exec "$C8OPT_PYTHON" -B tools/hpc_dispatch.py run "$C8OPT_DISPATCH" --lane "$SLURM_PROCID" \
       --threads "$SLURM_CPUS_PER_TASK" --scratch "$C8OPT_SCRATCH"
'
rc=$?
echo "c8opt lanes: srun exit $rc; $(date -u +%FT%TZ); lane summaries in $C8OPT_DISPATCH/runs/"
exit $rc
