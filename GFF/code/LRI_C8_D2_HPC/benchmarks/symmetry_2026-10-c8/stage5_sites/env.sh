# C8_ENV for LRI_C8_D2_HPC on symmetry: the symmetry block of slurm/env.sh.example at c8 HEAD 09e8f4a (installed
# 2026-10-05, Stage 5; the previous file is ~/c8d2/env.sh.bak-20261003): system GCC 11.4 + Boost 1.77 module headers +
# system GMP 6.2.1 + python/3.11 venv ~/c8d2/venv, Slurm on PATH, C8_SITE=symmetry, the H7 AMD-pool cap C8_AMDQ_CAP=4
# (at most 4 live c8d2- jobs on amdq, amddebugq and amdpreq together; slurm_submit.py enforces it) and the symmetry
# seed log C8_SEEDS (docs/HPC.md, "The seed log": every new seed goes into both sites' logs and the package mirror).
# Safe to source under `set -euo pipefail`: the module system and the venv activation run with nounset suspended.
case $- in *u*) _c8_nounset=1; set +u ;; *) _c8_nounset=0 ;; esac
source /etc/profile.d/modules.sh
module load boost/1.77.0 python/3.11
export PATH=/cm/shared/apps/slurm/current/bin:$PATH
source "$HOME/c8d2/venv/bin/activate"
export C8_PYTHON="$(command -v python3)"
export C8_SITE=symmetry C8_AMDQ_CAP=4
export C8_SEEDS=<SCRATCH>/c8-d2/forbidden_seeds.json
# symmetry: CPU partitions give whole EXCLUSIVE nodes and have finite limits (amdq/defq 24 h, amddebugq/debugq 1 h);
# keep C8_TIME_POLICY=finite (default); lanes: C8_SBATCH_ARGS="-p amdq --exclude=cn112" C8_LANE_MEM=245G (amdq only) or
# 180G (fits Intel and AMD, e.g. "-p amdq,defq"); campaign directories on <SCRATCH>; MaxArraySize 1001.
# sharedq (lane drills): at most 8 CPUs and 2,000 MB per CPU, PreemptMode=REQUEUE, 4 running jobs per user.
if [ "$_c8_nounset" = 1 ]; then set -u; fi
unset _c8_nounset
