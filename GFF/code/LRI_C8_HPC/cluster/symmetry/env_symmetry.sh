# C8 extension environment on symmetry (amendment A1; sourced by jobs before set -u).
# Runs the Expanse-built production binary (code/c0ffa63/bin/c8_integrate, sha256 ffb200d4...) with the GCC 13.3.0
# runtime libraries copied from Expanse (its RPATH points at Expanse paths that do not exist here).
source /etc/profile.d/modules.sh
module purge
module load anaconda3/2023.07-2
export PATH=/cm/shared/apps/slurm/current/bin:$PATH
export C8W=/mnt/beegfs/zzheng1/c8_hpc
export LD_LIBRARY_PATH=$C8W/rtlib_gcc13.3${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
export C8_PYTHON=$(command -v python3)
export C8_ROOT=$C8W/code/c0ffa63                 # frozen production tools and binary (byte-identical to Expanse)
export C8_EXE=$C8_ROOT/bin/c8_integrate
export C8_EXE_SHA256=ffb200d40026a25f6337bdf778f8652a73a02b4730c8f2e8c91232b6ebc7db8b
export C8_BUNDLE=$C8W/designs_frozen/prod4_34000
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_DYNAMIC=FALSE OMP_PLACES=cores OMP_PROC_BIND=close
