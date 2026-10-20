# Environment file for a C8(1) production rerun (sourced by every job through C8_ENV_SETUP, before `set -u`).
# Copy, fill in the placeholders, and export C8_ENV_SETUP=/path/to/your/copy. The production versions are
# cluster/env_expanse.sh and cluster/symmetry/env_symmetry.sh.
module purge                                   # site specific: a GCC with libquadmath (production: GCC 13.3.0) and Boost headers
module load <GCC_MODULE> <BOOST_MODULE>
export CPATH="$BOOST_ROOT/include${CPATH:+:$CPATH}"
source <SCRATCH>/c8_venv/bin/activate         # Python >= 3.8 with numpy, scipy, mpmath (see requirements)
export C8_PYTHON=<SCRATCH>/c8_venv/bin/python3
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
