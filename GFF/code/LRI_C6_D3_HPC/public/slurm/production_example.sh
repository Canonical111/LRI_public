#!/bin/bash
# The C6(3) production of 2026-09-29, as a rerun recipe (template; documented, never run in CI). Replace <...>.
# It ran on SDSC Expanse (AMD EPYC 7742, GCC 13.3), shared partition, 458 array elements of 64 CPUs, about
# 1.0e4 core-hours (plan estimate 9,653), 07:08-10:14 PDT with up to 64 concurrent elements.
# A rerun with a fresh seed gives an independent estimate of the same quantity, not the same digits: the result
# depends on the seed, and must be judged by the reporting rule in results/C6_3/CAMPAIGN.md.
set -euo pipefail
export C6_PACKAGE=<GFF>/code/LRI_C6_D3_HPC          # built on the target architecture: make clean && make && make -f public.mk test
export C6_ENV_SETUP=<ENV_SCRIPT>                     # modules + venv, as slurm/expanse_env.sh.example
export C6_RUN=<SCRATCH>/c6-d3/run-<DATE>             # a NEW directory on a shared filesystem (not node-local)
source "$C6_ENV_SETUP"
cd "$C6_PACKAGE"
# 1. Plan (about 90 s; run it on a compute node: srun -c 1 --mem=8G ...). The production used seed 3864037981285414462;
#    a rerun must choose a fresh 63-bit seed, e.g. python3 -c 'import secrets;print(secrets.randbits(63))'.
python3 tools/production.py plan "$C6_RUN" --seed <FRESH_SEED> \
  --replicates 64 --multiplier 8192 --chunk-points 8388608 --threads 64 --checkpoint-tasks 1024 --shards 200
# 2. Submit all work elements and an afterok merge + assembly (arrays split at 1000; 64 CPUs and the suggested time
#    come from the plan). The production passed --mem=8G (peak RSS 121 MB per element).
C6_SBATCH_ARGS="-A <ACCOUNT> -p <PARTITION>" slurm/submit.sh --mem=8G
# 3. Monitor; recover failed elements (scancel the pending merge first, then):
python3 tools/production.py status "$C6_RUN"
#    C6_SBATCH_ARGS="-A <ACCOUNT> -p <PARTITION>" slurm/resubmit.sh --mem=8G
# 4. The merge job writes $C6_RUN/C6_result.json (tools/production.py merge; tools/assemble.py --bootstrap 4096).
#    Report it only by the pre-registered rule (results/C6_3/CAMPAIGN.md): estimate +- 4 x SE rounded up to a
#    multiple of 0.0001 (Amendment 1), with the a/b, bootstrap, previous-value and lower-order checks.
#    The same replay applies to the new run: make -f public.mk replay RESULTS=$C6_RUN (its quoted-digit rows will
#    then differ by design; the binding and recomputation rows must pass).
