#!/bin/bash
# make test-all of LRI_C6_D3_HPC on one node (template; replace the <...> placeholders).
# Measured: about 6 min on 16 cores / 32 GB of an AMD EPYC 7742 node (SDSC Expanse, shared partition, job 54510646).
#SBATCH --account=<ACCOUNT>
#SBATCH --partition=<PARTITION>
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --time=00:30:00
#SBATCH --job-name=c6d3-test-all
#SBATCH --output=c6d3-test-all-%j.out
set -euo pipefail
<LOAD_MODULES>            # e.g. module load cpu/0.21.2a gcc/13.3.0 boost/1.86.0 on Expanse; GCC with OpenMP and libquadmath
source <VENV>/bin/activate  # Python >= 3.10 with requirements.txt installed
cd <GFF>/code/LRI_C6_D3_HPC
make -f public.mk clean
make -f public.mk test-all
make -f public.mk replay
