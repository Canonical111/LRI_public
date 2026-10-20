# Sourced by every C8(3) job script (PLAN D.10): the site setup, then nounset, the interpreter check, the package and
# campaign variables, the CPU pin and the job's node-local scratch. Not a job script itself.
# The CPU pin (HD11; slurm/site.sh c8_site_cpu, c8_cpu_guard): a job of C8_SITE=symmetry (AMD pool) or expanse that runs
# on another CPU than the site's cost-model CPU (EPYC 7543, EPYC 7742) exits 68 here, before any scratch directory,
# lane claim, plan, merge or probe output exists (lane_worker.sh, run_array.sh, plan.sh, merge.sh, scratch_probe.sh); a
# node of another CPU vendor than the campaign's pin ($C8_RUN/cpu_vendor.json; S2-001) exits 68 there too.
# C8_ENV_SETUP is sourced with errexit on and BEFORE nounset (module and bashrc scripts reference unset variables).
if [[ -n "${C8_ENV_SETUP:-}" ]]; then [[ -r "$C8_ENV_SETUP" ]] || { echo "C8: cannot read C8_ENV_SETUP=$C8_ENV_SETUP" >&2; exit 64; }; source "$C8_ENV_SETUP"; fi
set -u
PY="${C8_PYTHON:-python3}"
"$PY" -c 'import sys;sys.exit(0 if sys.version_info>=(3,10) else 1)' || { echo "C8: $PY is missing or older than Python 3.10; set C8_PYTHON or C8_ENV_SETUP" >&2; exit 64; }
: "${C8_PACKAGE:?Set C8_PACKAGE to the package directory (slurm_submit.py sets it)}"
# C8_SCRATCH is computed HERE, inside the job, whatever the submitting shell held (--export=ALL would otherwise carry a
# login-node value into the job; A-EXP-1): $SLURM_TMPDIR, else the node-local disk (Expanse /scratch/$USER/job_$SLURM_JOB_ID;
# symmetry, C8_SITE=symmetry from env.sh, /local1/$USER/job_$SLURM_JOB_ID); never /tmp. One rule for every job script:
# slurm/site.sh (c8_set_scratch).
source "$C8_PACKAGE/slurm/site.sh"
c8_cpu_guard
c8_vendor_guard   # one CPU vendor per campaign: a node of another vendor than $C8_RUN/cpu_vendor.json's exits 68 (S2-001)
c8_set_scratch
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
