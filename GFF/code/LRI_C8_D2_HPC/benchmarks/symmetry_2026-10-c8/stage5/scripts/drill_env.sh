# Shell setup of the sharedq lane drills J-DRL-4..8 on symmetry (Stage 5; PLAN "C7(2) drills ported to lanes"), sourced
# in fresh login shells: drill-mode lane workers (C8_LANE_DRILL=1, 2 CPUs, 3G, no --exclusive, --no-requeue) and
# 2-CPU merges on sharedq, 2-thread test-only plans as in C7(2)'s drill_env.sh, outside the H7 AMD cap; sharedqos runs
# at most 4 jobs of a user at once. The cost model is the final symmetry model (J-SWEEP-2 + J-SWEEP-3 class factors).
export PATH=/cm/shared/apps/slurm/current/bin:$PATH
source "$HOME/c8d2/env.sh"
export C8_ENV_SETUP=$HOME/c8d2/env.sh C8_PACKAGE=<SCRATCH>/c8d2/pkg/5d7586e9f1ab
export C8_LANE_DRILL=1 C8_LANE_CPUS=2 C8_LANE_MEM=3G C8_MERGE_JOBS=2 C8_MERGE_MEM=3G C8_SBATCH_ARGS="-p sharedq"
export C8_LANE_TIME=00:30:00 C8_MERGE_TIME=00:30:00
DR=<SCRATCH>/c8-d2/drills-5d7586e9f1ab; EV=<SCRATCH>/c8d2/evidence/5d7586e9f1ab/drills; mkdir -p $DR $EV
CM=$C8_PACKAGE/cost_models/gmp_symmetry_amd_c8.json
seed(){ python3 -c 'import secrets;print(secrets.randbits(63))'; }
PLAN(){ python3 -B $C8_PACKAGE/tools/production.py plan "$1" --pilot --seed "$2" --backend gmp --points "${3:-8}" --replicates 4 --test-graphs 2 \
          --shards 4 --threads 2 --checkpoint-tasks 64 --cost-model $CM; }
STATUS(){ python3 -B $C8_PACKAGE/tools/production.py status "$@"; }
SUBMIT(){ $C8_PACKAGE/slurm/submit.sh "$@"; }
SQ(){ squeue -u <USER> -h -o '%i %j %T %P %M %l %R %E' | grep c8d2; }
sums(){ (cd "$1" && find groups -name merged.json -o -name graph_replicates.csv -o -name graph_tails.csv -o -name graph_costs.csv | sort | xargs sha256sum; ls C8_test_result.json 2>/dev/null && sha256sum C8_test_result.json); }
