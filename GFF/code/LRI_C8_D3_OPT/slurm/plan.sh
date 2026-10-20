#!/usr/bin/env bash
# Plan a campaign and build its dispatch index inside a job (tools/submit.py plan): campaign.py plan hashes every
# graph payload of the selected loops (up to 9.3 GB), which does not belong on a login node.
#   C8OPT_RUN, C8OPT_DISPATCH  the new campaign and dispatch-index directories (must not exist)
#   C8OPT_SEED                 the fresh base seed (submit.py checked and reserved it)
#   C8OPT_LANES                lanes of the index (= nodes x lanes per node of the lanes job)
#   C8OPT_PLAN_ARGV, C8OPT_INDEX_ARGV  JSON arrays of allow-listed extra options (submit.py: never --seed,
#                              --executable, a destination or --lanes), passed as separate arguments, never word-split
#SBATCH --job-name=c8opt-plan
#SBATCH --output=c8opt-plan-%j.out
set -euo pipefail
: "${C8OPT_ENV_SETUP:?}" "${C8OPT_RUN:?}" "${C8OPT_DISPATCH:?}" "${C8OPT_SEED:?}" "${C8OPT_LANES:?}"
: "${C8OPT_PLAN_ARGV:?}" "${C8OPT_INDEX_ARGV:?}"
unset C8OPT_ENV_COMPLETE
source "$C8OPT_ENV_SETUP" || { echo "c8opt: sourcing $C8OPT_ENV_SETUP failed" >&2; exit 65; }
source "$C8OPT_PACKAGE/slurm/site.sh"
c8opt_site
c8opt_check_env
cd "$C8OPT_PACKAGE"
export OPENBLAS_NUM_THREADS=1
exec "$C8OPT_PYTHON" -B - <<'PY'
import json, os, subprocess, sys
e = os.environ
plan_extra, index_extra = json.loads(e["C8OPT_PLAN_ARGV"]), json.loads(e["C8OPT_INDEX_ARGV"])
for argv, banned in ((plan_extra, ("--seed", "--executable")), (index_extra, ("--lanes",))):
    if not isinstance(argv, list) or not all(isinstance(x, str) for x in argv) or any(x in banned for x in argv):
        sys.exit(f"c8opt plan: refused extra arguments {argv}")
plan = [e["C8OPT_PYTHON"], "-B", "tools/campaign.py", "plan", e["C8OPT_RUN"], *plan_extra,
        "--seed", e["C8OPT_SEED"], "--executable", os.path.join(e["C8OPT_PACKAGE"], "bin/c8d3_optimized")]
index = [e["C8OPT_PYTHON"], "-B", "tools/hpc_dispatch.py", "index", e["C8OPT_RUN"], e["C8OPT_DISPATCH"], *index_extra,
         "--lanes", e["C8OPT_LANES"]]
for cmd in (plan, index):
    print("c8opt plan:", json.dumps(cmd), flush=True)
    subprocess.run(cmd, check=True)
print("c8opt plan: campaign and dispatch ready", flush=True)
PY
