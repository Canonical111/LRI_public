#!/bin/bash
#SBATCH --job-name=c8d2-plan
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=15G
#SBATCH --time=01:00:00
#SBATCH --no-requeue
#SBATCH --output=c8d2-plan-%j.log
# Plan a campaign inside a job (plans above 10^6 tasks must; never on a login node), add its base seed to the
# forbidden-seed log $C8_SEEDS at once (D9: before any index can run; tools/seeds.py add, idempotent, source = RUN;
# without C8_SEEDS a note asks for it; a non-test plan has already registered it in its first --forbid-seeds-from log
# under that log's lock before publishing, Z15, so the add says "present" when that log is $C8_SEEDS), then register
# this job in the new campaign's allocation ledger with role plan
# (plan jobs are overhead, not work; R10). A failed seed add does not skip the ledger registration: the job then exits
# with the add's status, naming the command to repeat. Publication is atomic: a job killed mid-way leaves no campaign
# directory, and a rerun succeeds.
#   sbatch [site options] slurm/plan.sh RUN <production.py plan arguments>
#   e.g. symmetry: sbatch -p sharedq -c 8 --mem=15G -t 01:00:00 --no-requeue slurm/plan.sh /mnt/beegfs/$USER/c8-d2/pilot1 \
#                  --pilot --points 4096 --replicates 8 --threads 8 --index-hours 1.5 --cost-model ... --forbid-seeds-from $C8_SEEDS --seed <fresh>
set -eo pipefail
if [[ -n "${C8_ENV_SETUP:-}" ]]; then [[ -r "$C8_ENV_SETUP" ]] || { echo "C8: cannot read C8_ENV_SETUP=$C8_ENV_SETUP" >&2; exit 64; }; source "$C8_ENV_SETUP"; fi
set -u
PY="${C8_PYTHON:-python3}"
: "${C8_PACKAGE:?Set C8_PACKAGE to the package directory}"
[[ $# -ge 1 ]] || { echo "usage: slurm/plan.sh RUN <plan arguments>" >&2; exit 64; }
run="$1"; shift
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
"$PY" -B "$C8_PACKAGE/tools/production.py" plan "$run" "$@"
seed_rc=0
if [[ -n "${C8_SEEDS:-}" ]]; then "$PY" -B "$C8_PACKAGE/tools/seeds.py" add "$run" || seed_rc=$?
else echo "C8: C8_SEEDS is not set: add the seed by hand before any index runs (tools/seeds.py add $run --log <seed log>)" >&2; fi
"$PY" -B "$C8_PACKAGE/tools/ledger.py" register "$run" --role plan
if (( seed_rc )); then
    echo "C8: the base seed of $run was NOT added to $C8_SEEDS (exit $seed_rc): add it before any index runs (tools/seeds.py add $run)" >&2; exit "$seed_rc"
fi
