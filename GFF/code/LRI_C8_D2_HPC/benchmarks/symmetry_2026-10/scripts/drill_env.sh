# Environment for the C7(2) fix-loop real-Slurm drills on symmetry (sourced in fresh login shells).
export PATH=/cm/shared/apps/slurm/current/bin:$PATH
W=<SCRATCH>/c7d2_fix; E=$W/evidence/drills; mkdir -p $E
export C7_PACKAGE=$W/final C7_ENV_SETUP=$HOME/c7d2_prod/env.sh C7_SBATCH_ARGS="-p sharedq --mem=1900M"
PYV=$HOME/c7d2_prod/venv/bin/python3
seed(){ $PYV -c 'import secrets;print(secrets.randbelow(2**63))'; }
PLAN(){ $PYV -B $C7_PACKAGE/tools/production.py plan "$1" --seed $(seed) --backend gmp --points 8 --replicates 4 --test-graphs 2 --shards 4 --threads 2 --checkpoint-tasks 64; }
STATUS(){ $PYV -B $C7_PACKAGE/tools/production.py status "$@"; }
