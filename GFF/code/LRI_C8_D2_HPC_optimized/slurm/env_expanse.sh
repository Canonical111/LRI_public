# C8_ENV_SETUP of the site layer on SDSC Expanse (account <ACCOUNT>; docs/SITES.md). Install the package as a git clone
# at a tag in ~/c8ind/LRI_C8_D2_HPC_optimized and export C8_ENV_SETUP=~/c8ind/LRI_C8_D2_HPC_optimized/slurm/env_expanse.sh
# before tools/site_submit.py, a build or a test. Sourced by slurm/node_runner.sh (set -euo pipefail), slurm/merge.sh
# (set -eo pipefail) and slurm/site_gate.sh; the module and venv code run with nounset suspended.
# Stack: Spack GCC 13.3.0 (cpu/0.21.2a), Boost 1.77 headers BY PATH (the boost/* modules set only BOOST_ROOT, not CPATH,
# and inject py-numpy on PYTHONPATH, so they are not loaded), Spack GMP 6.2.1, python/3.11.9 with this layer's own venv
# ~/c8ind/venv (numpy, scipy 1.17.x for the private Sobol API, mpmath; separate from LRI_C8_D2_HPC's ~/c8d2/venv).
# Inside a job TMPDIR is the job's node-local /scratch/$USER/job_$SLURM_JOB_ID, which must exist and allow writing and
# executing (production.py run executes a private copy of the binary there); otherwise the job stops with exit 64.
case $- in *u*) _c8_nounset=1; set +u ;; *) _c8_nounset=0 ;; esac
if ! type module >/dev/null 2>&1; then source /etc/profile.d/modules.sh; fi
module purge
module load cpu/0.21.2a gcc/13.3.0 python/3.11.9
module load slurm/expanse/23.02.7
export C8_BOOST=/cm/shared/apps/spack/0.17.3/cpu/b/opt/spack/linux-rocky8-zen2/gcc-10.2.0/boost-1.77.0-bbnd4wnz3ueozpqlp2sz6rhsi2o2tuzn
export C8_GMP=/cm/shared/apps/spack/0.21.2/cpu/a/opt/spack/linux-rocky8-zen2/gcc-13.3.0/gmp-6.2.1-eywq454gcb355knxklm3gnfrkmj3nscw
export CPATH=$C8_BOOST/include:$C8_GMP/include${CPATH:+:$CPATH}
export LIBRARY_PATH=$C8_GMP/lib${LIBRARY_PATH:+:$LIBRARY_PATH}
export LD_LIBRARY_PATH=$C8_GMP/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
source "$HOME/c8ind/venv/bin/activate"
if [ "$_c8_nounset" = 1 ]; then set -u; fi
unset _c8_nounset
C8_PYTHON="$(command -v python3)"; export C8_PYTHON
export C8_SITE=expanse
export C8_DATA=<SCRATCH>/temp_project/c8-d2-indep
# Our forbidden-seed registry's Expanse log (LRI_C8_D2_HPC tools/seeds.py; the port reserves non-test seeds there) and
# our pinned seed tools (LRI_C8_D2_HPC aafa8a4, deployed by git archive).
export C8_SEEDS=<SCRATCH>/temp_project/c8d2/forbidden_seeds.json
export C8_SEEDS_TOOL_DIR="$HOME/c8ind/c8d2_seedtool/tools"
export C8_REQUIRE_BACKEND="${C8_REQUIRE_BACKEND:-gmp}"
export OPENBLAS_NUM_THREADS=1
if [ -n "${SLURM_JOB_ID:-}" ]; then
  export TMPDIR="/scratch/${USER:-$(id -un)}/job_$SLURM_JOB_ID"
  _c8_probe="$TMPDIR/.c8_exec_probe.$$"
  if [ ! -d "$TMPDIR" ] || ! printf '#!/bin/sh\nexit 0\n' > "$_c8_probe" 2>/dev/null || ! chmod 700 "$_c8_probe" || ! "$_c8_probe"; then
    echo "C8: node-local TMPDIR=$TMPDIR is missing, not writable or not executable; stopping (exit 64)" >&2
    rm -f "$_c8_probe" 2>/dev/null; unset _c8_probe; return 64 2>/dev/null || exit 64
  fi
  rm -f "$_c8_probe"; unset _c8_probe
fi
