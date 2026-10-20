# C8_ENV_SETUP of the site layer on symmetry (Perimeter; docs/SITES.md). Install the package as a git clone at a tag in
# ~/c8ind/LRI_C8_D2_HPC_optimized and export C8_ENV_SETUP=~/c8ind/LRI_C8_D2_HPC_optimized/slurm/env_symmetry.sh before
# tools/site_submit.py, a build or a test. Sourced by slurm/node_runner.sh (set -euo pipefail), slurm/merge.sh
# (set -eo pipefail) and slurm/site_gate.sh; the module and venv code run with nounset suspended.
# Stack: system GCC 11.4, the boost/1.77.0 module's headers, system GMP 6.2.1, python/3.11 with this layer's own venv
# ~/c8ind/venv (numpy, scipy 1.17.x for the private Sobol API, mpmath; separate from LRI_C8_D2_HPC's ~/c8d2/venv), and
# the Slurm 21.08 commands (sacct -s needs -E there).
# Inside a job TMPDIR is a fresh per-job directory under node-local /tmp, checked to allow executing (production.py run
# executes a private copy of the binary there) and removed when the job's shell exits (c8_site_cleanup).
# The AMD-pool budget is NOT set here: C8_AMD_CAP (this session's share) and C8_AMD_POOL_TOTAL (both sessions) come
# from the agreement with C63d in force (LRI_C8_shared/inventory/DECISIONS.md) and are exported explicitly.
case $- in *u*) _c8_nounset=1; set +u ;; *) _c8_nounset=0 ;; esac
source /etc/profile.d/modules.sh
module load boost/1.77.0 python/3.11
export PATH=/cm/shared/apps/slurm/current/bin:$PATH
source "$HOME/c8ind/venv/bin/activate"
if [ "$_c8_nounset" = 1 ]; then set -u; fi
unset _c8_nounset
C8_PYTHON="$(command -v python3)"; export C8_PYTHON
export C8_SITE=symmetry
export C8_DATA=<SCRATCH>/c8-d2-indep
# Our forbidden-seed registry's symmetry log (LRI_C8_D2_HPC tools/seeds.py; the port reserves non-test seeds there) and
# our pinned seed tools (LRI_C8_D2_HPC aafa8a4, deployed by git archive).
export C8_SEEDS=<SCRATCH>/c8-d2/forbidden_seeds.json
export C8_SEEDS_TOOL_DIR="$HOME/c8ind/c8d2_seedtool/tools"
export C8_REQUIRE_BACKEND="${C8_REQUIRE_BACKEND:-gmp}"
export OPENBLAS_NUM_THREADS=1
if [ -n "${SLURM_JOB_ID:-}" ]; then
  if ! _c8_tmp="$(mktemp -d "/tmp/c8ind_${SLURM_JOB_ID}_XXXXXX")"; then
    echo "C8: cannot create a per-job directory in node-local /tmp; stopping (exit 64)" >&2; return 64 2>/dev/null || exit 64
  fi
  export TMPDIR="$_c8_tmp"; unset _c8_tmp
  c8_site_cleanup() { if [ -n "${TMPDIR:-}" ] && [ -d "$TMPDIR" ]; then case "$TMPDIR" in /tmp/c8ind_*) rm -rf "$TMPDIR" ;; esac; fi; }
  trap c8_site_cleanup EXIT  # slurm/node_runner.sh replaces this trap with its own, which calls c8_site_cleanup
  if ! printf '#!/bin/sh\nexit 0\n' > "$TMPDIR/.c8_exec_probe" || ! chmod 700 "$TMPDIR/.c8_exec_probe" || ! "$TMPDIR/.c8_exec_probe"; then
    echo "C8: node-local TMPDIR=$TMPDIR does not allow executing; stopping (exit 64)" >&2; c8_site_cleanup; return 64 2>/dev/null || exit 64
  fi
  rm -f "$TMPDIR/.c8_exec_probe"
fi
