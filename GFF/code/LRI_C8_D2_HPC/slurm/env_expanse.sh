# C8_ENV for LRI_C8_D2_HPC on SDSC Expanse (account yun124). Install as ~/c8d2/env_expanse.sh; every Expanse job
# of this package sources that copy and records its sha256.
# Site deviation U1 (user, 2026-10-03; LRI_C8_D2_HPC_loop/PLAN-REVIEW-LOG.md): development, validation and
# profiling compute run on Expanse while symmetry's compute nodes are down; the package stays symmetry-ready.
# Stack (PLAN A-EXP-1): Spack GCC 13.3.0 (cpu/0.21.2a), Boost 1.77 headers by path (Expanse's boost/* modules set
# only BOOST_ROOT, not CPATH, so a plain build would see the system Boost 1.66), Spack GMP 6.2.1, a python/3.11.9 venv
# ~/c8d2/venv holding requirements.txt plus pytest (numpy 2.3.5, scipy 1.17.1, mpmath 1.3.0, sympy 1.14.0, as on
# symmetry), and the Slurm commands on PATH. Data live on Lustre under $C8_DATA, code in home.
# Safe to source under `set -euo pipefail`: the module system and the venv activation run with nounset suspended.
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
source "$HOME/c8d2/venv/bin/activate"
export C8_PYTHON="$(command -v python3)"
export C8_SITE=expanse
export C8_DATA=/expanse/lustre/scratch/zzheng8/temp_project/c8d2
# The forbidden-seed log (PLAN D9; tools/seeds.py): every campaign's base seed and the L=2 control's.
export C8_SEEDS=$C8_DATA/forbidden_seeds.json
if [ "$_c8_nounset" = 1 ]; then set -u; fi
unset _c8_nounset
